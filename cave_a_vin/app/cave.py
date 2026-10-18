"""Logique métier de la cave : vins, bouteilles, mouvements, garde, accords, statistiques."""

import csv
import io
import re
from datetime import date

from .db import maintenant

COULEURS = {
    "rouge": "Rouge",
    "blanc": "Blanc",
    "rose": "Rosé",
    "effervescent": "Effervescent",
    "liquoreux": "Liquoreux / moelleux",
    "autre": "Autre",
}

STATUTS = {
    "trop_jeune": "À garder",
    "a_boire": "Prêt à boire",
    "apogee": "À l'apogée",
    "declin": "Après l'apogée",
    "urgent": "À boire vite",
    "depasse": "Garde dépassée",
    "inconnu": "Garde non renseignée",
}
# Origine de la fenêtre de garde : l'IA ne remplace jamais une garde saisie à la main.
SOURCES_GARDE = {"": "Non estimée", "estimation": "Estimation automatique", "ia": "Estimée par l'IA",
                 "manuel": "Saisie à la main"}
CHAMPS_GARDE = ("garde_debut", "garde_apogee", "garde_fin")

RAISONS_ENTREE = {"achat": "Achat", "cadeau": "Cadeau", "inventaire": "Inventaire", "autre": "Autre"}
RAISONS_SORTIE = {"bue": "Bue", "offerte": "Offerte", "cassee": "Cassée / bouchonnée", "vendue": "Vendue", "autre": "Autre"}

CHAMPS_TEXTE = ["nom", "domaine", "appellation", "region", "pays", "couleur", "cepages",
                "format", "fournisseur", "accords", "notes", "code_barre"]
CHAMPS_ENTIERS = ["millesime", "garde_debut", "garde_apogee", "garde_fin"]
CHAMPS_REELS = ["degre", "prix_achat", "valeur"]
CHAMPS_VIN = CHAMPS_TEXTE + CHAMPS_ENTIERS + CHAMPS_REELS + ["favori"]

# Garde indicative en années après le millésime : (début, apogée, fin), selon le « niveau » du vin.
NIVEAUX = {
    "courant": "vin de tous les jours",
    "moyen": "vin de moyenne garde",
    "garde": "vin de garde",
    "grand": "grand vin de garde",
}
GARDE = {
    "rouge": {"courant": (1, 2, 5), "moyen": (3, 5, 9), "garde": (5, 10, 18), "grand": (8, 15, 30)},
    "blanc": {"courant": (0, 1, 3), "moyen": (1, 3, 6), "garde": (3, 6, 12), "grand": (5, 10, 20)},
    "rose": {"courant": (0, 1, 2), "moyen": (0, 1, 2), "garde": (1, 3, 5), "grand": (1, 3, 6)},
    "effervescent": {"courant": (0, 1, 3), "moyen": (1, 3, 6), "garde": (3, 7, 12), "grand": (5, 10, 20)},
    "liquoreux": {"courant": (2, 5, 10), "moyen": (4, 10, 20), "garde": (6, 15, 30), "grand": (10, 25, 50)},
}
# Appellations réputées pour la garde (sans prix connu, on reste prudent : « garde », jamais « grand »).
APPELLATIONS_GARDE = [
    "pauillac", "margaux", "saint-julien", "saint-estèphe", "saint-estephe", "pessac-léognan", "pessac-leognan",
    "pomerol", "saint-émilion grand cru", "saint-emilion grand cru", "hermitage", "côte-rôtie", "cote-rotie",
    "cornas", "châteauneuf-du-pape", "chateauneuf-du-pape", "bandol", "madiran", "grand cru", "premier cru",
    "1er cru", "sauternes", "barsac", "château-chalon", "chateau-chalon", "vin jaune", "barolo", "barbaresco",
    "brunello", "rioja gran reserva", "vintage", "porto",
]
APPELLATIONS_MOYEN = [
    "haut-médoc", "haut-medoc", "médoc", "medoc", "graves", "saint-émilion", "saint-emilion", "listrac", "moulis",
    "fronsac", "côtes de bourg", "cotes de bourg", "blaye", "castillon", "cahors", "gigondas", "vacqueyras",
    "crozes-hermitage", "saint-joseph", "chinon", "bourgueil", "saumur-champigny", "morgon", "moulin-à-vent",
    "moulin-a-vent", "chablis", "meursault", "pouilly-fuissé", "pouilly-fuisse", "savennières", "savennieres",
    "vouvray", "faugères", "faugeres", "pic saint-loup", "corbières-boutenac", "minervois-la-livinière", "irouléguy",
    "jurançon", "jurancon", "champagne",
]
APPELLATIONS_COURANT = [
    "bordeaux supérieur", "bordeaux superieur", "côtes-du-rhône", "cotes-du-rhone", "côtes du rhône",
    "vin de france", "igp", "pays d'oc", "vin de pays", "beaujolais", "bergerac", "côtes de gascogne",
    "cotes de gascogne", "muscadet", "touraine", "anjou", "crémant", "cremant",
]


def niveau_du_vin(appellation="", region="", prix=None):
    """Devine le potentiel de garde : d'abord par le prix, sinon par l'appellation."""
    if prix:
        prix = float(prix)
        return "courant" if prix < 10 else "moyen" if prix < 25 else "garde" if prix < 80 else "grand"
    texte = f" {appellation or ''} ".lower()
    if any(m in texte for m in APPELLATIONS_GARDE):
        return "garde"
    if any(m in texte for m in APPELLATIONS_MOYEN):
        return "moyen"
    if any(m in texte for m in APPELLATIONS_COURANT) or texte.strip() == "bordeaux":
        return "courant"
    return "moyen" if (region or "").strip() else "courant"


PLATS = {
    "viande_rouge": {"label": "Viande rouge / gibier", "couleurs": {"rouge": 3},
                     "mots": ["bordeaux", "rhône", "rhone", "syrah", "cabernet", "madiran", "cahors", "malbec"]},
    "viande_blanche": {"label": "Volaille / viande blanche", "couleurs": {"rouge": 2, "blanc": 2},
                       "mots": ["bourgogne", "pinot", "chardonnay", "beaujolais", "gamay"]},
    "poisson": {"label": "Poisson", "couleurs": {"blanc": 3, "rose": 1},
                "mots": ["loire", "chablis", "sauvignon", "chardonnay", "bourgogne"]},
    "fruits_de_mer": {"label": "Fruits de mer / crustacés", "couleurs": {"blanc": 3, "effervescent": 2},
                      "mots": ["muscadet", "chablis", "picpoul", "riesling", "entre-deux-mers", "sancerre"]},
    "fromage": {"label": "Fromages", "couleurs": {"rouge": 2, "blanc": 2, "liquoreux": 1},
                "mots": ["jura", "savagnin", "bourgogne", "sauternes", "comté"]},
    "dessert": {"label": "Dessert", "couleurs": {"liquoreux": 3, "effervescent": 2},
                "mots": ["sauternes", "muscat", "banyuls", "maury", "champagne", "loupiac"]},
    "aperitif": {"label": "Apéritif", "couleurs": {"effervescent": 3, "blanc": 1, "rose": 1},
                 "mots": ["champagne", "crémant", "cremant"]},
    "epice": {"label": "Cuisine épicée / exotique", "couleurs": {"blanc": 2, "rose": 2},
              "mots": ["gewurztraminer", "alsace", "riesling", "pinot gris"]},
    "barbecue": {"label": "Barbecue / grillades", "couleurs": {"rouge": 2, "rose": 3},
                 "mots": ["provence", "rhône", "rhone", "grenache", "syrah", "languedoc"]},
    "vegetarien": {"label": "Végétarien", "couleurs": {"blanc": 2, "rose": 2, "rouge": 1},
                   "mots": ["loire", "gamay", "pinot"]},
}
BONUS_MATURITE = {"urgent": 8, "declin": 7, "apogee": 6, "depasse": 5, "a_boire": 4, "inconnu": 1}


class ErreurAPI(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


# --------------------------------------------------------------------------- outils

def _entier(v, champ):
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        raise ErreurAPI(f"« {champ} » doit être un nombre entier")


def _reel(v, champ):
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        raise ErreurAPI(f"« {champ} » doit être un nombre")


def annee_courante():
    return date.today().year


def nettoyer_vin(data, partiel=False):
    propre = {}
    for champ in CHAMPS_VIN:
        if partiel and champ not in data:
            continue
        v = data.get(champ)
        if champ in CHAMPS_TEXTE:
            propre[champ] = ("" if v is None else str(v)).strip()
        elif champ in CHAMPS_ENTIERS:
            propre[champ] = _entier(v, champ)
        elif champ in CHAMPS_REELS:
            propre[champ] = _reel(v, champ)
        elif champ == "favori":
            propre[champ] = 1 if v in (True, 1, "1", "true", "oui") else 0
    if propre.get("code_barre"):
        propre["code_barre"] = re.sub(r"\D", "", propre["code_barre"])
    if "nom" in propre and not propre["nom"]:
        raise ErreurAPI("Le nom du vin est obligatoire")
    if "couleur" in propre:
        propre["couleur"] = propre["couleur"].lower() or "rouge"
        if propre["couleur"] not in COULEURS:
            raise ErreurAPI(f"Couleur inconnue : {propre['couleur']}")
    if not partiel:
        propre["pays"] = propre.get("pays") or "France"
        propre["format"] = propre.get("format") or "75 cl"
    return propre


def plateau_apogee(apogee, fin):
    """Années où le vin est à son sommet : de l'apogée jusqu'à environ 40 % du temps restant avant la fin."""
    if not apogee:
        return None
    duree = max(1, round(((fin or apogee) - apogee) * 0.4))
    return apogee, apogee + duree - 1


def statut_garde(vin, annee=None):
    annee = annee or annee_courante()
    debut, apogee, fin = vin.get("garde_debut"), vin.get("garde_apogee"), vin.get("garde_fin")
    if not debut and not fin:
        return "inconnu"
    if debut and annee < debut:
        return "trop_jeune"
    if fin and annee > fin:
        return "depasse"
    if fin and annee == fin:
        return "urgent"
    plateau = plateau_apogee(apogee, fin)
    if plateau and annee > plateau[1]:
        return "declin"
    if plateau and annee >= plateau[0]:
        return "apogee"
    return "a_boire"


def estimer_garde(couleur, millesime, region="", appellation="", prix=None, annee_achat=None):
    """Fenêtre de dégustation indicative, à affiner par l'utilisateur.

    Sans millésime (vin non millésimé, ou millésime inconnu), la garde est comptée à partir de l'année
    d'achat : le vin est supposé prêt à boire à sa mise en vente, et il garde le même potentiel
    (apogée et fin) qu'un vin millésimé du même niveau. Un champagne de grande maison reste ainsi
    « à garder » plusieurs années, un rosé courant est à boire dans l'année ou la suivante.
    """
    millesime = int(millesime) if millesime else None
    profil = GARDE.get(couleur)
    if not profil:
        return {"garde_debut": None, "garde_apogee": None, "garde_fin": None, "niveau": None}
    niveau = niveau_du_vin(appellation, region, prix)
    d, a, f = profil[niveau]
    resultat = {"niveau": niveau, "niveau_label": NIVEAUX[niveau]}
    if millesime is None:
        base = int(annee_achat) if annee_achat else annee_courante()
        return {**resultat, "garde_debut": base, "garde_apogee": base + max(0, a - d), "garde_fin": base + (f - d),
                "reference": "achat", "annee_reference": base}
    return {**resultat, "garde_debut": millesime + d, "garde_apogee": millesime + a, "garde_fin": millesime + f,
            "reference": "millesime", "annee_reference": millesime}


def _enrichir(vin, annee=None):
    vin["statut"] = statut_garde(vin, annee)
    vin["statut_label"] = STATUTS[vin["statut"]]
    vin["couleur_label"] = COULEURS.get(vin["couleur"], vin["couleur"])
    vin["valeur_unitaire"] = vin["valeur"] if vin["valeur"] is not None else vin["prix_achat"]
    vin["favori"] = bool(vin["favori"])
    vin["a_photo"] = bool(vin.pop("photo", None))
    vin["a_photo_originale"] = bool(vin.pop("photo_originale", None))
    return vin


# --------------------------------------------------------------------------- vins

SELECT_VIN = """
SELECT v.*, COUNT(b.id) AS stock
FROM vins v LEFT JOIN bouteilles b ON b.vin_id = v.id
"""


def lister_vins(db, filtres):
    where, params = [], []
    q = (filtres.get("q") or "").strip().lower()
    if q:
        for mot in q.split():
            where.append("(LOWER(v.nom || ' ' || v.domaine || ' ' || v.appellation || ' ' || v.region || ' ' || v.cepages"
                         " || ' ' || v.pays || ' ' || IFNULL(v.millesime, '') || ' ' || v.code_barre) LIKE ?)")
            params.append(f"%{mot}%")
    for champ in ("couleur", "region", "pays", "appellation"):
        if filtres.get(champ):
            where.append(f"v.{champ} = ?")
            params.append(filtres[champ])
    if filtres.get("favori") in ("1", "true"):
        where.append("v.favori = 1")
    if filtres.get("cave_id"):
        where.append("v.id IN (SELECT vin_id FROM bouteilles WHERE cave_id IN "
                     "(SELECT id FROM caves WHERE id = ? OR parent_id = ?))")  # la cave et ses étagères
        params += [_entier(filtres["cave_id"], "cave_id")] * 2
    sql = SELECT_VIN + (" WHERE " + " AND ".join(where) if where else "") + " GROUP BY v.id"
    stock = filtres.get("stock", "1")
    if stock == "1":
        sql += " HAVING stock > 0"
    elif stock == "0":
        sql += " HAVING stock = 0"
    tri = {
        "nom": "LOWER(v.nom), v.millesime",
        "millesime": "v.millesime IS NULL, v.millesime, LOWER(v.nom)",
        "region": "LOWER(v.region), LOWER(v.nom)",
        "stock": "stock DESC, LOWER(v.nom)",
        "recent": "v.created_at DESC",
        "garde": "v.garde_fin IS NULL, v.garde_fin, LOWER(v.nom)",
        "valeur": "COALESCE(v.valeur, v.prix_achat) IS NULL, COALESCE(v.valeur, v.prix_achat) DESC",
    }.get(filtres.get("tri") or "nom", "LOWER(v.nom), v.millesime")
    sql += " ORDER BY " + tri
    annee = annee_courante()
    vins = [_enrichir(v, annee) for v in db.all(sql, params)]
    if filtres.get("statut"):
        statuts = set(filtres["statut"].split(","))
        vins = [v for v in vins if v["statut"] in statuts]
    return vins


def lire_vin(db, vin_id, details=True):
    vin = db.one(SELECT_VIN + " WHERE v.id = ? GROUP BY v.id", (vin_id,))
    if not vin:
        raise ErreurAPI("Vin introuvable", 404)
    vin = _enrichir(vin)
    if details:
        vin["bouteilles"] = db.all(
            f"""SELECT b.*, {NOM_COMPLET} AS cave_nom, COALESCE(c.parent_id, c.id) AS cave_racine FROM bouteilles b
               LEFT JOIN caves c ON c.id = b.cave_id LEFT JOIN caves p ON p.id = c.parent_id
               WHERE b.vin_id = ? ORDER BY cave_nom, b.rangee, b.colonne, b.id""", (vin_id,))
        vin["mouvements"] = db.all(
            "SELECT * FROM mouvements WHERE vin_id = ? ORDER BY date DESC, id DESC", (vin_id,))
        notes = [m["note"] for m in vin["mouvements"] if m["note"] is not None]
        vin["note_moyenne"] = round(sum(notes) / len(notes), 1) if notes else None
    return vin


def vin_par_code_barre(db, code):
    code = (code or "").strip()
    if not code:
        return None
    vin = db.one(SELECT_VIN + " WHERE v.code_barre = ? GROUP BY v.id ORDER BY v.id DESC", (code,))
    return _enrichir(vin) if vin else None


def _source_garde(data, defaut):
    source = data.get("garde_source")
    return source if source in SOURCES_GARDE else defaut


def creer_vin(db, data):
    vin = nettoyer_vin(data)
    vin["garde_source"] = _source_garde(data, "manuel" if any(vin.get(c) for c in CHAMPS_GARDE) else "")
    quantite = _entier(data.get("quantite"), "quantite") or 0
    if quantite < 0:
        raise ErreurAPI("La quantité doit être positive")
    cave_id = _entier(data.get("cave_id"), "cave_id")
    now = maintenant()
    vin["created_at"] = vin["updated_at"] = now
    with db.transaction() as conn:
        cols = ", ".join(vin)
        cur = conn.execute(f"INSERT INTO vins ({cols}) VALUES ({', '.join('?' * len(vin))})",
                           list(vin.values()))
        vin_id = cur.lastrowid
        if quantite:
            _entree(conn, vin_id, quantite, cave_id, data.get("raison") or "achat",
                    data.get("date") or now[:10], data.get("commentaire") or "",
                    _entier(data.get("rangee"), "rangee"), _entier(data.get("colonne"), "colonne"))
    return lire_vin(db, vin_id)


def modifier_vin(db, vin_id, data):
    actuel = lire_vin(db, vin_id, details=False)
    vin = nettoyer_vin(data, partiel=True)
    if "garde_source" in data and data["garde_source"] in SOURCES_GARDE:
        vin["garde_source"] = data["garde_source"]
    elif any(c in vin and vin[c] != actuel[c] for c in CHAMPS_GARDE):
        vin["garde_source"] = "manuel"  # fenêtre corrigée à la main : l'IA n'y touchera plus
    if vin:
        vin["updated_at"] = maintenant()
        with db.transaction() as conn:
            conn.execute(f"UPDATE vins SET {', '.join(f'{k} = ?' for k in vin)} WHERE id = ?",
                         [*vin.values(), vin_id])
    return lire_vin(db, vin_id)


def supprimer_vin(db, vin_id):
    """Supprime le vin et renvoie les noms de ses fichiers photo, à effacer."""
    vin = db.one("SELECT photo, photo_originale FROM vins WHERE id = ?", (vin_id,))
    if not vin:
        raise ErreurAPI("Vin introuvable", 404)
    with db.transaction() as conn:
        conn.execute("DELETE FROM vins WHERE id = ?", (vin_id,))
    return [n for n in vin.values() if n]


# --------------------------------------------------------------------------- caves & emplacements

def _cases_libres(conn, cave_id, n):
    cave = conn.execute("SELECT * FROM caves WHERE id = ?", (cave_id,)).fetchone()
    if not cave:
        raise ErreurAPI("Cave introuvable", 404)
    if not cave["rangees"] or not cave["colonnes"]:
        return [(None, None)] * n  # cave « en vrac », sans plan
    occupees = {(r, c) for r, c in conn.execute(
        "SELECT rangee, colonne FROM bouteilles WHERE cave_id = ? AND rangee IS NOT NULL", (cave_id,))}
    libres = [(r, c) for r in range(1, cave["rangees"] + 1) for c in range(1, cave["colonnes"] + 1)
              if (r, c) not in occupees]
    if len(libres) < n:
        raise ErreurAPI(f"Plus assez de place dans « {cave['nom']} » ({len(libres)} emplacement(s) libre(s))", 409)
    return libres[:n]


def _entree(conn, vin_id, quantite, cave_id, raison, jour, commentaire="", rangee=None, colonne=None):
    vin = conn.execute("SELECT nom, millesime FROM vins WHERE id = ?", (vin_id,)).fetchone()
    if not vin:
        raise ErreurAPI("Vin introuvable", 404)
    if cave_id and rangee and colonne:
        # la première bouteille va dans la case choisie, les suivantes dans les premières cases libres
        _verifier_case(conn, cave_id, rangee, colonne)
        cases = [(rangee, colonne)]
        if quantite > 1:
            cases += [c for c in _cases_libres(conn, cave_id, quantite) if c != (rangee, colonne)][:quantite - 1]
    elif cave_id:
        cases = _cases_libres(conn, cave_id, quantite)
    else:
        cases = [(None, None)] * quantite
    for r, c in cases:
        conn.execute("INSERT INTO bouteilles (vin_id, cave_id, rangee, colonne, date_entree) VALUES (?, ?, ?, ?, ?)",
                     (vin_id, cave_id, r, c, jour))
    conn.execute("""INSERT INTO mouvements (vin_id, vin_nom, millesime, type, quantite, raison, commentaire, date)
                    VALUES (?, ?, ?, 'entree', ?, ?, ?, ?)""",
                 (vin_id, vin["nom"], vin["millesime"], quantite, raison, commentaire, jour))


def _verifier_case(conn, cave_id, rangee, colonne, ignorer_bouteille=None):
    cave = conn.execute("SELECT * FROM caves WHERE id = ?", (cave_id,)).fetchone()
    if not cave:
        raise ErreurAPI("Cave introuvable", 404)
    if not (1 <= rangee <= cave["rangees"] and 1 <= colonne <= cave["colonnes"]):
        raise ErreurAPI("Emplacement hors du plan de la cave")
    occupant = conn.execute("SELECT id FROM bouteilles WHERE cave_id = ? AND rangee = ? AND colonne = ?",
                            (cave_id, rangee, colonne)).fetchone()
    if occupant and occupant["id"] != ignorer_bouteille:
        raise ErreurAPI("Cet emplacement est déjà occupé", 409)


def ajouter_bouteilles(db, vin_id, data):
    quantite = _entier(data.get("quantite"), "quantite") or 1
    if quantite < 1 or quantite > 500:
        raise ErreurAPI("Quantité invalide")
    raison = data.get("raison") or "achat"
    if raison not in RAISONS_ENTREE:
        raise ErreurAPI("Raison d'entrée inconnue")
    with db.transaction() as conn:
        _entree(conn, vin_id, quantite, _entier(data.get("cave_id"), "cave_id"), raison,
                data.get("date") or maintenant()[:10], data.get("commentaire") or "",
                _entier(data.get("rangee"), "rangee"), _entier(data.get("colonne"), "colonne"))
    return lire_vin(db, vin_id)


def sortir_bouteilles(db, vin_id, data):
    quantite = _entier(data.get("quantite"), "quantite") or 1
    raison = data.get("raison") or "bue"
    if raison not in RAISONS_SORTIE:
        raise ErreurAPI("Raison de sortie inconnue")
    note = _reel(data.get("note"), "note")
    if note is not None and not 0 <= note <= 5:
        raise ErreurAPI("La note doit être comprise entre 0 et 5")
    bouteille_id = _entier(data.get("bouteille_id"), "bouteille_id")
    with db.transaction() as conn:
        vin = conn.execute("SELECT nom, millesime FROM vins WHERE id = ?", (vin_id,)).fetchone()
        if not vin:
            raise ErreurAPI("Vin introuvable", 404)
        if bouteille_id:
            ids = [r[0] for r in conn.execute("SELECT id FROM bouteilles WHERE id = ? AND vin_id = ?",
                                              (bouteille_id, vin_id))]
            if not ids:
                raise ErreurAPI("Bouteille introuvable", 404)
            quantite = 1
        else:
            # On sort d'abord les bouteilles non rangées, puis les plus récemment entrées.
            ids = [r[0] for r in conn.execute(
                """SELECT id FROM bouteilles WHERE vin_id = ?
                   ORDER BY (rangee IS NOT NULL), id DESC LIMIT ?""", (vin_id, quantite))]
            if len(ids) < quantite or quantite < 1:
                raise ErreurAPI(f"Stock insuffisant ({len(ids)} bouteille(s) en cave)", 409)
        conn.executemany("DELETE FROM bouteilles WHERE id = ?", [(i,) for i in ids])
        conn.execute("""INSERT INTO mouvements (vin_id, vin_nom, millesime, type, quantite, raison, note, commentaire, date)
                        VALUES (?, ?, ?, 'sortie', ?, ?, ?, ?, ?)""",
                     (vin_id, vin["nom"], vin["millesime"], quantite, raison, note,
                      (data.get("commentaire") or "").strip(), data.get("date") or maintenant()[:10]))
    return lire_vin(db, vin_id)


def deplacer_bouteille(db, bouteille_id, data):
    cave_id = _entier(data.get("cave_id"), "cave_id")
    rangee, colonne = _entier(data.get("rangee"), "rangee"), _entier(data.get("colonne"), "colonne")
    with db.transaction() as conn:
        if not conn.execute("SELECT 1 FROM bouteilles WHERE id = ?", (bouteille_id,)).fetchone():
            raise ErreurAPI("Bouteille introuvable", 404)
        if cave_id and rangee and colonne:
            _verifier_case(conn, cave_id, rangee, colonne, ignorer_bouteille=bouteille_id)
        elif cave_id:
            rangee, colonne = _cases_libres(conn, cave_id, 1)[0]
        else:
            rangee = colonne = None
        conn.execute("UPDATE bouteilles SET cave_id = ?, rangee = ?, colonne = ? WHERE id = ?",
                     (cave_id, rangee, colonne, bouteille_id))
    return db.one("SELECT * FROM bouteilles WHERE id = ?", (bouteille_id,))


def bouteilles_sans_emplacement(db):
    """Bouteilles non rangées ou rangées « en vrac » : candidates pour une case libre du plan."""
    return db.all(f"""SELECT b.id, b.vin_id, b.cave_id, {NOM_COMPLET} AS cave_nom, v.nom, v.millesime, v.couleur
                     FROM bouteilles b JOIN vins v ON v.id = b.vin_id LEFT JOIN caves c ON c.id = b.cave_id
                     LEFT JOIN caves p ON p.id = c.parent_id
                     WHERE b.rangee IS NULL ORDER BY LOWER(v.nom), v.millesime, b.id""")


POSITIONS = {"bas": "en bas", "haut": "en haut", "gauche": "à gauche", "droite": "à droite"}
NOM_COMPLET = "CASE WHEN p.id IS NULL THEN c.nom ELSE p.nom || ' · ' || c.nom END"


def lister_caves(db):
    """Toutes les caves et étagères. Pour une cave principale, « bouteilles » et « capacite » comptent aussi ses
    étagères ; « nom_complet » nomme une étagère avec sa cave (Armoire · Étagère 2)."""
    caves = db.all(f"""SELECT c.*, {NOM_COMPLET} AS nom_complet, COUNT(b.id) AS bouteilles_propres
                       FROM caves c LEFT JOIN caves p ON p.id = c.parent_id
                       LEFT JOIN bouteilles b ON b.cave_id = c.id GROUP BY c.id ORDER BY nom_complet""")
    for c in caves:
        c["capacite_propre"] = c["rangees"] * c["colonnes"]
    for c in caves:
        groupe = [c] + ([x for x in caves if x["parent_id"] == c["id"]] if not c["parent_id"] else [])
        c["bouteilles"] = sum(x["bouteilles_propres"] for x in groupe)
        c["capacite"] = sum(x["capacite_propre"] for x in groupe)
    return caves


def _lire_casier(db, cave_id):
    cave = db.one("SELECT * FROM caves WHERE id = ?", (cave_id,))
    if not cave:
        raise ErreurAPI("Cave introuvable", 404)
    cave["capacite"] = cave["rangees"] * cave["colonnes"]
    annee = annee_courante()
    bouteilles = db.all(
        """SELECT b.id, b.rangee, b.colonne, b.vin_id, b.cave_id, v.nom, v.millesime, v.couleur, v.domaine,
                  v.garde_debut, v.garde_apogee, v.garde_fin
           FROM bouteilles b JOIN vins v ON v.id = b.vin_id
           WHERE b.cave_id = ? ORDER BY b.rangee, b.colonne, v.nom""", (cave_id,))
    for b in bouteilles:
        b["statut"] = statut_garde(b, annee)
    cave["bouteilles"] = bouteilles
    return cave


def lire_cave(db, cave_id):
    """Une cave avec ses bouteilles ; pour une cave principale, aussi ses étagères (« etageres »)."""
    cave = _lire_casier(db, cave_id)
    cave["etageres"] = []
    if not cave["parent_id"]:
        ids = [r["id"] for r in db.all("SELECT id FROM caves WHERE parent_id = ? ORDER BY id", (cave_id,))]
        cave["etageres"] = [_lire_casier(db, i) for i in ids]
    return cave


def _nettoyer_cave(data):
    nom = (data.get("nom") or "").strip()
    if not nom:
        raise ErreurAPI("Le nom de la cave est obligatoire")
    rangees = _entier(data.get("rangees"), "rangees") or 0
    colonnes = _entier(data.get("colonnes"), "colonnes") or 0
    if not (0 <= rangees <= 100 and 0 <= colonnes <= 100):
        raise ErreurAPI("Le plan est limité à 100 rangées × 100 colonnes")
    return nom, rangees, colonnes, (data.get("description") or "").strip()


def _placement_etagere(db, data):
    """Vérifie où accrocher une étagère : cave principale, casier de référence (la cave ou une de ses étagères)."""
    parent_id = _entier(data.get("parent_id"), "parent_id")
    parent = db.one("SELECT * FROM caves WHERE id = ?", (parent_id,))
    if not parent or parent["parent_id"]:
        raise ErreurAPI("Une étagère s'ajoute à une cave principale")
    ref_id = _entier(data.get("ref_id"), "ref_id") or parent_id
    if ref_id != parent_id and not db.one("SELECT id FROM caves WHERE id = ? AND parent_id = ?", (ref_id, parent_id)):
        raise ErreurAPI("Casier de référence inconnu")
    position = data.get("position") or "bas"
    if position not in POSITIONS:
        raise ErreurAPI("Position : en haut, en bas, à gauche ou à droite")
    return parent_id, ref_id, position


def creer_cave(db, data):
    nom = (data.get("nom") or "").strip()
    etagere = data.get("parent_id") not in (None, "", 0, "0")
    if etagere:
        parent_id, ref_id, position = _placement_etagere(db, data)
        if not nom:
            n = db.scalar("SELECT COUNT(*) FROM caves WHERE parent_id = ?", (parent_id,)) or 0
            data = {**data, "nom": f"Étagère {n + 2}"}
    nom, rangees, colonnes, description = _nettoyer_cave(data)
    if etagere and not (rangees and colonnes):
        raise ErreurAPI("Une étagère a au moins une rangée et une colonne")
    with db.transaction() as conn:
        if etagere:
            cur = conn.execute("INSERT INTO caves (nom, rangees, colonnes, description, created_at, parent_id, position, ref_id) "
                               "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (nom, rangees, colonnes, description, maintenant(), parent_id, position, ref_id))
        else:
            cur = conn.execute("INSERT INTO caves (nom, rangees, colonnes, description, created_at) VALUES (?, ?, ?, ?, ?)",
                               (nom, rangees, colonnes, description, maintenant()))
    return lire_cave(db, cur.lastrowid)


def modifier_cave(db, cave_id, data):
    actuelle = _lire_casier(db, cave_id)
    nom, rangees, colonnes, description = _nettoyer_cave(data)
    if actuelle["parent_id"] and not (rangees and colonnes):
        raise ErreurAPI("Une étagère a au moins une rangée et une colonne")
    with db.transaction() as conn:
        hors_plan = conn.execute(
            "SELECT COUNT(*) FROM bouteilles WHERE cave_id = ? AND (rangee > ? OR colonne > ?)",
            (cave_id, rangees, colonnes)).fetchone()[0]
        if hors_plan and rangees and colonnes:
            raise ErreurAPI(f"{hors_plan} bouteille(s) se trouvent en dehors du nouveau plan : déplacez-les d'abord", 409)
        if not rangees or not colonnes:
            conn.execute("UPDATE bouteilles SET rangee = NULL, colonne = NULL WHERE cave_id = ?", (cave_id,))
        conn.execute("UPDATE caves SET nom = ?, rangees = ?, colonnes = ?, description = ? WHERE id = ?",
                     (nom, rangees, colonnes, description, cave_id))
        if actuelle["parent_id"] and data.get("position") in POSITIONS:
            conn.execute("UPDATE caves SET position = ? WHERE id = ?", (data["position"], cave_id))
    return lire_cave(db, cave_id)


def supprimer_cave(db, cave_id):
    """Supprime une cave (et ses étagères) ou une étagère ; les bouteilles restent dans l'inventaire.
    Les bouteilles d'une étagère supprimée reviennent « en vrac » dans sa cave principale."""
    cave = _lire_casier(db, cave_id)
    with db.transaction() as conn:
        if cave["parent_id"]:
            conn.execute("UPDATE bouteilles SET cave_id = ?, rangee = NULL, colonne = NULL WHERE cave_id = ?",
                         (cave["parent_id"], cave_id))
            conn.execute("UPDATE caves SET ref_id = ? WHERE ref_id = ?", (cave["ref_id"], cave_id))
        else:
            conn.execute("UPDATE bouteilles SET cave_id = NULL, rangee = NULL, colonne = NULL "
                         "WHERE cave_id IN (SELECT id FROM caves WHERE id = ? OR parent_id = ?)", (cave_id, cave_id))
            conn.execute("DELETE FROM caves WHERE parent_id = ?", (cave_id,))
        conn.execute("DELETE FROM caves WHERE id = ?", (cave_id,))


# --------------------------------------------------------------------------- envies (liste d'achats)

def lister_envies(db):
    return [dict(e, fait=bool(e["fait"])) for e in
            db.all("SELECT * FROM envies ORDER BY fait, created_at DESC, id DESC")]


def creer_envie(db, data):
    nom = (data.get("nom") or "").strip()
    if not nom:
        raise ErreurAPI("Le nom est obligatoire")
    with db.transaction() as conn:
        cur = conn.execute("INSERT INTO envies (nom, details, fait, created_at) VALUES (?, ?, 0, ?)",
                           (nom, (data.get("details") or "").strip(), maintenant()))
    return _lire_envie(db, cur.lastrowid)


def _lire_envie(db, envie_id):
    e = db.one("SELECT * FROM envies WHERE id = ?", (envie_id,))
    if not e:
        raise ErreurAPI("Envie introuvable", 404)
    e["fait"] = bool(e["fait"])
    return e


def modifier_envie(db, envie_id, data):
    e = _lire_envie(db, envie_id)
    nom = (data.get("nom", e["nom"]) or "").strip()
    if not nom:
        raise ErreurAPI("Le nom est obligatoire")
    fait = data.get("fait", e["fait"]) in (True, 1, "1", "true")
    with db.transaction() as conn:
        conn.execute("UPDATE envies SET nom = ?, details = ?, fait = ? WHERE id = ?",
                     (nom, (data.get("details", e["details"]) or "").strip(), int(fait), envie_id))
    return _lire_envie(db, envie_id)


def supprimer_envie(db, envie_id):
    _lire_envie(db, envie_id)
    with db.transaction() as conn:
        conn.execute("DELETE FROM envies WHERE id = ?", (envie_id,))


# --------------------------------------------------------------------------- accords & suggestions

def suggerer(db, plat=None, couleur=None, limite=5):
    if plat and plat not in PLATS:
        raise ErreurAPI("Plat inconnu")
    regle = PLATS.get(plat) if plat else None
    resultats = []
    for vin in lister_vins(db, {"stock": "1", "couleur": couleur or ""}):
        if vin["statut"] == "trop_jeune":
            continue
        score = BONUS_MATURITE.get(vin["statut"], 0) + (1 if vin["favori"] else 0)
        raisons = [vin["statut_label"]]
        if regle:
            poids = regle["couleurs"].get(vin["couleur"], 0)
            texte = " ".join([vin["region"], vin["appellation"], vin["cepages"], vin["nom"], vin["accords"]]).lower()
            mots = [m for m in regle["mots"] if m in texte]
            if not poids and not mots:
                continue
            score += poids * 10 + 4 * len(mots)
            if mots:
                raisons.append("accord : " + ", ".join(mots))
        resultats.append({"score": score, "raisons": raisons, "vin": vin})
    resultats.sort(key=lambda r: (-r["score"], r["vin"]["garde_fin"] or 9999))
    return resultats[:max(1, min(int(limite or 5), 50))]


# --------------------------------------------------------------------------- statistiques

def statistiques(db):
    annee = annee_courante()
    vins = lister_vins(db, {"stock": "1"})
    total = sum(v["stock"] for v in vins)
    valeur = sum((v["valeur_unitaire"] or 0) * v["stock"] for v in vins)

    def repartition(cle, libelles=None):
        compte = {}
        for v in vins:
            k = v[cle] if v[cle] not in (None, "") else "—"
            compte[k] = compte.get(k, 0) + v["stock"]
        lignes = [{"cle": k, "label": (libelles or {}).get(k, str(k)), "bouteilles": n} for k, n in compte.items()]
        return sorted(lignes, key=lambda l: -l["bouteilles"])

    par_statut = {k: 0 for k in STATUTS}
    for v in vins:
        par_statut[v["statut"]] += v["stock"]

    def resume(v):
        return {k: v[k] for k in ("id", "nom", "domaine", "appellation", "millesime", "couleur", "stock",
                                  "garde_debut", "garde_apogee", "garde_fin", "statut", "statut_label")}

    urgents = sorted([v for v in vins if v["statut"] in ("urgent", "depasse")],
                     key=lambda v: v["garde_fin"] or 0)
    a_boire = sorted([v for v in vins if v["statut"] in ("declin", "apogee", "a_boire")],
                     key=lambda v: (v["garde_fin"] or 9999, v["nom"].lower()))
    debut_mois = date.today().replace(day=1).isoformat()
    debut_annee = date(annee, 1, 1).isoformat()
    caves = lister_caves(db)
    non_rangees = db.scalar("SELECT COUNT(*) FROM bouteilles WHERE cave_id IS NULL") or 0
    return {
        "annee": annee,
        "bouteilles": total,
        "references": len(vins),
        "valeur": round(valeur, 2),
        "par_couleur": repartition("couleur", COULEURS),
        "par_region": repartition("region")[:12],
        "par_millesime": sorted(repartition("millesime"), key=lambda l: str(l["cle"])),
        "par_statut": [{"cle": k, "label": STATUTS[k], "bouteilles": n} for k, n in par_statut.items()],
        "par_cave": [{"id": c["id"], "nom": c["nom"], "bouteilles": c["bouteilles"], "capacite": c["capacite"]}
                     for c in caves if not c["parent_id"]] + ([{"id": None, "nom": "Non rangées", "bouteilles": non_rangees, "capacite": 0}]
                                        if non_rangees else []),
        "urgents": [resume(v) for v in urgents],
        "a_boire": [resume(v) for v in a_boire],
        "entrees_mois": db.scalar("SELECT COALESCE(SUM(quantite), 0) FROM mouvements WHERE type = 'entree' AND date >= ?",
                                  (debut_mois,)),
        "sorties_mois": db.scalar("SELECT COALESCE(SUM(quantite), 0) FROM mouvements WHERE type = 'sortie' AND date >= ?",
                                  (debut_mois,)),
        "bues_annee": db.scalar("""SELECT COALESCE(SUM(quantite), 0) FROM mouvements
                                   WHERE type = 'sortie' AND raison = 'bue' AND date >= ?""", (debut_annee,)),
        "derniers_mouvements": db.all("SELECT * FROM mouvements ORDER BY date DESC, id DESC LIMIT 10"),
        "envies": db.scalar("SELECT COUNT(*) FROM envies WHERE fait = 0"),
    }


def lister_mouvements(db, limite=200, type_=None):
    if type_ and type_ not in ("entree", "sortie"):
        raise ErreurAPI("Type de mouvement inconnu")
    sql = "SELECT * FROM mouvements" + (" WHERE type = ?" if type_ else "") + " ORDER BY date DESC, id DESC LIMIT ?"
    return db.all(sql, ((type_,) if type_ else ()) + (max(1, min(int(limite), 5000)),))


def autocompletion(db):
    def distinct(col):
        return [r["v"] for r in db.all(f"SELECT DISTINCT {col} AS v FROM vins WHERE {col} != '' ORDER BY {col}")]
    cepages = set()
    for c in distinct("cepages"):
        cepages.update(x.strip() for x in c.split(",") if x.strip())
    return {
        "domaines": distinct("domaine"), "appellations": distinct("appellation"), "regions": distinct("region"),
        "pays": distinct("pays"), "fournisseurs": distinct("fournisseur"), "formats": distinct("format"),
        "cepages": sorted(cepages),
    }


# --------------------------------------------------------------------------- import / export

COLONNES_CSV = ["id"] + CHAMPS_VIN + ["quantite"]


class _PointVirgule(csv.excel):
    delimiter = ";"


def exporter_csv(db):
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=";")
    w.writerow(COLONNES_CSV)
    for v in lister_vins(db, {"stock": "all"}):
        v["quantite"] = v["stock"]
        v["favori"] = int(v["favori"])
        w.writerow(["" if v.get(c) is None else v.get(c) for c in COLONNES_CSV])
    return "﻿" + sortie.getvalue()


def importer_csv(db, texte):
    texte = texte.lstrip("﻿")
    try:
        dialecte = csv.Sniffer().sniff(texte.split("\n", 1)[0], delimiters=";,\t")
    except csv.Error:
        dialecte = _PointVirgule
    lignes = list(csv.DictReader(io.StringIO(texte), dialect=dialecte))
    crees, erreurs = 0, []
    for i, ligne in enumerate(lignes, start=2):
        ligne = {(k or "").strip().lower(): (v or "").strip() for k, v in ligne.items()}
        if not ligne.get("nom"):
            continue
        try:
            creer_vin(db, {**ligne, "raison": "inventaire", "garde_source": ""})  # l'IA pourra affiner
            crees += 1
        except ErreurAPI as e:
            erreurs.append(f"Ligne {i} : {e.message}")
    return {"vins_crees": crees, "erreurs": erreurs}


TABLES_SAUVEGARDE = ["caves", "vins", "bouteilles", "mouvements", "envies"]


def exporter_json(db):
    return {"format": "cave-a-vin", "version": 1, "exporte_le": maintenant(),
            **{t: db.all(f"SELECT * FROM {t} ORDER BY id") for t in TABLES_SAUVEGARDE}}


def importer_json(db, donnees):
    if not isinstance(donnees, dict) or donnees.get("format") != "cave-a-vin":
        raise ErreurAPI("Ce fichier n'est pas une sauvegarde de Tessvine")
    with db.transaction() as conn:
        for t in reversed(TABLES_SAUVEGARDE):
            conn.execute(f"DELETE FROM {t}")
        for t in TABLES_SAUVEGARDE:
            colonnes_valides = {r[1] for r in conn.execute(f"PRAGMA table_info({t})")}
            for ligne in donnees.get(t) or []:
                ligne = {k: v for k, v in ligne.items() if k in colonnes_valides}
                if ligne:
                    conn.execute(f"INSERT INTO {t} ({', '.join(ligne)}) VALUES ({', '.join('?' * len(ligne))})",
                                 list(ligne.values()))
    return {t: len(donnees.get(t) or []) for t in TABLES_SAUVEGARDE}
