"""Lecture d'étiquette par l'IA configurée dans Home Assistant (action ai_task.generate_data).

La photo est déposée temporairement dans le dossier « media » de Home Assistant, puis transmise
à l'IA en pièce jointe. Le fichier est supprimé dès la réponse reçue.
"""

import json
import logging
import os
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import ha
from .cave import COULEURS

log = logging.getLogger("cave_a_vin")
SOUS_DOSSIER = "cave_a_vin"
INSTRUCTIONS = (
    "Tu es sommelier. La photo jointe montre une bouteille de vin. Remplis, en français, la fiche de ce vin "
    "pour l'inventaire d'une cave.\n"
    "1. Recopie ce qui est écrit sur la bouteille (étiquette, contre-étiquette, collerette, capsule) : le nom de la "
    "cuvée ou du château ; le producteur (domaine, château, maison ou négociant : il est souvent écrit en grand, ou "
    "dans la mention « mis en bouteille par… » / « mis en bouteille au château ») ; l'appellation ; le millésime ; "
    "le degré ; la contenance.\n"
    "2. Complète avec tes connaissances ce qui n'est pas écrit mais se déduit : la région viticole et le pays à "
    "partir de l'appellation (Haut-Médoc → Bordeaux, France ; Chablis → Bourgogne) ; la couleur (mention sur "
    "l'étiquette, appellation, cépages, couleur du vin ou de la bouteille) ; les cépages habituels de l'appellation "
    "s'ils ne sont pas indiqués ; un prix de marché indicatif en euros pour une bouteille ; trois à cinq accords "
    "mets-vins ; une description courte du vin.\n"
    "3. Si la cuvée porte le nom du producteur (par exemple « Château Lagrange »), mets ce nom dans les deux champs.\n"
    "Remplis tous les champs que tu peux. Seule exception : n'invente pas de millésime, laisse-le vide s'il n'est "
    "pas lisible."
)
TEXTE = {"text": {}}
STRUCTURE = {
    "nom": {"description": "Nom du vin : château ou cuvée, sans le millésime", "required": True, "selector": TEXTE},
    "domaine": {"description": "Producteur : domaine, château, maison ou négociant", "required": True, "selector": TEXTE},
    "appellation": {"description": "Appellation (AOC/AOP/IGP), par exemple Haut-Médoc", "selector": TEXTE},
    "region": {"description": "Région viticole : Bordeaux, Bourgogne, Loire, Rhône, Alsace, Champagne…",
               "required": True, "selector": TEXTE},
    "pays": {"description": "Pays de production", "required": True, "selector": TEXTE},
    "couleur": {"description": "Type de vin", "required": True, "selector": {"select": {"options": list(COULEURS)}}},
    "millesime": {"description": "Année de récolte, seulement si elle est lisible", "selector": {"number": {"min": 1900, "max": 2100}}},
    "cepages": {"description": "Cépages, indiqués ou habituels pour l'appellation, séparés par des virgules", "selector": TEXTE},
    "degre": {"description": "Degré d'alcool en % vol.", "selector": {"number": {"min": 0, "max": 25, "step": 0.1}}},
    "format": {"description": "Contenance, par exemple 75 cl", "selector": TEXTE},
    "valeur": {"description": "Prix de marché indicatif d'une bouteille, en euros", "selector": {"number": {"min": 0, "max": 100000, "step": 0.5}}},
    "accords": {"description": "Trois à cinq accords mets-vins, séparés par des virgules", "required": True, "selector": TEXTE},
    "description": {"description": "Deux phrases : style du vin, arômes typiques, potentiel", "selector": TEXTE},
}
# Réponses libres de certaines IA ramenées aux couleurs de la cave.
MOTS_COULEURS = [
    ("effervescent", ("efferv", "mousseux", "champagne", "crémant", "cremant", "pétillant", "petillant", "sparkling", "brut")),
    ("liquoreux", ("liquoreux", "moelleux", "doux", "sweet", "vendanges tardives")),
    ("rose", ("rosé", "rose")),
    ("blanc", ("blanc", "white")),
    ("rouge", ("rouge", "red")),
]


def couleur_depuis(texte):
    texte = str(texte or "").strip().lower()
    if texte in COULEURS:
        return texte
    return next((c for c, mots in MOTS_COULEURS if any(m in texte for m in mots)), None)


class IAErreur(Exception):
    pass


def dossier_media():
    """Dossier « media » de Home Assistant, partagé avec le module (map: media)."""
    chemin = os.environ.get("HA_MEDIA_DIR") or ("/media" if ha.mode_addon() else "")
    return Path(chemin) if chemin and Path(chemin).is_dir() else None


def etat(reglages, image=True):
    """Indique si l'IA est utilisable (avec une photo jointe ou non), et sinon pourquoi."""
    if reglages.get("ia_active", "1") != "1":
        return {"possible": False, "raison": "IA désactivée dans les réglages"}
    url, _ = ha.connexion(reglages)
    if not url:
        return {"possible": False, "raison": "Home Assistant n'est pas connecté"}
    if image and not dossier_media():
        return {"possible": False, "raison": "Dossier « media » de Home Assistant inaccessible"}
    return {"possible": True, "entite": reglages.get("ia_entite") or None}


AUCUNE_IA = ("Home Assistant n'a aucune IA de type « tâche IA » : ajoutez une intégration d'IA (OpenAI, Google Gemini, "
             "Anthropic, Ollama…) et, dans ses options, une « tâche IA » (AI Task). La cave l'utilisera automatiquement.")


def entite_a_utiliser(reglages):
    """L'IA choisie dans les réglages, sinon la première IA « tâche IA » disponible dans Home Assistant."""
    if reglages.get("ia_entite"):
        return reglages["ia_entite"]
    disponibles = [e for e in entites(reglages) if e.get("etat") not in ("unavailable", "unknown")]
    return disponibles[0]["entity_id"] if disponibles else None


def _appeler(reglages, corps, timeout):
    """Appelle ai_task.generate_data et renvoie les données structurées de la réponse."""
    url, jeton = ha.connexion(reglages)
    entite = entite_a_utiliser(reglages)
    if entite:
        corps["entity_id"] = entite
    req = urllib.request.Request(f"{url}/services/ai_task/generate_data?return_response", method="POST",
                                 data=json.dumps(corps).encode(),
                                 headers={"Authorization": f"Bearer {jeton}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as rep:
            reponse = json.loads(rep.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        if "entity" in detail.lower():
            if not entite:
                raise IAErreur(AUCUNE_IA)
            raise IAErreur(f"L'IA « {entite} » de Home Assistant est introuvable ou indisponible : "
                           "choisissez-en une autre dans les Réglages de la cave")
        raise IAErreur(f"L'IA de Home Assistant a refusé la demande ({e.code}) : {detail}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise IAErreur(f"Home Assistant injoignable ({getattr(e, 'reason', e)})")
    donnees = (reponse.get("service_response") or {}).get("data")
    if isinstance(donnees, str):  # certaines IA renvoient du JSON sous forme de texte
        try:
            donnees = json.loads(donnees)
        except ValueError:
            raise IAErreur("L'IA n'a pas renvoyé de données exploitables")
    if not isinstance(donnees, dict):
        raise IAErreur("Réponse de l'IA inattendue")
    return donnees


_cache_entites = {"cle": None, "quand": 0.0, "valeur": []}


def entites(reglages, cache_secondes=60):
    """Entités « tâche IA » (ai_task.*) de Home Assistant, mises en cache une minute."""
    url, jeton = ha.connexion(reglages)
    if not url:
        return []
    if _cache_entites["cle"] == url and time.time() - _cache_entites["quand"] < cache_secondes:
        return _cache_entites["valeur"]
    req = urllib.request.Request(f"{url}/states", headers={"Authorization": f"Bearer {jeton}"})
    try:
        with urllib.request.urlopen(req, timeout=8) as rep:
            etats = json.loads(rep.read().decode())
    except (urllib.error.URLError, OSError, ValueError):
        return []
    valeur = [{"entity_id": e["entity_id"], "nom": e.get("attributes", {}).get("friendly_name", e["entity_id"]),
               "etat": e.get("state")}
              for e in etats if e["entity_id"].startswith("ai_task.")]
    _cache_entites.update(cle=url, quand=time.time(), valeur=valeur)
    return valeur


VIDES = ("", "inconnu", "inconnue", "non indiqué", "non indiquée", "n/a", "na", "null", "none", "-", "?")


def _nettoyer(donnees):
    if not isinstance(donnees, dict):
        raise IAErreur("Réponse de l'IA inattendue")
    propre = {}
    for cle in ("nom", "domaine", "appellation", "region", "pays", "cepages", "format", "accords"):
        v = donnees.get(cle)
        if isinstance(v, list):
            v = ", ".join(str(x) for x in v)
        if isinstance(v, str) and v.strip().lower() not in VIDES:
            propre[cle] = v.strip()[:300]
    if couleur := couleur_depuis(donnees.get("couleur")):
        propre["couleur"] = couleur
    for cle, mini, maxi, conv in (("millesime", 1900, 2100, int), ("degre", 3, 25, float), ("valeur", 0.5, 100000, float)):
        try:
            valeur = conv(float(str(donnees.get(cle)).replace(",", ".").replace("€", "").strip()))
        except (TypeError, ValueError):
            continue
        if mini <= valeur <= maxi:
            propre[cle] = round(valeur, 2) if conv is float else valeur
    description = donnees.get("description")
    if isinstance(description, str) and description.strip().lower() not in VIDES:
        propre["notes"] = description.strip()[:600]
    return propre


def lire_etiquette(reglages, image_jpeg, timeout=120):
    possible = etat(reglages)
    if not possible["possible"]:
        raise IAErreur(possible["raison"])
    dossier = dossier_media() / SOUS_DOSSIER
    dossier.mkdir(parents=True, exist_ok=True)
    nom = f"etiquette-{secrets.token_hex(6)}.jpg"
    (dossier / nom).write_bytes(image_jpeg)
    corps = {
        "task_name": "Lecture d'étiquette de vin",
        "instructions": INSTRUCTIONS,
        "structure": STRUCTURE,
        "attachments": [{"media_content_id": f"media-source://media_source/local/{SOUS_DOSSIER}/{nom}",
                         "media_content_type": "image/jpeg"}],
    }
    try:
        champs = _nettoyer(_appeler(reglages, corps, timeout))
        log.info("Étiquette lue par l'IA : %s", ", ".join(f"{k}={v}" for k, v in champs.items() if k != "notes"))
        return champs
    finally:
        (dossier / nom).unlink(missing_ok=True)


# --------------------------------------------------------------------------- estimation de la garde

INSTRUCTIONS_GARDE = (
    "Tu es sommelier et caviste. Nous sommes en {annee}. Estime la fenêtre de dégustation de ce vin, conservé "
    "dans de bonnes conditions de cave :\n{fiche}\n\n"
    "Donne : l'année à partir de laquelle il est agréable à boire (garde_debut), l'année où il atteint son apogée "
    "(garde_apogee) et la dernière année recommandée avant qu'il ne décline (garde_fin). Appuie-toi sur ce que tu "
    "sais du producteur, de l'appellation, de la qualité du millésime dans cette région, de la couleur, du format "
    "et du prix. Sois réaliste : un vin d'entrée de gamme se boit jeune, seuls les grands vins se gardent longtemps. "
    "Si tu ne connais pas ce vin précisément, raisonne sur l'appellation et le prix, et indique une confiance faible. "
    "Justifie en une ou deux phrases courtes, en français."
)
STRUCTURE_GARDE = {
    "garde_debut": {"description": "Année à partir de laquelle le vin est bon à boire", "required": True,
                    "selector": {"number": {"min": 1900, "max": 2200}}},
    "garde_apogee": {"description": "Année de l'apogée", "required": True, "selector": {"number": {"min": 1900, "max": 2200}}},
    "garde_fin": {"description": "Dernière année recommandée", "required": True, "selector": {"number": {"min": 1900, "max": 2200}}},
    "justification": {"description": "Explication courte", "selector": {"text": {}}},
    "confiance": {"description": "Confiance dans l'estimation", "selector": {"select": {"options": ["faible", "moyenne", "elevee"]}}},
}
CONFIANCES = {"faible": "faible", "moyenne": "moyenne", "elevee": "élevée", "élevée": "élevée"}


def fiche_texte(vin, annee_achat):
    lignes = [f"- Vin : {vin['nom']}"]
    for cle, libelle in (("domaine", "Producteur"), ("appellation", "Appellation"), ("region", "Région"),
                         ("pays", "Pays"), ("couleur_label", "Couleur"), ("cepages", "Cépages"), ("format", "Format")):
        if vin.get(cle):
            lignes.append(f"- {libelle} : {vin[cle]}")
    lignes.append(f"- Millésime : {vin['millesime']}" if vin.get("millesime")
                  else f"- Non millésimé (ou millésime inconnu), acheté en {annee_achat}")
    prix = vin.get("prix_achat") or vin.get("valeur")
    if prix:
        lignes.append(f"- Prix : environ {prix:.0f} € la bouteille")
    return "\n".join(lignes)


def estimer_garde(reglages, vin, annee_achat, annee, timeout=90):
    """Demande à l'IA la fenêtre de garde d'un vin ; renvoie des années validées et une note explicative."""
    possible = etat(reglages, image=False)
    if not possible["possible"]:
        raise IAErreur(possible["raison"])
    donnees = _appeler(reglages, {
        "task_name": "Garde d'un vin",
        "instructions": INSTRUCTIONS_GARDE.format(annee=annee, fiche=fiche_texte(vin, annee_achat)),
        "structure": STRUCTURE_GARDE,
    }, timeout)
    try:
        debut, fin = int(float(donnees["garde_debut"])), int(float(donnees["garde_fin"]))
        apogee = int(float(donnees["garde_apogee"])) if donnees.get("garde_apogee") not in (None, "") else None
    except (KeyError, TypeError, ValueError):
        raise IAErreur("L'IA n'a pas donné d'années exploitables")
    reference = vin.get("millesime") or annee_achat
    if not (reference - 1 <= debut <= fin <= reference + 100):
        raise IAErreur(f"Estimation de l'IA incohérente ({debut} → {fin})")
    if apogee is not None and not debut <= apogee <= fin:
        apogee = None
    note = str(donnees.get("justification") or "").strip()[:400]
    confiance = CONFIANCES.get(str(donnees.get("confiance") or "").strip().lower())
    if confiance:
        note = f"{note} (confiance {confiance})".strip()
    return {"garde_debut": debut, "garde_apogee": apogee, "garde_fin": fin, "note": note}
