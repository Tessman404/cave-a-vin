"""Lecture d'étiquette par l'IA configurée dans Home Assistant (action ai_task.generate_data).

La photo est déposée temporairement dans le dossier « media » de Home Assistant, puis transmise
à l'IA en pièce jointe. Le fichier est supprimé dès la réponse reçue.
"""

import json
import os
import secrets
import urllib.error
import urllib.request
from pathlib import Path

from . import ha
from .cave import COULEURS

SOUS_DOSSIER = "cave_a_vin"
INSTRUCTIONS = (
    "Tu es sommelier. La photo jointe montre une bouteille de vin. Lis son étiquette et renvoie les "
    "informations demandées, en français. N'invente rien : laisse un champ vide si l'information n'est "
    "ni écrite sur l'étiquette ni déductible avec certitude (par exemple la région à partir d'une "
    "appellation connue : Haut-Médoc → Bordeaux, Chablis → Bourgogne). Pour la couleur, appuie-toi sur "
    "l'étiquette, l'appellation ou la couleur visible du vin. Le nom est celui de la cuvée ou du château, "
    "le domaine est le producteur ou le négociant."
)
STRUCTURE = {
    "nom": {"description": "Nom du vin : château ou cuvée, sans le millésime", "required": True,
            "selector": {"text": {}}},
    "domaine": {"description": "Producteur, domaine, château ou négociant", "selector": {"text": {}}},
    "appellation": {"description": "Appellation (AOC/AOP/IGP), par exemple Haut-Médoc", "selector": {"text": {}}},
    "region": {"description": "Région viticole : Bordeaux, Bourgogne, Loire, Rhône, Alsace…", "selector": {"text": {}}},
    "pays": {"description": "Pays de production", "selector": {"text": {}}},
    "couleur": {"description": "Type de vin", "selector": {"select": {"options": list(COULEURS)}}},
    "millesime": {"description": "Année de récolte, si elle est indiquée", "selector": {"number": {"min": 1900, "max": 2100}}},
    "cepages": {"description": "Cépages mentionnés, séparés par des virgules", "selector": {"text": {}}},
    "degre": {"description": "Degré d'alcool en % vol.", "selector": {"number": {"min": 0, "max": 25, "step": 0.1}}},
    "format": {"description": "Contenance, par exemple 75 cl", "selector": {"text": {}}},
}


class IAErreur(Exception):
    pass


def dossier_media():
    """Dossier « media » de Home Assistant, partagé avec le module (map: media)."""
    chemin = os.environ.get("HA_MEDIA_DIR") or ("/media" if ha.mode_addon() else "")
    return Path(chemin) if chemin and Path(chemin).is_dir() else None


def etat(reglages):
    """Indique si la lecture d'étiquette est possible, et sinon pourquoi."""
    if reglages.get("ia_active", "1") != "1":
        return {"possible": False, "raison": "Lecture d'étiquette désactivée dans les réglages"}
    url, _ = ha.connexion(reglages)
    if not url:
        return {"possible": False, "raison": "Home Assistant n'est pas connecté"}
    if not dossier_media():
        return {"possible": False, "raison": "Dossier « media » de Home Assistant inaccessible"}
    return {"possible": True, "entite": reglages.get("ia_entite") or None}


def entites(reglages):
    url, jeton = ha.connexion(reglages)
    if not url:
        return []
    req = urllib.request.Request(f"{url}/states", headers={"Authorization": f"Bearer {jeton}"})
    try:
        with urllib.request.urlopen(req, timeout=8) as rep:
            etats = json.loads(rep.read().decode())
    except (urllib.error.URLError, OSError, ValueError):
        return []
    return [{"entity_id": e["entity_id"], "nom": e.get("attributes", {}).get("friendly_name", e["entity_id"])}
            for e in etats if e["entity_id"].startswith("ai_task.")]


def _nettoyer(donnees):
    if not isinstance(donnees, dict):
        raise IAErreur("Réponse de l'IA inattendue")
    propre = {}
    for cle in ("nom", "domaine", "appellation", "region", "pays", "cepages", "format"):
        v = donnees.get(cle)
        if isinstance(v, str) and v.strip() and v.strip().lower() not in ("inconnu", "non indiqué", "n/a", "null"):
            propre[cle] = v.strip()[:200]
    couleur = str(donnees.get("couleur") or "").strip().lower().replace("é", "e")
    if couleur in COULEURS:
        propre["couleur"] = couleur
    try:
        millesime = int(float(donnees.get("millesime")))
        if 1900 <= millesime <= 2100:
            propre["millesime"] = millesime
    except (TypeError, ValueError):
        pass
    try:
        degre = float(str(donnees.get("degre")).replace(",", "."))
        if 3 <= degre <= 25:
            propre["degre"] = degre
    except (TypeError, ValueError):
        pass
    return propre


def lire_etiquette(reglages, image_jpeg, timeout=120):
    possible = etat(reglages)
    if not possible["possible"]:
        raise IAErreur(possible["raison"])
    url, jeton = ha.connexion(reglages)
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
    if reglages.get("ia_entite"):
        corps["entity_id"] = reglages["ia_entite"]
    req = urllib.request.Request(f"{url}/services/ai_task/generate_data?return_response", method="POST",
                                 data=json.dumps(corps).encode(),
                                 headers={"Authorization": f"Bearer {jeton}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as rep:
            reponse = json.loads(rep.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        if e.code == 400 and "entity" in detail.lower():
            raise IAErreur("Aucune IA par défaut dans Home Assistant : choisissez-en une dans les Réglages de la cave")
        raise IAErreur(f"L'IA de Home Assistant a refusé la demande ({e.code}) : {detail}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise IAErreur(f"Home Assistant injoignable ({getattr(e, 'reason', e)})")
    finally:
        (dossier / nom).unlink(missing_ok=True)
    donnees = (reponse.get("service_response") or {}).get("data")
    if isinstance(donnees, str):  # certaines IA renvoient du JSON sous forme de texte
        try:
            donnees = json.loads(donnees)
        except ValueError:
            raise IAErreur("L'IA n'a pas renvoyé de données exploitables")
    return _nettoyer(donnees)
