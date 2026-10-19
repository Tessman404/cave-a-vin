"""Notifications Home Assistant quand un vin arrive en fin de garde.

Un vin est signalé l'année de sa dernière année de garde (statut « à boire vite ») : assez tôt pour le boire à temps.
Chaque vin est rappelé au plus RAPPELS_MAX fois, à INTERVALLE jours d'écart ; un vin dépassé n'est plus signalé.
"""

import json
import logging
import os
import threading
import urllib.error
import urllib.request
from datetime import date, timedelta

from . import cave, ha

log = logging.getLogger("cave_a_vin")
RAPPELS_MAX = 2
INTERVALLE = timedelta(days=15)


def services_notification(reglages):
    """Services notify.* de Home Assistant (téléphones, etc.), pour le menu des réglages."""
    url, jeton = ha.connexion(reglages)
    if not url:
        return []
    req = urllib.request.Request(f"{url}/services", headers={"Authorization": f"Bearer {jeton}"})
    try:
        with urllib.request.urlopen(req, timeout=8) as rep:
            domaines = json.loads(rep.read().decode())
    except (urllib.error.URLError, OSError, ValueError):
        return []
    notify = next((d for d in domaines if d.get("domain") == "notify"), {})
    noms = sorted(n for n in notify.get("services", {}) if n not in ("send_message", "persistent_notification"))
    return [f"notify.{n}" for n in noms]


def envoyer(reglages, service, titre, message):
    url, jeton = ha.connexion(reglages)
    if not url:
        raise RuntimeError("Home Assistant n'est pas configuré")
    domaine, _, nom = service.partition(".")
    if domaine != "notify" or not nom:
        raise RuntimeError("Service de notification invalide")
    donnees = {"group": "tessvine"}
    if os.environ.get("HOSTNAME") and ha.mode_addon():  # toucher la notification ouvre la cave dans Home Assistant
        donnees["url"] = "/" + os.environ["HOSTNAME"].replace("-", "_")
    corps = json.dumps({"title": titre, "message": message, "data": donnees}).encode()
    req = urllib.request.Request(f"{url}/services/notify/{nom}", data=corps, method="POST",
                                 headers={"Authorization": f"Bearer {jeton}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15):
        pass


def vins_a_rappeler(db, aujourdhui=None):
    """Vins en cave « à boire vite » qui n'ont pas encore eu leurs rappels, ou dont le dernier date de 15 jours."""
    aujourdhui = aujourdhui or date.today()
    vins = [v for v in cave.lister_vins(db, {"stock": "1"}) if v["statut"] == "urgent"]
    suivi = {r["vin_id"]: r for r in db.all("SELECT * FROM rappels_fin")}
    choisis = []
    for v in vins:
        r = suivi.get(v["id"])
        # un nouveau millésime de garde (garde modifiée) relance le suivi
        if r and r["garde_fin"] != v["garde_fin"]:
            r = None
        if not r or (r["nombre"] < RAPPELS_MAX and date.fromisoformat(r["dernier"]) + INTERVALLE <= aujourdhui):
            choisis.append((v, (r["nombre"] if r else 0) + 1))
    return choisis


def verifier(app, aujourdhui=None):
    """Envoie une notification groupée pour les vins à rappeler. Renvoie le nombre de vins signalés."""
    reglages = app.reglages()
    service = reglages.get("notif_service") or ""
    if not service:
        return 0
    aujourdhui = aujourdhui or date.today()
    choisis = vins_a_rappeler(app.db, aujourdhui)
    if not choisis:
        return 0
    lignes = [f"• {v['nom']}{' ' + str(v['millesime']) if v['millesime'] else ''} ({v['stock']} bout.)"
              + (" : dernier rappel" if n == RAPPELS_MAX else "") for v, n in choisis]
    titre = ("🍷 Un vin arrive en fin de garde" if len(choisis) == 1
             else f"🍷 {len(choisis)} vins arrivent en fin de garde")
    message = f"À boire avant la fin de {aujourdhui.year} :\n" + "\n".join(lignes)
    envoyer(reglages, service, titre, message)
    with app.db.transaction() as conn:
        for v, n in choisis:
            conn.execute("INSERT INTO rappels_fin (vin_id, nombre, dernier, garde_fin) VALUES (?, ?, ?, ?) "
                         "ON CONFLICT(vin_id) DO UPDATE SET nombre = excluded.nombre, dernier = excluded.dernier, "
                         "garde_fin = excluded.garde_fin", (v["id"], n, aujourdhui.isoformat(), v["garde_fin"]))
    log.info("Notification de fin de garde envoyée pour %d vin(s)", len(choisis))
    return len(choisis)


JOURS_AVANT_OCCASION = 7


def verifier_occasions(app, aujourdhui=None):
    """Note personnelle datée (« À boire pour un anniversaire », le 12 mars) : une notification 7 jours avant.
    Un seul rappel par date. Renvoie le nombre de vins signalés."""
    reglages = app.reglages()
    service = reglages.get("notif_service") or ""
    if not service:
        return 0
    aujourdhui = aujourdhui or date.today()
    choisis = []
    for v in cave.lister_vins(app.db, {"stock": "1"}):
        if not v.get("note_perso") or not v.get("note_date") or v.get("note_rappel") == v["note_date"]:
            continue
        try:
            jour = date.fromisoformat(v["note_date"])
        except ValueError:
            continue
        if 0 <= (jour - aujourdhui).days <= JOURS_AVANT_OCCASION:
            choisis.append((v, jour))
    for v, jour in choisis:
        dans = (jour - aujourdhui).days
        quand = "aujourd'hui" if dans == 0 else "demain" if dans == 1 else f"dans {dans} jours"
        titre = f"📌 {v['note_perso']} : {quand}"
        message = (f"Pensez à sortir {v['nom']}{' ' + str(v['millesime']) if v['millesime'] else ''} "
                   f"pour le {jour.strftime('%d/%m')}.")
        envoyer(reglages, service, titre, message)
        with app.db.transaction() as conn:
            conn.execute("UPDATE vins SET note_rappel = ? WHERE id = ?", (v["note_date"], v["id"]))
    if choisis:
        log.info("Rappel d'occasion envoyé pour %d vin(s)", len(choisis))
    return len(choisis)


class Surveillance:
    """Tâche de fond : vérifie toutes les 6 heures s'il faut prévenir d'un vin en fin de garde."""

    def __init__(self, app, intervalle=6 * 3600):
        self.app = app
        self.intervalle = intervalle
        self._arret = threading.Event()

    def demarrer(self):
        threading.Thread(target=self._boucle, name="alertes-fin", daemon=True).start()

    def arreter(self):
        self._arret.set()

    def _boucle(self):
        self._arret.wait(60)
        while not self._arret.is_set():
            for tache, nom in ((verifier, "de fin de garde"), (verifier_occasions, "d'occasion")):
                try:
                    tache(self.app)
                except Exception as e:  # noqa: BLE001 - on réessaiera au prochain passage
                    log.warning("Notification %s impossible : %s", nom, e)
            self._arret.wait(self.intervalle)
