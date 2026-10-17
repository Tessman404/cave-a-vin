"""Lecture des capteurs de la cave (température, humidité) dans Home Assistant."""

import json
import os
import time
import urllib.error
import urllib.request

REGLAGES_DEFAUT = {
    "ha_url": "",
    "ha_token": "",
    "capteur_temperature": "",
    "capteur_humidite": "",
    "temp_min": "10",
    "temp_max": "16",
    "hum_min": "60",
    "hum_max": "80",
    "ia_active": "1",
    "ia_entite": "",
    "detourage_qualite": "standard",
    "fond_defaut": "cave-voutee",
    "cadrage_defaut": "etiquette",
    "ia_garde_auto": "1",
    "ia_garde_derniere": "",
}

_cache = {"cle": None, "quand": 0, "valeur": None}


def mode_addon():
    return bool(os.environ.get("SUPERVISOR_TOKEN"))


def connexion(reglages):
    """Renvoie (url_api, jeton) ou (None, None) si Home Assistant n'est pas configuré."""
    if mode_addon():
        return "http://supervisor/core/api", os.environ["SUPERVISOR_TOKEN"]
    url = (reglages.get("ha_url") or os.environ.get("HA_URL") or "").rstrip("/")
    jeton = reglages.get("ha_token") or os.environ.get("HA_TOKEN") or ""
    if not url or not jeton:
        return None, None
    return url + "/api", jeton


def lire_etat(url, jeton, entity_id, timeout=5):
    req = urllib.request.Request(f"{url}/states/{entity_id}",
                                 headers={"Authorization": f"Bearer {jeton}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as rep:
        return json.loads(rep.read().decode())


def _mesure(url, jeton, entity_id, mini, maxi):
    if not entity_id:
        return None
    try:
        etat = lire_etat(url, jeton, entity_id)
    except urllib.error.HTTPError as e:
        return {"entity_id": entity_id, "erreur": "Capteur introuvable" if e.code == 404 else f"Erreur HTTP {e.code}"}
    except (urllib.error.URLError, OSError, ValueError) as e:
        return {"entity_id": entity_id, "erreur": f"Home Assistant injoignable ({getattr(e, 'reason', e)})"}
    try:
        valeur = float(etat["state"])
    except (TypeError, ValueError, KeyError):
        return {"entity_id": entity_id, "erreur": f"Valeur indisponible ({etat.get('state')})"}
    alerte = None
    if mini is not None and valeur < mini:
        alerte = "basse"
    elif maxi is not None and valeur > maxi:
        alerte = "haute"
    attributs = etat.get("attributes", {})
    return {
        "entity_id": entity_id,
        "nom": attributs.get("friendly_name", entity_id),
        "valeur": valeur,
        "unite": attributs.get("unit_of_measurement", ""),
        "mis_a_jour": etat.get("last_updated"),
        "min": mini,
        "max": maxi,
        "alerte": alerte,
    }


def _nombre(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def climat(reglages, cache_secondes=30):
    url, jeton = connexion(reglages)
    if not url:
        return {"configure": False}
    cle = (url, reglages.get("capteur_temperature"), reglages.get("capteur_humidite"),
           reglages.get("temp_min"), reglages.get("temp_max"), reglages.get("hum_min"), reglages.get("hum_max"))
    if _cache["cle"] == cle and time.time() - _cache["quand"] < cache_secondes:
        return _cache["valeur"]
    valeur = {
        "configure": bool(reglages.get("capteur_temperature") or reglages.get("capteur_humidite")),
        "temperature": _mesure(url, jeton, reglages.get("capteur_temperature"),
                               _nombre(reglages.get("temp_min")), _nombre(reglages.get("temp_max"))),
        "humidite": _mesure(url, jeton, reglages.get("capteur_humidite"),
                            _nombre(reglages.get("hum_min")), _nombre(reglages.get("hum_max"))),
    }
    _cache.update(cle=cle, quand=time.time(), valeur=valeur)
    return valeur


def capteurs_disponibles(reglages):
    """Liste des capteurs de température / humidité, pour les menus des réglages."""
    url, jeton = connexion(reglages)
    if not url:
        return []
    req = urllib.request.Request(f"{url}/states", headers={"Authorization": f"Bearer {jeton}"})
    try:
        with urllib.request.urlopen(req, timeout=8) as rep:
            etats = json.loads(rep.read().decode())
    except (urllib.error.URLError, OSError, ValueError):
        return []
    capteurs = []
    for e in etats:
        attrs = e.get("attributes", {})
        if e["entity_id"].startswith("sensor.") and attrs.get("device_class") in ("temperature", "humidity"):
            capteurs.append({"entity_id": e["entity_id"], "nom": attrs.get("friendly_name", e["entity_id"]),
                             "type": attrs["device_class"], "etat": e.get("state"),
                             "unite": attrs.get("unit_of_measurement", "")})
    return sorted(capteurs, key=lambda c: (c["type"], c["nom"].lower()))
