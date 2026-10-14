"""Serveur HTTP : API JSON + interface web. Uniquement la bibliothèque standard Python."""

import base64
import binascii
import hmac
import json
import logging
import mimetypes
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import __version__, cave, ha
from .cave import ErreurAPI

log = logging.getLogger("cave_a_vin")

STATIC = Path(__file__).parent / "static"
INGRESS_IP = "172.30.32.2"  # adresse du proxy « ingress » de Home Assistant
TAILLE_MAX = 15 * 1024 * 1024
ROUTES = []


def route(methode, motif):
    def deco(fn):
        ROUTES.append((methode, re.compile("^" + motif + "$"), fn))
        return fn
    return deco


class Reponse:
    def __init__(self, corps, type_="application/json; charset=utf-8", status=200, entetes=None):
        self.corps, self.type, self.status, self.entetes = corps, type_, status, entetes or {}


# --------------------------------------------------------------------------- routes

def _fichier_photo(app, nom):
    """Chemin d'une photo, uniquement dans le dossier des photos (une sauvegarde importée n'est pas fiable)."""
    if not nom or Path(nom).name != nom:
        return None
    return app.photos / nom


@route("GET", "api/health")
def _sante(app, req):
    return {"status": "ok", "version": __version__, "addon": ha.mode_addon()}


@route("GET", "api/stats")
def _stats(app, req):
    return cave.statistiques(app.db)


@route("GET", "api/referentiel")
def _referentiel(app, req):
    return {
        "couleurs": cave.COULEURS, "statuts": cave.STATUTS, "plats": {k: v["label"] for k, v in cave.PLATS.items()},
        "raisons_entree": cave.RAISONS_ENTREE, "raisons_sortie": cave.RAISONS_SORTIE,
        "autocompletion": cave.autocompletion(app.db), "annee": cave.annee_courante(),
        "addon": ha.mode_addon(), "version": __version__,
    }


@route("GET", "api/vins")
def _vins(app, req):
    return cave.lister_vins(app.db, req.query)


@route("POST", "api/vins")
def _creer_vin(app, req):
    return cave.creer_vin(app.db, req.json()), 201


@route("GET", r"api/vins/(\d+)")
def _vin(app, req, vin_id):
    return cave.lire_vin(app.db, int(vin_id))


@route("PUT", r"api/vins/(\d+)")
def _modifier_vin(app, req, vin_id):
    return cave.modifier_vin(app.db, int(vin_id), req.json())


@route("DELETE", r"api/vins/(\d+)")
def _supprimer_vin(app, req, vin_id):
    photo = cave.supprimer_vin(app.db, int(vin_id))
    if _fichier_photo(app, photo):
        _fichier_photo(app, photo).unlink(missing_ok=True)
    return {"ok": True}


@route("POST", r"api/vins/(\d+)/entree")
def _entree(app, req, vin_id):
    return cave.ajouter_bouteilles(app.db, int(vin_id), req.json())


@route("POST", r"api/vins/(\d+)/sortie")
def _sortie(app, req, vin_id):
    return cave.sortir_bouteilles(app.db, int(vin_id), req.json())


@route("GET", r"api/vins/(\d+)/photo")
def _photo(app, req, vin_id):
    vin = app.db.one("SELECT photo FROM vins WHERE id = ?", (int(vin_id),))
    chemin = _fichier_photo(app, vin["photo"]) if vin else None
    if not chemin or not chemin.exists():
        raise ErreurAPI("Pas de photo", 404)
    return Reponse(chemin.read_bytes(), "image/jpeg", entetes={"Cache-Control": "no-cache"})


@route("PUT", r"api/vins/(\d+)/photo")
def _envoyer_photo(app, req, vin_id):
    vin_id = int(vin_id)
    cave.lire_vin(app.db, vin_id, details=False)
    image = (req.json().get("image") or "")
    m = re.match(r"^data:image/(jpeg|png|webp);base64,(.+)$", image, re.S)
    if not m:
        raise ErreurAPI("Image invalide (JPEG, PNG ou WebP attendu)")
    try:
        contenu = base64.b64decode(m.group(2), validate=True)
    except (binascii.Error, ValueError):
        raise ErreurAPI("Image illisible")
    ancien = app.db.one("SELECT photo FROM vins WHERE id = ?", (vin_id,))["photo"]
    nom = f"vin-{vin_id}-{os.urandom(4).hex()}.{ 'jpg' if m.group(1) == 'jpeg' else m.group(1)}"
    (app.photos / nom).write_bytes(contenu)
    with app.db.transaction() as conn:
        conn.execute("UPDATE vins SET photo = ? WHERE id = ?", (nom, vin_id))
    if _fichier_photo(app, ancien):
        _fichier_photo(app, ancien).unlink(missing_ok=True)
    return {"ok": True}


@route("DELETE", r"api/vins/(\d+)/photo")
def _supprimer_photo(app, req, vin_id):
    vin = app.db.one("SELECT photo FROM vins WHERE id = ?", (int(vin_id),))
    if vin and vin["photo"]:
        if _fichier_photo(app, vin["photo"]):
            _fichier_photo(app, vin["photo"]).unlink(missing_ok=True)
        with app.db.transaction() as conn:
            conn.execute("UPDATE vins SET photo = NULL WHERE id = ?", (int(vin_id),))
    return {"ok": True}


@route("GET", "api/garde")
def _garde(app, req):
    q = req.query
    prix = q.get("valeur") or q.get("prix_achat") or None
    try:
        prix = float(prix.replace(",", ".")) if prix else None
    except ValueError:
        prix = None
    return cave.estimer_garde(q.get("couleur", "rouge"), q.get("millesime") or None, q.get("region", ""),
                              q.get("appellation", ""), prix)


@route("GET", "api/bouteilles/non-rangees")
def _non_rangees(app, req):
    return cave.bouteilles_sans_emplacement(app.db)


@route("PUT", r"api/bouteilles/(\d+)")
def _deplacer(app, req, bouteille_id):
    return cave.deplacer_bouteille(app.db, int(bouteille_id), req.json())


@route("GET", "api/caves")
def _caves(app, req):
    return cave.lister_caves(app.db)


@route("POST", "api/caves")
def _creer_cave(app, req):
    return cave.creer_cave(app.db, req.json()), 201


@route("GET", r"api/caves/(\d+)")
def _cave(app, req, cave_id):
    return cave.lire_cave(app.db, int(cave_id))


@route("PUT", r"api/caves/(\d+)")
def _modifier_cave(app, req, cave_id):
    return cave.modifier_cave(app.db, int(cave_id), req.json())


@route("DELETE", r"api/caves/(\d+)")
def _supprimer_cave(app, req, cave_id):
    cave.supprimer_cave(app.db, int(cave_id))
    return {"ok": True}


@route("GET", "api/mouvements")
def _mouvements(app, req):
    try:
        limite = int(req.query.get("limite", 200))
    except ValueError:
        raise ErreurAPI("Limite invalide")
    return cave.lister_mouvements(app.db, limite, req.query.get("type"))


@route("GET", "api/envies")
def _envies(app, req):
    return cave.lister_envies(app.db)


@route("POST", "api/envies")
def _creer_envie(app, req):
    return cave.creer_envie(app.db, req.json()), 201


@route("PUT", r"api/envies/(\d+)")
def _modifier_envie(app, req, envie_id):
    return cave.modifier_envie(app.db, int(envie_id), req.json())


@route("DELETE", r"api/envies/(\d+)")
def _supprimer_envie(app, req, envie_id):
    cave.supprimer_envie(app.db, int(envie_id))
    return {"ok": True}


@route("GET", "api/suggestion")
def _suggestion(app, req):
    try:
        limite = int(req.query.get("limite", 5))
    except ValueError:
        raise ErreurAPI("Limite invalide")
    return cave.suggerer(app.db, req.query.get("plat") or None, req.query.get("couleur") or None, limite)


@route("GET", "api/reglages")
def _reglages(app, req):
    r = app.reglages()
    r["ha_token_defini"] = bool(r.pop("ha_token"))
    r["addon"] = ha.mode_addon()
    return r


@route("PUT", "api/reglages")
def _modifier_reglages(app, req):
    data = req.json()
    with app.db.transaction() as conn:
        for cle in ha.REGLAGES_DEFAUT:
            if cle in data and (cle != "ha_token" or data[cle]):
                conn.execute("INSERT INTO reglages (cle, valeur) VALUES (?, ?) "
                             "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
                             (cle, str(data[cle] or "").strip()))
    return _reglages(app, req)


@route("GET", "api/ha/climat")
def _climat(app, req):
    return ha.climat(app.reglages())


@route("GET", "api/ha/capteurs")
def _capteurs(app, req):
    return ha.capteurs_disponibles(app.reglages())


@route("GET", "api/ha/resume")
def _resume_ha(app, req):
    """Tout ce dont l'intégration Home Assistant a besoin, en un seul appel."""
    stats = cave.statistiques(app.db)
    stats["climat"] = ha.climat(app.reglages())
    stats["version"] = __version__
    return stats


@route("GET", "api/export.csv")
def _export_csv(app, req):
    return Reponse(cave.exporter_csv(app.db).encode(), "text/csv; charset=utf-8",
                   entetes={"Content-Disposition": 'attachment; filename="cave-a-vin.csv"'})


@route("GET", "api/export.json")
def _export_json(app, req):
    return Reponse(json.dumps(cave.exporter_json(app.db), ensure_ascii=False, indent=1).encode(),
                   entetes={"Content-Disposition": 'attachment; filename="cave-a-vin-sauvegarde.json"'})


@route("POST", "api/import.csv")
def _import_csv(app, req):
    return cave.importer_csv(app.db, req.corps.decode("utf-8-sig", errors="replace"))


@route("POST", "api/import.json")
def _import_json(app, req):
    return cave.importer_json(app.db, req.json())


# --------------------------------------------------------------------------- serveur

class Requete:
    def __init__(self, query, corps):
        self.query = {k: v[-1] for k, v in query.items()}
        self.corps = corps

    def json(self):
        if not self.corps:
            return {}
        try:
            data = json.loads(self.corps)
        except ValueError:
            raise ErreurAPI("JSON invalide")
        if not isinstance(data, dict):
            raise ErreurAPI("Un objet JSON est attendu")
        return data


class Handler(BaseHTTPRequestHandler):
    server_version = f"CaveAVin/{__version__}"
    app = None  # renseigné par creer_serveur()

    def log_message(self, fmt, *args):
        log.debug("%s - %s", self.address_string(), fmt % args)

    def do_GET(self):
        self._traiter("GET")

    def do_POST(self):
        self._traiter("POST")

    def do_PUT(self):
        self._traiter("PUT")

    def do_DELETE(self):
        self._traiter("DELETE")

    def _autorise(self, query):
        cle = self.app.api_key
        if not cle or self.client_address[0] == INGRESS_IP:
            return True
        fournie = self.headers.get("X-API-Key") or (query.get("cle") or [""])[-1]
        auth = self.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            fournie = auth[7:]
        return hmac.compare_digest(fournie.encode(), cle.encode())

    def _traiter(self, methode):
        url = urlparse(self.path)
        chemin = url.path.lstrip("/")
        try:
            if not chemin.startswith("api/"):
                if methode != "GET":
                    raise ErreurAPI("Méthode non autorisée", 405)
                return self._fichier_statique(chemin)
            query = parse_qs(url.query)
            if not self._autorise(query):
                raise ErreurAPI("Clé d'API manquante ou invalide", 401)
            longueur = int(self.headers.get("Content-Length") or 0)
            if longueur > TAILLE_MAX:
                raise ErreurAPI("Requête trop volumineuse", 413)
            req = Requete(query, self.rfile.read(longueur) if longueur else b"")
            for m, motif, fn in ROUTES:
                trouve = motif.match(chemin)
                if trouve and m == methode:
                    resultat = fn(self.app, req, *trouve.groups())
                    break
            else:
                existe = any(motif.match(chemin) for _, motif, _ in ROUTES)
                raise ErreurAPI("Méthode non autorisée" if existe else "Introuvable", 405 if existe else 404)
            status = 200
            if isinstance(resultat, tuple):
                resultat, status = resultat
            if not isinstance(resultat, Reponse):
                resultat = Reponse(json.dumps(resultat, ensure_ascii=False).encode(), status=status)
            self._envoyer(resultat)
        except ErreurAPI as e:
            self._envoyer(Reponse(json.dumps({"erreur": e.message}, ensure_ascii=False).encode(), status=e.status))
        except Exception:  # noqa: BLE001 - on renvoie toujours une réponse propre
            log.exception("Erreur sur %s %s", methode, self.path)
            self._envoyer(Reponse(json.dumps({"erreur": "Erreur interne"}).encode(), status=500))

    def _fichier_statique(self, chemin):
        chemin = chemin or "index.html"
        cible = (STATIC / chemin).resolve()
        if STATIC.resolve() not in cible.parents or not cible.is_file():
            cible = STATIC / "index.html"  # application monopage
        type_ = mimetypes.guess_type(cible.name)[0] or "application/octet-stream"
        if type_.startswith("text/") or type_ in ("application/javascript", "image/svg+xml"):
            type_ += "; charset=utf-8"
        self._envoyer(Reponse(cible.read_bytes(), type_, entetes={"Cache-Control": "no-cache"}))

    def _envoyer(self, rep):
        try:
            self.send_response(rep.status, HTTPStatus(rep.status).phrase)
            self.send_header("Content-Type", rep.type)
            self.send_header("Content-Length", str(len(rep.corps)))
            for k, v in rep.entetes.items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(rep.corps)
        except (BrokenPipeError, ConnectionResetError):
            pass


class Application:
    def __init__(self, db, dossier_donnees, api_key=""):
        self.db = db
        self.api_key = api_key
        self.photos = Path(dossier_donnees) / "photos"
        self.photos.mkdir(parents=True, exist_ok=True)

    def reglages(self):
        r = dict(ha.REGLAGES_DEFAUT)
        r.update({l["cle"]: l["valeur"] for l in self.db.all("SELECT cle, valeur FROM reglages")})
        return r


def creer_serveur(app, hote="0.0.0.0", port=8099):
    handler = type("CaveHandler", (Handler,), {"app": app})
    serveur = ThreadingHTTPServer((hote, port), handler)
    serveur.daemon_threads = True
    return serveur
