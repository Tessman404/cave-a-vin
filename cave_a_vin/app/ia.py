"""Lecture d'étiquette par l'IA configurée dans Home Assistant (action ai_task.generate_data).

La photo est déposée temporairement dans le dossier « media » de Home Assistant, puis transmise
à l'IA en pièce jointe. Le fichier est supprimé dès la réponse reçue.
"""

import json
import logging
import os
import re
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import ha
from .cave import COULEURS

log = logging.getLogger("cave_a_vin")
SOUS_DOSSIER = "cave_a_vin"
DEVISES = ("EUR", "USD", "GBP", "CHF", "DKK")
VALEUR_MAX = 1_000_000


def devise_code(reglages):
    """Devise dans laquelle les valeurs des vins sont exprimées (EUR tant qu'aucune n'est choisie)."""
    devise = (reglages or {}).get("devise")
    return devise if devise in DEVISES else "EUR"


def langue_texte(reglages):
    """Langue des textes libres renvoyés par l'IA (notes, justification) : celle de l'interface."""
    langue = (reglages or {}).get("langue")
    if langue == "en":
        return "in English (for an English-speaking user)"
    if langue == "it":
        return "en italien (pour un utilisateur italophone)"
    return "en français"


INSTRUCTIONS = (
    "Tu es sommelier. La première photo jointe montre une bouteille de vin, vue de face (étiquette). S'il y a une "
    "seconde photo, c'est le verso de la même bouteille (contre-étiquette) : sers-t'en pour compléter et confirmer "
    "(producteur, cépages, degré, contenance, conseils de service) et recopie les chiffres du code-barres s'ils "
    "sont lisibles. Remplis, {langue}, la fiche de ce vin pour l'inventaire d'une cave.\n"
    "1. Recopie ce qui est écrit sur la bouteille (étiquette, contre-étiquette, collerette, capsule) : le nom de la "
    "cuvée ou du château ; le producteur (domaine, château, maison ou négociant : il est souvent écrit en grand, ou "
    "dans la mention « mis en bouteille par… » / « mis en bouteille au château ») ; l'appellation ; le millésime ; "
    "le degré ; la contenance.\n"
    "2. Complète avec tes connaissances ce qui n'est pas écrit mais se déduit : la région viticole et le pays à "
    "partir de l'appellation (Haut-Médoc → Bordeaux, France ; Chablis → Bourgogne) ; la couleur (mention sur "
    "l'étiquette, appellation, cépages, couleur du vin ou de la bouteille) ; les cépages habituels de l'appellation "
    "s'ils ne sont pas indiqués ; un prix de marché indicatif en {devise} pour une bouteille ; trois à cinq accords "
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
    "valeur": {"description": "Prix de marché indicatif d'une bouteille, en {devise}", "selector": {"number": {"min": 0, "max": VALEUR_MAX, "step": 0.5}}},
    "accords": {"description": "Trois à cinq accords mets-vins, séparés par des virgules", "required": True, "selector": TEXTE},
    "description": {"description": "Deux phrases : style du vin, arômes typiques, potentiel", "selector": TEXTE},
    "code_barre": {"description": "Chiffres du code-barres (EAN, 8 à 14 chiffres) s'ils sont lisibles sur la "
                                  "contre-étiquette, sinon vide", "selector": TEXTE},
}


def structure_etiquette(devise):
    """STRUCTURE, avec la devise choisie dans la description du prix."""
    return {cle: {**champ, "description": champ["description"].replace("{devise}", devise)}
            for cle, champ in STRUCTURE.items()}

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
                raise IAErreur(diagnostic(reglages)["conseil"] or AUCUNE_IA)
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
    # agents de conversation à base d'IA (hors l'agent intégré « Home Assistant ») : utiles pour le diagnostic
    agents = [e.get("attributes", {}).get("friendly_name", e["entity_id"]) for e in etats
              if e["entity_id"].startswith("conversation.") and e["entity_id"] != "conversation.home_assistant"]
    _cache_entites.update(cle=url, quand=time.time(), valeur=valeur, agents=agents)
    return valeur


def diagnostic(reglages):
    """Ce que Home Assistant propose comme IA, pour guider l'utilisateur."""
    taches = entites(reglages)
    agents = _cache_entites.get("agents", []) if _cache_entites["cle"] else []
    if taches:
        conseil = ""
    elif agents:
        conseil = (f"Vous avez une IA de conversation ({', '.join(agents)}) mais pas de « tâche IA ». Dans Home Assistant : "
                   "Paramètres → Appareils et services → ouvrez cette intégration d'IA → « Ajouter une tâche IA » "
                   "(bouton ou menu ⋮). La cave l'utilisera automatiquement. Si ce bouton n'existe pas, cette "
                   "intégration ne sait pas faire de tâches IA (c'est le cas des intégrations qui passent par un "
                   "abonnement Claude ou ChatGPT) : ajoutez l'intégration officielle Google Gemini (« Google "
                   "Generative AI », offre gratuite), Anthropic ou OpenAI avec une clé d'API, puis « Ajouter une tâche IA ».")
    else:
        conseil = ("Home Assistant n'a aucune intégration d'IA. Ajoutez-en une : Paramètres → Appareils et services → "
                   "Ajouter une intégration → Google Gemini (« Google Generative AI », offre gratuite), OpenAI, Anthropic "
                   "ou Ollama (IA locale) ; puis, dans cette intégration, « Ajouter une tâche IA ». Un modèle qui "
                   "comprend les images est nécessaire pour lire les étiquettes. Remarque : Claude ou une autre IA "
                   "connectée À Home Assistant (serveur MCP, appli) ne peut pas être utilisée PAR Home Assistant.")
    return {"taches_ia": taches, "agents_conversation": agents, "conseil": conseil}


VIDES = ("", "inconnu", "inconnue", "non indiqué", "non indiquée", "n/a", "na", "null", "none", "-", "?")


def _nombre(v):
    """Nombre contenu dans une réponse de l'IA, même écrite avec un symbole ou un code de devise (« 15 € », « 120 DKK »)."""
    return float(re.sub(r"[^\d.,-]", "", str(v)).replace(",", "."))


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
    for cle, mini, maxi, conv in (("millesime", 1900, 2100, int), ("degre", 3, 25, float), ("valeur", 0.5, VALEUR_MAX, float)):
        try:
            valeur = conv(_nombre(donnees.get(cle)))
        except (TypeError, ValueError):
            continue
        if mini <= valeur <= maxi:
            propre[cle] = round(valeur, 2) if conv is float else valeur
    code = re.sub(r"\D", "", str(donnees.get("code_barre") or ""))
    if 8 <= len(code) <= 14:
        propre["code_barre"] = code
    description = donnees.get("description")
    if isinstance(description, str) and description.strip().lower() not in VIDES:
        propre["notes"] = description.strip()[:600]
    return propre


def lire_etiquette(reglages, image_jpeg, timeout=120, verso_jpeg=None):
    """Lit l'étiquette (et la contre-étiquette si elle est fournie) en une seule demande à l'IA.
    Les photos ne sont déposées que le temps de la lecture."""
    possible = etat(reglages)
    if not possible["possible"]:
        raise IAErreur(possible["raison"])
    devise = devise_code(reglages)
    dossier = dossier_media() / SOUS_DOSSIER
    dossier.mkdir(parents=True, exist_ok=True)
    jeton = secrets.token_hex(6)
    noms = [f"etiquette-{jeton}.jpg"] + ([f"verso-{jeton}.jpg"] if verso_jpeg else [])
    for nom, contenu in zip(noms, (image_jpeg, verso_jpeg)):
        (dossier / nom).write_bytes(contenu)
    corps = {
        "task_name": "Lecture d'étiquette de vin",
        "instructions": INSTRUCTIONS.replace("{langue}", langue_texte(reglages)).replace("{devise}", devise),
        "structure": structure_etiquette(devise),
        "attachments": [{"media_content_id": f"media-source://media_source/local/{SOUS_DOSSIER}/{nom}",
                         "media_content_type": "image/jpeg"} for nom in noms],
    }
    try:
        champs = _nettoyer(_appeler(reglages, corps, timeout))
        log.info("Étiquette lue par l'IA%s : %s", " (avec le verso)" if verso_jpeg else "",
                 ", ".join(f"{k}={v}" for k, v in champs.items() if k != "notes"))
        return champs
    finally:
        for nom in noms:
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
    "Justifie en une ou deux phrases courtes, {langue}."
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


def fiche_texte(vin, annee_achat, devise="EUR", avec_prix=True):
    lignes = [f"- Vin : {vin['nom']}"]
    for cle, libelle in (("domaine", "Producteur"), ("appellation", "Appellation"), ("region", "Région"),
                         ("pays", "Pays"), ("couleur_label", "Couleur"), ("cepages", "Cépages"), ("format", "Format")):
        if vin.get(cle):
            lignes.append(f"- {libelle} : {vin[cle]}")
    lignes.append(f"- Millésime : {vin['millesime']}" if vin.get("millesime")
                  else f"- Non millésimé (ou millésime inconnu), acheté en {annee_achat}")
    prix = vin.get("prix_achat") or vin.get("valeur")
    if prix and avec_prix:
        lignes.append(f"- Prix : environ {prix:.0f} {devise} la bouteille")
    return "\n".join(lignes)


def estimer_garde(reglages, vin, annee_achat, annee, timeout=90):
    """Demande à l'IA la fenêtre de garde d'un vin ; renvoie des années validées et une note explicative."""
    possible = etat(reglages, image=False)
    if not possible["possible"]:
        raise IAErreur(possible["raison"])
    donnees = _appeler(reglages, {
        "task_name": "Garde d'un vin",
        "instructions": INSTRUCTIONS_GARDE.format(annee=annee, fiche=fiche_texte(vin, annee_achat, devise_code(reglages)),
                                         langue=langue_texte(reglages)),
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


# --------------------------------------------------------------------------- estimation de la valeur

INSTRUCTIONS_VALEUR = (
    "Tu es caviste. Estime le prix de marché indicatif actuel d'une bouteille de ce vin, en {devise} :\n{fiche}\n\n"
    "Donne un seul nombre, exprimé en {devise} (et non dans une autre devise), pour une bouteille. Si tu ne connais pas "
    "ce vin précisément, raisonne sur le producteur, l'appellation, le millésime et le format."
)


def estimer_valeur(reglages, vin, annee_achat, timeout=90):
    """Demande à l'IA la valeur d'une bouteille, dans la devise choisie ; renvoie un nombre."""
    possible = etat(reglages, image=False)
    if not possible["possible"]:
        raise IAErreur(possible["raison"])
    devise = devise_code(reglages)
    donnees = _appeler(reglages, {
        "task_name": "Valeur d'un vin",
        "instructions": INSTRUCTIONS_VALEUR.format(devise=devise, fiche=fiche_texte(vin, annee_achat, devise, avec_prix=False)),
        "structure": {"valeur": {"description": f"Prix de marché indicatif d'une bouteille, en {devise}", "required": True,
                                 "selector": {"number": {"min": 0, "max": VALEUR_MAX, "step": 0.5}}}},
    }, timeout)
    try:
        valeur = _nombre(donnees["valeur"])
    except (KeyError, TypeError, ValueError):
        raise IAErreur("L'IA n'a pas donné de valeur exploitable")
    if not 0.5 <= valeur <= VALEUR_MAX:
        raise IAErreur(f"Estimation de l'IA incohérente ({valeur:g} {devise})")
    return round(valeur, 2)
