"""Logique métier de la cave : vins, bouteilles, mouvements, garde, accords, statistiques."""

import csv
import io
import json
import re
from datetime import datetime, date

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
                "format", "fournisseur", "accords", "notes", "code_barre", "note_perso", "note_date"]
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


# Valeur approximative d'une unité de chaque devise en euros : sert seulement à situer un prix sur les paliers ci-dessous.
TAUX_EUR = {"EUR": 1.0, "USD": 0.92, "GBP": 1.17, "CHF": 1.05, "DKK": 0.134}


def niveau_du_vin(appellation="", region="", prix=None, devise="EUR"):
    """Devine le potentiel de garde : d'abord par le prix, sinon par l'appellation."""
    if prix:
        prix = float(prix) * TAUX_EUR.get(devise, 1.0)
        return "courant" if prix < 10 else "moyen" if prix < 25 else "garde" if prix < 80 else "grand"
    texte = f" {appellation or ''} ".lower()
    if any(m in texte for m in APPELLATIONS_GARDE):
        return "garde"
    if any(m in texte for m in APPELLATIONS_MOYEN):
        return "moyen"
    if any(m in texte for m in APPELLATIONS_COURANT) or texte.strip() == "bordeaux":
        return "courant"
    return "moyen" if (region or "").strip() else "courant"


# Accords mets-vins. « couleurs » : poids de chaque type de vin (0 à 3) ; « mots » : appellations, régions et cépages
# qui s'accordent ; « synonymes » : mots du plat recherchés dans les accords notés sur la fiche du vin (souvent par l'IA).
PLATS = {
    "boeuf": {"label": "Bœuf", "icone": "🥩", "couleurs": {"rouge": 3},
              "mots": ["médoc", "medoc", "pauillac", "saint-julien", "saint-estèphe", "margaux", "graves", "bordeaux",
                       "cabernet", "syrah", "malbec", "cahors", "madiran", "côtes-du-rhône", "cotes-du-rhone"],
              "synonymes": ["bœuf", "boeuf", "entrecôte", "entrecote", "steak", "côte de bœuf", "viande rouge", "rôti"]},
    "agneau": {"label": "Agneau", "icone": "🐑", "couleurs": {"rouge": 3, "rose": 1},
               "mots": ["pauillac", "saint-julien", "bordeaux", "grenache", "bandol", "rhône", "rhone", "languedoc",
                        "rioja", "cabernet"],
               "synonymes": ["agneau", "gigot", "souris d'agneau", "côtelettes"]},
    "canard": {"label": "Canard", "icone": "🦆", "couleurs": {"rouge": 3},
               "mots": ["madiran", "cahors", "saint-émilion", "saint-emilion", "pomerol", "merlot", "pinot noir", "bourgogne",
                        "côtes-du-rhône", "gaillac", "fronton", "marcillac", "tannat"],
               "synonymes": ["canard", "magret", "confit", "aiguillettes", "parmentier de canard"]},
    "gibier": {"label": "Gibier", "icone": "🦌", "couleurs": {"rouge": 3},
               "mots": ["pomerol", "saint-émilion", "côte-rôtie", "cote-rotie", "hermitage", "cornas", "syrah",
                        "châteauneuf", "chateauneuf", "gevrey", "nuits", "pommard", "bandol", "mourvèdre"],
               "synonymes": ["gibier", "chevreuil", "sanglier", "biche", "lièvre", "faisan", "civet"]},
    "volaille": {"label": "Volaille", "icone": "🍗", "couleurs": {"rouge": 2, "blanc": 2},
                 "mots": ["bourgogne", "pinot", "beaujolais", "gamay", "chardonnay", "morgon", "fleurie", "jura",
                          "mâcon", "macon", "chinon", "saumur"],
                 "synonymes": ["volaille", "poulet", "dinde", "chapon", "pintade", "viande blanche",
                               "poulet rôti", "volaille rôtie", "rôti de dinde", "dinde rôtie"]},
    "porc": {"label": "Porc & charcuterie", "icone": "🥓", "couleurs": {"rouge": 2, "rose": 2, "blanc": 1},
             "mots": ["beaujolais", "gamay", "morgon", "côtes-du-rhône", "alsace", "pinot", "chinon", "saumur", "savoie"],
             "synonymes": ["porc", "charcuterie", "saucisse", "jambon", "filet mignon", "travers", "choucroute",
                           "rôti de porc", "porc rôti"]},
    "poisson": {"label": "Poisson", "icone": "🐟", "couleurs": {"blanc": 3, "rose": 1},
                "mots": ["chablis", "sancerre", "pouilly", "sauvignon", "chardonnay", "loire", "muscadet", "meursault",
                         "graves", "entre-deux-mers"],
                "synonymes": ["poisson", "saumon", "cabillaud", "sole", "bar", "dorade", "lotte", "truite"]},
    "fruits_de_mer": {"label": "Fruits de mer", "icone": "🦐", "couleurs": {"blanc": 3, "effervescent": 2},
                      "mots": ["muscadet", "chablis", "picpoul", "riesling", "entre-deux-mers", "sancerre", "champagne"],
                      "synonymes": ["fruits de mer", "huîtres", "huitres", "crustacés", "homard", "crevettes", "moules",
                                    "langoustines", "coquilles"]},
    "foie_gras": {"label": "Foie gras", "icone": "🍯", "couleurs": {"liquoreux": 3, "effervescent": 1, "blanc": 1},
                  "mots": ["sauternes", "loupiac", "barsac", "jurançon", "jurancon", "monbazillac", "gewurztraminer",
                           "vendanges tardives", "coteaux du layon"],
                  "synonymes": ["foie gras"]},
    "fromage": {"label": "Fromages", "icone": "🧀", "couleurs": {"rouge": 2, "blanc": 2, "liquoreux": 1},
                "mots": ["jura", "savagnin", "bourgogne", "sauternes", "comté", "vin jaune", "chinon", "saint-joseph"],
                "synonymes": ["fromage", "comté", "camembert", "roquefort", "chèvre", "plateau de fromages"]},
    "pates_pizza": {"label": "Pâtes & pizza", "icone": "🍕", "couleurs": {"rouge": 2, "rose": 2},
                    "mots": ["chianti", "sangiovese", "italie", "côtes-du-rhône", "languedoc", "provence", "grenache"],
                    "synonymes": ["pâtes", "pates", "pizza", "lasagnes", "bolognaise", "risotto"]},
    "epice": {"label": "Épicé & exotique", "icone": "🌶️", "couleurs": {"blanc": 2, "rose": 2},
              "mots": ["gewurztraminer", "alsace", "riesling", "pinot gris", "vouvray"],
              "synonymes": ["épicé", "epice", "curry", "asiatique", "exotique", "thaï", "indien"]},
    "vegetarien": {"label": "Végétarien", "icone": "🥗", "couleurs": {"blanc": 2, "rose": 2, "rouge": 1},
                   "mots": ["loire", "gamay", "pinot", "sauvignon"],
                   "synonymes": ["légumes", "legumes", "végétarien", "salade", "tarte salée"]},
    "dessert": {"label": "Dessert", "icone": "🍰", "couleurs": {"liquoreux": 3, "effervescent": 2},
                "mots": ["sauternes", "muscat", "banyuls", "maury", "champagne", "loupiac", "rivesaltes"],
                "synonymes": ["dessert", "chocolat", "tarte", "fruits", "gâteau"]},
    "aperitif": {"label": "Apéritif", "icone": "🥂", "couleurs": {"effervescent": 3, "blanc": 1, "rose": 1},
                 "mots": ["champagne", "crémant", "cremant", "prosecco", "blanquette"],
                 "synonymes": ["apéritif", "aperitif", "amuse-bouche"]},
}
# anciens noms (scripts Home Assistant existants)
PLATS_ALIAS = {"viande_rouge": "boeuf", "viande_blanche": "volaille", "barbecue": "boeuf"}
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
    if propre.get("note_date") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", propre["note_date"]):
        raise ErreurAPI("Date de la note invalide")
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


def estimer_garde(couleur, millesime, region="", appellation="", prix=None, annee_achat=None, devise="EUR"):
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
    niveau = niveau_du_vin(appellation, region, prix, devise)
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
    if filtres.get("millesime"):
        if filtres["millesime"] in ("—", "aucun"):
            where.append("v.millesime IS NULL")
        else:
            where.append("v.millesime = ?")
            params.append(_entier(filtres["millesime"], "millesime"))
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
                    _entier(data.get("rangee"), "rangee"), _entier(data.get("colonne"), "colonne"), _emplacements(data))
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

# Disposition d'un casier : une ou plusieurs profondeurs (rang de devant, rangs derrière), chacune avec sa largeur
# (bouteilles côte à côte), sa hauteur (bouteilles empilées) et son empilement (aligné, ou décalé d'une demi-bouteille
# vers la gauche ou la droite, en quinconce). Sans disposition, un casier est une simple grille rangées × colonnes,
# c'est-à-dire une seule profondeur alignée.
# Adresse d'une place : colonne = position dans la largeur ; rangee = (profondeur - 1) × 100 + étage (1 = en haut).
# Le rang de devant garde donc exactement les adresses d'une grille simple.
PAS_PROFONDEUR = 100
EMPILEMENTS = ("aligne", "gauche", "droite")
# sens des bouteilles dans un rang : goulot vers soi (avant), fond vers soi (arrière), alternés, ou allongées de côté
SENS = ("avant", "arriere", "alterne_avant", "alterne_arriere", "allonge_droite", "allonge_gauche",
        "allonge_alterne", "allonge_alterne_inverse")
PROFONDEURS_MAX = 4


def profondeurs(cave):
    brut = cave["disposition"] if "disposition" in cave.keys() else None
    if brut:
        try:
            liste = json.loads(brut).get("profondeurs") or []
            if liste:
                return liste
        except (ValueError, AttributeError):
            pass
    if cave["rangees"] and cave["colonnes"]:
        return [{"largeur": cave["colonnes"], "hauteur": cave["rangees"], "empilement": "aligne"}]
    return []


def cases(cave):
    """Toutes les places d'un casier, du rang de devant au fond, de haut en bas, de gauche à droite
    (sans les emplacements retirés : coins d'un casier en diagonale, montant…)."""
    return [((p * PAS_PROFONDEUR) + n, c) for p, prof in enumerate(profondeurs(cave))
            for n in range(1, prof["hauteur"] + 1) for c in range(1, prof["largeur"] + 1)
            if [n, c] not in (prof.get("sans") or [])]


def _nettoyer_disposition(brut):
    """Vérifie une disposition envoyée par l'application ; renvoie (json, rangees, colonnes) pour la table caves."""
    liste = brut.get("profondeurs") if isinstance(brut, dict) else brut
    if not isinstance(liste, list) or not 1 <= len(liste) <= PROFONDEURS_MAX:
        raise ErreurAPI(f"Un casier a de 1 à {PROFONDEURS_MAX} profondeurs")
    propres = []
    for prof in liste:
        if not isinstance(prof, dict):
            raise ErreurAPI("Disposition invalide")
        largeur = _entier(prof.get("largeur"), "largeur") or 0
        hauteur = _entier(prof.get("hauteur"), "hauteur") or 0
        if not (1 <= largeur <= 50 and 1 <= hauteur <= 50):
            raise ErreurAPI("Largeur et hauteur : de 1 à 50 bouteilles")
        empilement = prof.get("empilement") or "aligne"
        if empilement not in EMPILEMENTS:
            raise ErreurAPI("Empilement : aligné, décalé à gauche ou décalé à droite")
        sens = prof.get("sens") or "avant"
        if sens not in SENS:
            raise ErreurAPI("Sens des bouteilles inconnu")
        propre = {"largeur": largeur, "hauteur": hauteur, "empilement": empilement}
        if sens != "avant":
            propre["sens"] = sens
        # emplacements retirés : [étage, colonne] (étage 1 = en haut), pour un casier en diagonale par exemple
        sans = []
        for e in prof.get("sans") or []:
            try:
                etage, col = int(e[0]), int(e[1])
            except (TypeError, ValueError, IndexError):
                raise ErreurAPI("Emplacement retiré invalide") from None
            if 1 <= etage <= hauteur and 1 <= col <= largeur and [etage, col] not in sans:
                sans.append([etage, col])
        if len(sans) >= largeur * hauteur:
            raise ErreurAPI("Il doit rester au moins un emplacement dans chaque rang")
        if sans:
            propre["sans"] = sorted(sans)
        propres.append(propre)
    rangees = max(p * PAS_PROFONDEUR + prof["hauteur"] for p, prof in enumerate(propres))
    colonnes = max(prof["largeur"] for prof in propres)
    simple = len(propres) == 1 and propres[0]["empilement"] == "aligne" and "sens" not in propres[0] and "sans" not in propres[0]
    return (None if simple else json.dumps({"profondeurs": propres})), rangees, colonnes


def _cases_libres(conn, cave_id, n):
    cave = conn.execute("SELECT * FROM caves WHERE id = ?", (cave_id,)).fetchone()
    if not cave:
        raise ErreurAPI("Cave introuvable", 404)
    if not cave["rangees"] or not cave["colonnes"]:
        return [(None, None)] * n  # cave « en vrac », sans plan
    occupees = {(r, c) for r, c in conn.execute(
        "SELECT rangee, colonne FROM bouteilles WHERE cave_id = ? AND rangee IS NOT NULL", (cave_id,))}
    libres = [x for x in cases(cave) if x not in occupees]
    if len(libres) < n:
        raise ErreurAPI(f"Plus assez de place dans « {cave['nom']} » ({len(libres)} emplacement(s) libre(s))", 409)
    return libres[:n]


def _emplacements(data):
    """Emplacements choisis sur le plan : [{cave_id, rangee, colonne}, …] (cave ou étagère)."""
    liste = data.get("emplacements") or []
    if not isinstance(liste, list):
        raise ErreurAPI("Emplacements invalides")
    propres = []
    for e in liste:
        if not isinstance(e, dict):
            raise ErreurAPI("Emplacements invalides")
        cle = (_entier(e.get("cave_id"), "cave_id"), _entier(e.get("rangee"), "rangee"), _entier(e.get("colonne"), "colonne"))
        if not all(cle):
            raise ErreurAPI("Emplacement incomplet")
        if cle in propres:
            raise ErreurAPI("Le même emplacement est choisi deux fois")
        propres.append(cle)
    return propres


def _entree(conn, vin_id, quantite, cave_id, raison, jour, commentaire="", rangee=None, colonne=None, emplacements=()):
    vin = conn.execute("SELECT nom, millesime FROM vins WHERE id = ?", (vin_id,)).fetchone()
    if not vin:
        raise ErreurAPI("Vin introuvable", 404)
    if emplacements:
        # bouteilles posées sur les emplacements cliqués ; s'il en reste, dans les cases libres du premier casier
        if len(emplacements) > quantite:
            raise ErreurAPI(f"{len(emplacements)} emplacements choisis pour {quantite} bouteille(s)")
        for c_id, r, c in emplacements:
            _verifier_case(conn, c_id, r, c)
        places = list(emplacements)
        if quantite > len(places):
            premier = places[0][0]
            libres = [x for x in _cases_libres(conn, premier, quantite)
                      if (premier, *x) not in places][:quantite - len(places)]
            places += [(premier, r, c) for r, c in libres]
        for c_id, r, c in places:
            conn.execute("INSERT INTO bouteilles (vin_id, cave_id, rangee, colonne, date_entree) VALUES (?, ?, ?, ?, ?)",
                         (vin_id, c_id, r, c, jour))
        conn.execute("""INSERT INTO mouvements (vin_id, vin_nom, millesime, type, quantite, raison, commentaire, date)
                        VALUES (?, ?, ?, 'entree', ?, ?, ?, ?)""",
                     (vin_id, vin["nom"], vin["millesime"], quantite, raison, commentaire, jour))
        return
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
    if (rangee, colonne) not in set(cases(cave)):
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
                _entier(data.get("rangee"), "rangee"), _entier(data.get("colonne"), "colonne"), _emplacements(data))
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
        retirees = [dict(r) for r in conn.execute(
            f"SELECT id, cave_id, rangee, colonne, date_entree FROM bouteilles WHERE id IN ({','.join('?' * len(ids))})", ids)]
        annulation = {"bouteilles": retirees}
        if data.get("effacer_note"):
            ancienne = conn.execute("SELECT note_perso, note_date FROM vins WHERE id = ?", (vin_id,)).fetchone()
            annulation["note"] = {"note_perso": ancienne["note_perso"], "note_date": ancienne["note_date"]}
            conn.execute("UPDATE vins SET note_perso = '', note_date = '', note_rappel = '' WHERE id = ?", (vin_id,))
        conn.executemany("DELETE FROM bouteilles WHERE id = ?", [(i,) for i in ids])
        cur = conn.execute("""INSERT INTO mouvements (vin_id, vin_nom, millesime, type, quantite, raison, note, commentaire, date,
                                                      annulation, cree_le)
                              VALUES (?, ?, ?, 'sortie', ?, ?, ?, ?, ?, ?, ?)""",
                           (vin_id, vin["nom"], vin["millesime"], quantite, raison, note,
                            (data.get("commentaire") or "").strip(), data.get("date") or maintenant()[:10],
                            json.dumps(annulation), maintenant()))
    resultat = lire_vin(db, vin_id)
    resultat["mouvement_id"] = cur.lastrowid
    return resultat


DELAI_ANNULATION = 30 * 60  # secondes pendant lesquelles une sortie peut être annulée


def annuler_sortie(db, mouvement_id):
    """Remet les bouteilles sorties à leur place exacte (ou en vrac dans la même cave si la place a été reprise),
    rétablit la note personnelle si elle avait été effacée, et retire la sortie de l'historique."""
    with db.transaction() as conn:
        m = conn.execute("SELECT * FROM mouvements WHERE id = ?", (mouvement_id,)).fetchone()
        if not m or m["type"] != "sortie" or not m["annulation"]:
            raise ErreurAPI("Cette sortie ne peut pas être annulée", 404)
        try:
            ecart = (datetime.fromisoformat(maintenant()) - datetime.fromisoformat(m["cree_le"])).total_seconds()
        except (TypeError, ValueError):
            ecart = DELAI_ANNULATION + 1
        if ecart > DELAI_ANNULATION:
            raise ErreurAPI("Trop tard pour annuler cette sortie : ajoutez la bouteille à la main", 409)
        infos = json.loads(m["annulation"])
        for b in infos["bouteilles"]:
            libre = b["rangee"] is None or not conn.execute(
                "SELECT 1 FROM bouteilles WHERE cave_id = ? AND rangee = ? AND colonne = ?",
                (b["cave_id"], b["rangee"], b["colonne"])).fetchone()
            existe_cave = b["cave_id"] is None or conn.execute("SELECT 1 FROM caves WHERE id = ?", (b["cave_id"],)).fetchone()
            conn.execute("INSERT INTO bouteilles (vin_id, cave_id, rangee, colonne, date_entree) VALUES (?, ?, ?, ?, ?)",
                         (m["vin_id"], b["cave_id"] if existe_cave else None,
                          b["rangee"] if libre and existe_cave else None, b["colonne"] if libre and existe_cave else None,
                          b["date_entree"]))
        if infos.get("note"):
            conn.execute("UPDATE vins SET note_perso = ?, note_date = ? WHERE id = ?",
                         (infos["note"]["note_perso"], infos["note"]["note_date"], m["vin_id"]))
        conn.execute("DELETE FROM mouvements WHERE id = ?", (mouvement_id,))
    return lire_vin(db, m["vin_id"])


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


# une cave « en vrac » n'a ni rangées ni colonnes (voir _cases_libres) : ses bouteilles sont rangées, sans case
SANS_PLAN_EXCLU = "(c.id IS NULL OR (COALESCE(c.rangees, 0) > 0 AND COALESCE(c.colonnes, 0) > 0))"


def bouteilles_sans_emplacement(db):
    """Bouteilles sans cave, ou dans une cave à plan mais sans case : candidates pour une case libre du plan.
    Celles d'une cave « en vrac » (sans plan) sont rangées : elles ne comptent pas ici."""
    lignes = db.all(f"""SELECT b.id, b.vin_id, b.cave_id, {NOM_COMPLET} AS cave_nom, v.nom, v.millesime, v.couleur,
                              v.appellation, v.region, v.cepages, v.domaine, v.updated_at, COALESCE(v.photo, '') <> '' AS a_photo
                       FROM bouteilles b JOIN vins v ON v.id = b.vin_id LEFT JOIN caves c ON c.id = b.cave_id
                       LEFT JOIN caves p ON p.id = c.parent_id
                       WHERE b.rangee IS NULL AND {SANS_PLAN_EXCLU} ORDER BY LOWER(v.nom), v.millesime, b.id""")
    for l in lignes:
        l["a_photo"] = bool(l["a_photo"])
    return lignes


# ---------------------------------------------------------------- filtre à charbon des caves électriques
JOURS_AVANT_FILTRE = 14  # rappel deux semaines avant l'échéance


def _ajouter_mois(jour, mois):
    a, m = divmod(jour.month - 1 + mois, 12)
    annee, mois_ = jour.year + a, m + 1
    fin = [31, 29 if annee % 4 == 0 and (annee % 100 or annee % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mois_ - 1]
    return date(annee, mois_, min(jour.day, fin))


def etat_filtres(db, aujourdhui=None):
    """Caves équipées d'un filtre à charbon : dernier remplacement, échéance et jours restants (négatif = en retard)."""
    aujourdhui = aujourdhui or date.today()
    lignes = db.all(f"""SELECT c.id, c.parent_id, c.nom, c.nom_casier, c.filtre_mois, c.filtre_date, c.filtre_rappel,
                               {NOM_COMPLET} AS nom_complet
                        FROM caves c LEFT JOIN caves p ON p.id = c.parent_id WHERE c.filtre_mois > 0 ORDER BY c.id""")
    etats = []
    for c in lignes:
        nom = c["nom_complet"] if c["parent_id"] else (c["nom_casier"] or c["nom"])
        echeance = jours = None
        if c["filtre_date"]:
            try:
                echeance = _ajouter_mois(date.fromisoformat(c["filtre_date"]), c["filtre_mois"])
                jours = (echeance - aujourdhui).days
            except ValueError:
                pass
        etats.append({"cave_id": c["id"], "nom": nom, "mois": c["filtre_mois"], "dernier": c["filtre_date"] or None,
                      "echeance": echeance.isoformat() if echeance else None, "jours": jours,
                      "a_changer": jours is None or jours <= JOURS_AVANT_FILTRE, "rappel": c["filtre_rappel"]})
    return etats


def regler_filtre(db, cave_id, data):
    """Durée de vie du filtre (en mois, 0 = pas de filtre) et date du dernier remplacement."""
    if not db.one("SELECT id FROM caves WHERE id = ?", (cave_id,)):
        raise ErreurAPI("Cave introuvable", 404)
    with db.transaction() as conn:
        if "filtre_mois" in data:
            mois = _entier(data.get("filtre_mois"), "filtre_mois") or 0
            if not 0 <= mois <= 60:
                raise ErreurAPI("Durée du filtre : de 1 à 60 mois (0 = pas de filtre)")
            conn.execute("UPDATE caves SET filtre_mois = ? WHERE id = ?", (mois, cave_id))
        if "filtre_date" in data:
            jour = (data.get("filtre_date") or "").strip()
            if jour:
                try:
                    if date.fromisoformat(jour) > date.today():
                        raise ErreurAPI("La date du dernier remplacement ne peut pas être dans le futur")
                except ValueError:
                    raise ErreurAPI("Date du dernier remplacement invalide") from None
            conn.execute("UPDATE caves SET filtre_date = ?, filtre_rappel = '' WHERE id = ?", (jour, cave_id))


def remplacer_filtre(db, cave_id, jour=None):
    """« Filtre remplacé » : enregistre la date (aujourd'hui par défaut) et la garde dans l'historique."""
    cave = db.one("SELECT id, filtre_mois FROM caves WHERE id = ?", (cave_id,))
    if not cave:
        raise ErreurAPI("Cave introuvable", 404)
    jour = jour or date.today().isoformat()
    try:
        date.fromisoformat(jour)
    except ValueError:
        raise ErreurAPI("Date invalide") from None
    with db.transaction() as conn:
        conn.execute("UPDATE caves SET filtre_date = ?, filtre_rappel = '', filtre_mois = CASE WHEN filtre_mois > 0 "
                     "THEN filtre_mois ELSE 12 END WHERE id = ?", (jour, cave_id))
        conn.execute("INSERT INTO filtres (cave_id, date) VALUES (?, ?)", (cave_id, jour))
    return next(f for f in etat_filtres(db) if f["cave_id"] == cave_id)


def historique_filtre(db, cave_id):
    return [l["date"] for l in db.all("SELECT date FROM filtres WHERE cave_id = ? ORDER BY date DESC, id DESC", (cave_id,))]


POSITIONS = {"bas": "en bas", "haut": "en haut", "gauche": "à gauche", "droite": "à droite"}
# nom d'une étagère sans nom : d'après sa position (Armoire · étagère du bas)
NOM_ETAGERE = ("CASE WHEN c.nom <> '' THEN c.nom ELSE 'étagère ' || CASE c.position WHEN 'haut' THEN 'du haut' "
               "WHEN 'gauche' THEN 'de gauche' WHEN 'droite' THEN 'de droite' ELSE 'du bas' END END")
NOM_COMPLET = f"CASE WHEN p.id IS NULL THEN c.nom ELSE p.nom || ' · ' || {NOM_ETAGERE} END"


def lister_caves(db):
    """Toutes les caves et étagères. Pour une cave principale, « bouteilles » et « capacite » comptent aussi ses
    étagères ; « nom_complet » nomme une étagère avec sa cave (Armoire · Étagère 2)."""
    caves = db.all(f"""SELECT c.*, {NOM_COMPLET} AS nom_complet, COUNT(b.id) AS bouteilles_propres
                       FROM caves c LEFT JOIN caves p ON p.id = c.parent_id
                       LEFT JOIN bouteilles b ON b.cave_id = c.id GROUP BY c.id ORDER BY nom_complet""")
    for c in caves:
        c["capacite_propre"] = len(cases(_Ligne(c)))
    for c in caves:
        groupe = [c] + ([x for x in caves if x["parent_id"] == c["id"]] if not c["parent_id"] else [])
        c["bouteilles"] = sum(x["bouteilles_propres"] for x in groupe)
        c["capacite"] = sum(x["capacite_propre"] for x in groupe)
    return caves


def _lire_casier(db, cave_id):
    cave = db.one("SELECT * FROM caves WHERE id = ?", (cave_id,))
    if not cave:
        raise ErreurAPI("Cave introuvable", 404)
    cave["profondeurs"] = profondeurs(_Ligne(cave))
    cave["capacite"] = len(cases(_Ligne(cave)))
    annee = annee_courante()
    bouteilles = db.all(
        """SELECT b.id, b.rangee, b.colonne, b.vin_id, b.cave_id, v.nom, v.millesime, v.couleur, v.domaine,
                  v.appellation, v.region, v.cepages, v.format, v.updated_at, COALESCE(v.photo, '') <> '' AS a_photo,
                  v.garde_debut, v.garde_apogee, v.garde_fin
           FROM bouteilles b JOIN vins v ON v.id = b.vin_id
           WHERE b.cave_id = ? ORDER BY b.rangee, b.colonne, v.nom""", (cave_id,))
    for b in bouteilles:
        b["statut"] = statut_garde(b, annee)
        b["a_photo"] = bool(b["a_photo"])
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


class _Ligne(dict):
    """Un dict lu en base, utilisable comme une ligne sqlite (méthode keys et accès par clé)."""


def _nettoyer_cave(data, etagere=False):
    nom = (data.get("nom") or "").strip()
    if not nom and not etagere:  # le nom d'une étagère est facultatif
        raise ErreurAPI("Le nom de la cave est obligatoire")
    rangees = _entier(data.get("rangees"), "rangees") or 0
    colonnes = _entier(data.get("colonnes"), "colonnes") or 0
    if not (0 <= rangees <= 100 and 0 <= colonnes <= 100):
        raise ErreurAPI("Le plan est limité à 100 rangées × 100 colonnes")
    disposition = None
    if data.get("disposition"):
        disposition, rangees, colonnes = _nettoyer_disposition(data["disposition"])
    return nom, rangees, colonnes, (data.get("description") or "").strip(), disposition


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
    nom, rangees, colonnes, description, disposition = _nettoyer_cave(data, etagere)
    if etagere and not (rangees and colonnes):
        raise ErreurAPI("Une étagère a au moins une rangée et une colonne")
    refrigere = 1 if data.get("refrigere") in (True, 1, "1", "true", "oui") else 0
    with db.transaction() as conn:
        if etagere:
            cur = conn.execute("INSERT INTO caves (nom, rangees, colonnes, description, created_at, parent_id, position, ref_id, refrigere, disposition) "
                               "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                               (nom, rangees, colonnes, description, maintenant(), parent_id, position, ref_id, refrigere, disposition))
        else:
            cur = conn.execute("INSERT INTO caves (nom, rangees, colonnes, description, created_at, refrigere, disposition) VALUES (?, ?, ?, ?, ?, ?, ?)",
                               (nom, rangees, colonnes, description, maintenant(), refrigere, disposition))
    return lire_cave(db, cur.lastrowid)


def modifier_cave(db, cave_id, data):
    actuelle = _lire_casier(db, cave_id)
    if not any(k in data for k in ("disposition", "rangees", "colonnes")):
        # simple changement de nom ou de description : la disposition du casier reste celle d'avant
        data = ({**data, "disposition": json.loads(actuelle["disposition"])} if actuelle.get("disposition")
                else {**data, "rangees": actuelle["rangees"], "colonnes": actuelle["colonnes"]})
    nom, rangees, colonnes, description, disposition = _nettoyer_cave(data, bool(actuelle["parent_id"]))
    if actuelle["parent_id"] and not (rangees and colonnes):
        raise ErreurAPI("Une étagère a au moins une rangée et une colonne")
    nouvelles = set(cases(_Ligne(rangees=rangees, colonnes=colonnes, disposition=disposition)))
    with db.transaction() as conn:
        # aucune bouteille ne doit se retrouver hors du nouveau plan (rien n'est déplacé sans le demander)
        hors_plan = sum(1 for r, c in conn.execute(
            "SELECT rangee, colonne FROM bouteilles WHERE cave_id = ? AND rangee IS NOT NULL", (cave_id,))
            if (r, c) not in nouvelles)
        if hors_plan and rangees and colonnes:
            raise ErreurAPI(f"{hors_plan} bouteille(s) se trouvent en dehors du nouveau plan : déplacez-les d'abord", 409)
        if not rangees or not colonnes:
            conn.execute("UPDATE bouteilles SET rangee = NULL, colonne = NULL WHERE cave_id = ?", (cave_id,))
        conn.execute("UPDATE caves SET nom = ?, rangees = ?, colonnes = ?, description = ?, disposition = ? WHERE id = ?",
                     (nom, rangees, colonnes, description, disposition, cave_id))
        if "refrigere" in data:
            conn.execute("UPDATE caves SET refrigere = ? WHERE id = ?",
                         (1 if data["refrigere"] in (True, 1, "1", "true", "oui") else 0, cave_id))
        if not actuelle["parent_id"] and "nom_casier" in data:
            conn.execute("UPDATE caves SET nom_casier = ? WHERE id = ?", ((data.get("nom_casier") or "").strip()[:60], cave_id))
        if actuelle["parent_id"] and data.get("position") in POSITIONS:
            conn.execute("UPDATE caves SET position = ? WHERE id = ?", (data["position"], cave_id))
        if actuelle["parent_id"] and data.get("ref_id") not in (None, ""):
            ref_id = _entier(data.get("ref_id"), "ref_id")
            parent = actuelle["parent_id"]
            if ref_id != parent and not conn.execute("SELECT id FROM caves WHERE id = ? AND parent_id = ?", (ref_id, parent)).fetchone():
                raise ErreurAPI("Casier de référence inconnu")
            # pas de boucle : la référence ne doit pas dépendre de cette étagère
            suivant, vus = ref_id, set()
            while suivant and suivant != parent and suivant not in vus:
                if suivant == cave_id:
                    raise ErreurAPI("Une étagère ne peut pas être placée par rapport à elle-même ou à une étagère qui dépend d'elle")
                vus.add(suivant)
                ligne = conn.execute("SELECT ref_id FROM caves WHERE id = ?", (suivant,)).fetchone()
                suivant = ligne["ref_id"] if ligne else None
            conn.execute("UPDATE caves SET ref_id = ? WHERE id = ?", (ref_id, cave_id))
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

_LETTRE = "a-zà-ÿœæ"
_TOUS_LES_MOTS = None


def _mots_trouves(mots, texte):
    """Mots (ou expressions) présents dans le texte en tant que mots entiers, au pluriel près : « bar » ne se trouve
    pas dans « barbecue ». Les expressions les plus longues de tous les plats passent d'abord et masquent leurs
    morceaux : « fruits de mer » n'est pas compté comme « fruits » (dessert), ni « poulet rôti » comme « rôti »."""
    global _TOUS_LES_MOTS
    if _TOUS_LES_MOTS is None:
        _TOUS_LES_MOTS = sorted({m for r in PLATS.values() for m in (*r["mots"], *r["synonymes"])}, key=len, reverse=True)
    voulus, trouves = set(mots), []
    for m in _TOUS_LES_MOTS:
        motif = rf"(?<![{_LETTRE}]){re.escape(m)}(?:s|x)?(?![{_LETTRE}])"
        if re.search(motif, texte):
            if m in voulus:
                trouves.append(m)
            texte = re.sub(motif, " ", texte)  # l'expression est prise : ses morceaux ne comptent plus
    return [m for m in mots if m in trouves]


def _accord(regle, vin):
    """Note de l'accord entre un plat et un vin (0 à 100) et ce qui la justifie."""
    poids = regle["couleurs"].get(vin["couleur"], 0)
    texte = " ".join(str(vin.get(c) or "") for c in ("region", "appellation", "cepages", "nom", "domaine")).lower()
    accords = (vin.get("accords") or "").lower()
    mots = _mots_trouves(regle["mots"], texte)
    cites = _mots_trouves(regle["synonymes"], accords)
    note = poids * 15 + min(len(mots), 2) * 12 + (31 if cites else 0)
    raisons = []
    if cites:
        raisons.append(f"conseillé avec : {cites[0]}")
    if mots:
        raisons.append("accord : " + ", ".join(dict.fromkeys(mots)))
    return min(note, 100), raisons


def suggerer(db, plat=None, couleur=None, limite=5):
    plat = PLATS_ALIAS.get(plat, plat)
    if plat and plat not in PLATS:
        raise ErreurAPI("Plat inconnu")
    regle = PLATS.get(plat) if plat else None
    resultats = []
    for vin in lister_vins(db, {"stock": "1", "couleur": couleur or ""}):
        if vin["statut"] == "trop_jeune":
            continue
        maturite = BONUS_MATURITE.get(vin["statut"], 0) + (1 if vin["favori"] else 0)
        raisons = []
        note = None
        if regle:
            note, raisons = _accord(regle, vin)
            if note < 15:  # couleur qui ne convient pas et aucun indice d'accord
                continue
        raisons.append(vin["statut_label"])
        # l'accord d'abord ; la maturité départage les vins aussi bien accordés
        score = (note or 0) * 10 + maturite
        resultats.append({"score": score, "accord": note, "raisons": raisons, "vin": vin})
    resultats.sort(key=lambda r: (-r["score"], r["vin"]["garde_fin"] or 9999))
    return resultats[:max(1, min(int(limite or 5), 50))]


# --------------------------------------------------------------------------- statistiques

def candidats_cave(db, limite=None):
    """Bouteilles à mettre en priorité dans une cave électrique, une par vin.
    Candidates : les bouteilles non rangées et celles des casiers non réfrigérés (jamais celles d'un réfrigérateur,
    qu'on va boire, ni celles déjà en cave électrique). Priorité : les vins qui profitent le plus d'une garde stable,
    c'est-à-dire ceux qui ont le plus d'années de garde devant eux, puis les plus précieux. La température de service
    (un blanc ou un champagne se boit frais) n'entre pas en compte."""
    annee = annee_courante()
    lignes = db.all(f"""SELECT b.id AS bouteille_id, b.rangee IS NOT NULL AS a_deplacer,
                               CASE WHEN c.id IS NULL THEN '' ELSE {NOM_COMPLET} END AS depuis,
                               v.id AS vin_id, v.nom, v.millesime, v.appellation, v.region, v.cepages, v.domaine, v.couleur, v.updated_at,
                               COALESCE(v.photo, '') <> '' AS a_photo, v.garde_debut, v.garde_apogee, v.garde_fin,
                               COALESCE(v.valeur, v.prix_achat) AS valeur
                        FROM bouteilles b JOIN vins v ON v.id = b.vin_id
                        LEFT JOIN caves c ON c.id = b.cave_id LEFT JOIN caves p ON p.id = c.parent_id
                        WHERE b.rangee IS NULL
                           OR (COALESCE(c.refrigere, 0) = 0
                               AND LOWER(COALESCE(c.nom, '') || ' ' || COALESCE(c.nom_casier, '')) NOT LIKE '%frig%')
                        ORDER BY b.rangee IS NOT NULL, b.id""")
    par_vin = {}
    for l in lignes:
        par_vin.setdefault(l["vin_id"], {**l, "nombre": 0})["nombre"] += 1
    candidats = []
    for c in par_vin.values():
        c["a_deplacer"], c["a_photo"] = bool(c["a_deplacer"]), bool(c["a_photo"])
        c["statut"] = statut_garde(c, annee)
        if c["statut"] == "depasse":
            continue  # à boire tout de suite, inutile de le mettre en cave
        reste = max(0, min((c["garde_fin"] or annee + 3) - annee, 30))  # sans garde connue : 3 ans par défaut
        valeur = c["valeur"] or 0
        c["priorite"] = round(reste * 4 + min(valeur, 200) / 5, 1)
        raisons = []
        if c["garde_fin"]:
            raisons.append(f"se garde jusqu'en {c['garde_fin']}" if reste >= 3 else f"à boire d'ici {c['garde_fin']}")
        c["raisons"] = raisons
        candidats.append(c)
    candidats.sort(key=lambda c: (-c["priorite"], c["a_deplacer"], c["nom"].lower()))  # à prix égal, les non rangées d'abord
    return candidats[:limite] if limite else candidats


def place_libre(db):
    """Première cave électrique (casier réfrigéré) qui a des places libres, et la bouteille la plus prioritaire à y
    mettre (voir candidats_cave). None s'il n'y a rien à proposer."""
    candidats = candidats_cave(db, 1)
    if not candidats:
        return None
    suggestion = candidats[0]
    casiers = db.all("""SELECT c.id, c.nom, c.nom_casier, c.parent_id, c.position, c.rangees, c.colonnes, c.disposition,
                               COALESCE(p.nom, c.nom) AS cave_nom, COALESCE(c.parent_id, c.id) AS cave_id,
                               (SELECT COUNT(*) FROM bouteilles b WHERE b.cave_id = c.id AND b.rangee IS NOT NULL) AS occupees
                        FROM caves c LEFT JOIN caves p ON p.id = c.parent_id
                        WHERE c.rangees > 0 AND c.colonnes > 0 AND c.refrigere = 1  -- seules les caves électriques
                        ORDER BY COALESCE(c.parent_id, c.id), c.parent_id IS NOT NULL, c.id""")
    for k in casiers:
        k["capacite"] = len(cases(_Ligne(k)))
    for k in casiers:
        libres = k["capacite"] - k["occupees"]
        if libres > 0:
            if k["parent_id"]:
                nom = k["nom"] or "étagère " + {"haut": "du haut", "gauche": "de gauche", "droite": "de droite"}.get(k["position"], "du bas")
                nom = f"{k['cave_nom']} · {nom}"
            else:
                nom = k["nom_casier"] or k["nom"]
            return {"cave_id": k["cave_id"], "casier_id": k["id"], "casier_nom": nom, "libres": libres,
                    "total_libres": sum(max(0, x["capacite"] - x["occupees"]) for x in casiers), "suggestion": suggestion}
    return None


def statistiques(db):
    annee = annee_courante()
    vins = lister_vins(db, {"stock": "1"})
    total = sum(v["stock"] for v in vins)
    valeur = sum((v["valeur_unitaire"] or 0) * v["stock"] for v in vins)
    paye = sum((v["prix_achat"] or 0) * v["stock"] for v in vins)
    sans_prix = sum(v["stock"] for v in vins if v["prix_achat"] is None)

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
        return {k: v[k] for k in ("id", "nom", "domaine", "appellation", "region", "cepages", "format", "millesime", "couleur",
                                  "stock", "garde_debut", "garde_apogee", "garde_fin", "statut", "statut_label",
                                  "note_perso", "note_date")}

    urgents = sorted([v for v in vins if v["statut"] in ("urgent", "depasse")],
                     key=lambda v: v["garde_fin"] or 0)
    a_boire = sorted([v for v in vins if v["statut"] in ("declin", "apogee", "a_boire")],
                     key=lambda v: (v["garde_fin"] or 9999, v["nom"].lower()))
    debut_mois = date.today().replace(day=1).isoformat()
    debut_annee = date(annee, 1, 1).isoformat()
    caves = lister_caves(db)
    non_rangees = db.scalar("SELECT COUNT(*) FROM bouteilles WHERE cave_id IS NULL") or 0
    sans_emplacement = db.scalar(f"""SELECT COUNT(*) FROM bouteilles b LEFT JOIN caves c ON c.id = b.cave_id
                                    WHERE b.rangee IS NULL AND {SANS_PLAN_EXCLU}""") or 0  # hors cave, ou en cave à plan sans case
    return {
        "annee": annee,
        "bouteilles": total,
        "references": len(vins),
        "sans_emplacement": sans_emplacement,
        "place_libre": place_libre(db),
        "valeur": round(valeur, 2),
        "valeur_payee": round(paye, 2),
        "sans_prix_achat": sans_prix,
        "par_couleur": repartition("couleur", COULEURS),
        "par_region": repartition("region")[:12],
        "par_millesime": sorted(repartition("millesime"), key=lambda l: str(l["cle"])),
        "par_statut": [{"cle": k, "label": STATUTS[k], "bouteilles": n} for k, n in par_statut.items()],
        "par_cave": [{"id": c["id"], "nom": c["nom"], "bouteilles": c["bouteilles"], "capacite": c["capacite"]}
                     for c in caves if not c["parent_id"]] + ([{"id": None, "nom": "Non rangées", "bouteilles": non_rangees, "capacite": 0}]
                                        if non_rangees else []),
        "urgents": [resume(v) for v in urgents],
        # vins réservés pour une occasion (note personnelle), les plus proches d'abord
        "occasions": [resume(v) for v in sorted((v for v in vins if v.get("note_perso")),
                                                key=lambda v: (v.get("note_date") or "9999", v["nom"].lower()))],
        "a_boire": [resume(v) for v in a_boire],
        "entrees_mois": db.scalar("SELECT COALESCE(SUM(quantite), 0) FROM mouvements WHERE type = 'entree' AND date >= ?",
                                  (debut_mois,)),
        "sorties_mois": db.scalar("SELECT COALESCE(SUM(quantite), 0) FROM mouvements WHERE type = 'sortie' AND date >= ?",
                                  (debut_mois,)),
        "bues_annee": db.scalar("""SELECT COALESCE(SUM(quantite), 0) FROM mouvements
                                   WHERE type = 'sortie' AND raison = 'bue' AND date >= ?""", (debut_annee,)),
        "derniers_mouvements": db.all("SELECT * FROM mouvements ORDER BY date DESC, id DESC LIMIT 10"),
        "envies": db.scalar("SELECT COUNT(*) FROM envies WHERE fait = 0"),
        "filtres": [{k: f[k] for k in ("cave_id", "nom", "mois", "dernier", "echeance", "jours", "a_changer")} for f in etat_filtres(db)],
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


TABLES_SAUVEGARDE = ["caves", "filtres", "vins", "bouteilles", "mouvements", "envies"]


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
