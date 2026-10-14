"""Recherche d'un vin par son code-barres dans Open Food Facts (base libre et collaborative)."""

import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

URL_OFF = os.environ.get("OFF_URL", "https://world.openfoodfacts.org")
AGENT = "CaveAVin/1.2 (module Home Assistant ; https://github.com/Tessman404/cave-a-vin)"
CHAMPS_OFF = ("product_name,product_name_fr,generic_name_fr,generic_name,brands,categories,categories_tags,"
              "labels_tags,origins,origins_tags,quantity,nutriments,image_front_url,image_url")
HOTES_IMAGES = ("openfoodfacts.org", "openfoodfacts.net")

COULEURS_TAGS = [
    ("effervescent", ("sparkling", "champagne", "cremant", "crémant", "mousseux", "petillant", "pétillant", "prosecco", "cava")),
    ("liquoreux", ("sweet-wine", "dessert-wine", "liquoreux", "moelleux", "sauternes", "fortified", "porto", "port-wine")),
    ("rose", ("rose-wine", "roses", "vins-roses", "rosé")),
    ("blanc", ("white-wine", "vins-blancs", "blanc")),
    ("rouge", ("red-wine", "vins-rouges", "rouge")),
]
REGIONS_TAGS = {
    "bordeaux": "Bordeaux", "burgundy": "Bourgogne", "bourgogne": "Bourgogne", "beaujolais": "Beaujolais",
    "rhone": "Rhône", "loire": "Loire", "alsace": "Alsace", "champagne": "Champagne", "languedoc": "Languedoc",
    "roussillon": "Roussillon", "provence": "Provence", "south-west": "Sud-Ouest", "sud-ouest": "Sud-Ouest",
    "jura": "Jura", "savoie": "Savoie", "savoy": "Savoie", "corsica": "Corse", "corse": "Corse",
}
PAYS_TAGS = {"france": "France", "italy": "Italie", "spain": "Espagne", "portugal": "Portugal", "germany": "Allemagne",
             "chile": "Chili", "argentina": "Argentine", "south-africa": "Afrique du Sud", "australia": "Australie",
             "united-states": "États-Unis", "new-zealand": "Nouvelle-Zélande", "switzerland": "Suisse"}
MOTS_GENERIQUES = ("vin", "wine", "boisson", "beverage", "alcool", "alcoholic", "drink", "aoc", "aop", "igp", "france",
                   "français", "french", "rouge", "blanc", "rosé", "red", "white")


class ScanErreur(Exception):
    pass


def gtin_valide(code):
    """Vérifie le chiffre de contrôle (EAN-8, UPC-A, EAN-13, GTIN-14)."""
    chiffres = [int(c) for c in code]
    somme = sum(c * (3 if i % 2 == 0 else 1) for i, c in enumerate(reversed(chiffres[:-1])))
    return (10 - somme % 10) % 10 == chiffres[-1]


def nettoyer_code(code):
    code = re.sub(r"\D", "", code or "")
    if len(code) not in (8, 12, 13, 14):
        raise ScanErreur("Code-barres invalide : 8 ou 13 chiffres attendus")
    if not gtin_valide(code):
        raise ScanErreur("Code-barres invalide : vérifiez les chiffres saisis")
    return code


def _format(quantite):
    q = (quantite or "").lower().replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|cl|l)\b", q)
    if not m:
        return ""
    cl = float(m.group(1)) * {"ml": 0.1, "cl": 1, "l": 100}[m.group(2)]
    noms = {37.5: "37,5 cl", 50: "50 cl", 62: "Clavelin 62 cl", 75: "75 cl", 150: "Magnum 1,5 L", 300: "Jéroboam 3 L"}
    for valeur, nom in noms.items():
        if abs(cl - valeur) < 0.6:
            return nom
    return f"{cl:g} cl"


def _appellation(produit):
    """Dernière catégorie spécifique, par exemple « Haut-Médoc » dans « Vins, Vins rouges, …, Haut-Médoc »."""
    regions = {r.lower() for r in REGIONS_TAGS.values()}
    for cat in reversed([c.strip() for c in (produit.get("categories") or "").split(",") if c.strip()]):
        bas = cat.lower()
        mots = re.split(r"[\s'’]+", bas)
        if ":" in cat or bas in regions or any(mot.startswith(g) for mot in mots for g in MOTS_GENERIQUES):
            continue
        return cat
    return ""


def depuis_off(produit, code):
    """Convertit une fiche Open Food Facts en champs de fiche vin."""
    tags = " ".join((produit.get("categories_tags") or []) + (produit.get("labels_tags") or [])).lower()
    nom = (produit.get("product_name_fr") or produit.get("product_name") or "").strip()
    texte = " ".join([nom, produit.get("generic_name_fr") or "", produit.get("generic_name") or ""])
    millesime = re.search(r"\b(19[5-9]\d|20[0-4]\d)\b", texte)
    couleur = next((c for c, mots in COULEURS_TAGS if any(m in tags for m in mots)), "")
    region = next((r for k, r in REGIONS_TAGS.items() if k in tags), "")
    pays = next((p for k, p in PAYS_TAGS.items() if f"en:{k}" in " ".join(produit.get("origins_tags") or [])), "")
    if not pays and ("wines-from-france" in tags or "vins-de-france" in tags or region):
        pays = "France"
    nutriments = produit.get("nutriments") or {}
    degre = nutriments.get("alcohol_100g", nutriments.get("alcohol"))
    if millesime:
        nom = re.sub(rf"\s*\b{millesime.group(1)}\b", "", nom).strip(" -–,")
    vin = {
        "nom": nom,
        "domaine": (produit.get("brands") or "").split(",")[0].strip(),
        "appellation": _appellation(produit),
        "region": region,
        "pays": pays,
        "couleur": couleur,
        "millesime": int(millesime.group(1)) if millesime else None,
        "degre": float(degre) if isinstance(degre, (int, float)) and 3 <= degre <= 25 else None,
        "format": _format(produit.get("quantity")),
        "code_barre": code,
    }
    image = produit.get("image_front_url") or produit.get("image_url") or ""
    return {"vin": {k: v for k, v in vin.items() if v not in ("", None)}, "image_url": image if image_autorisee(image) else ""}


def image_autorisee(url):
    hote = urlparse(url or "").hostname or ""
    return urlparse(url or "").scheme == "https" and any(hote == h or hote.endswith("." + h) for h in HOTES_IMAGES)


def chercher(code, timeout=10):
    """Renvoie {"vin": {...}, "image_url": ...} ou None si le produit est inconnu."""
    url = f"{URL_OFF}/api/v2/product/{code}.json?fields={CHAMPS_OFF}"
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as rep:
            donnees = json.loads(rep.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise ScanErreur(f"Open Food Facts a répondu {e.code}")
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise ScanErreur(f"Open Food Facts injoignable ({getattr(e, 'reason', e)})")
    if donnees.get("status") != 1 or not donnees.get("product"):
        return None
    resultat = depuis_off(donnees["product"], code)
    return resultat if resultat["vin"].get("nom") else None


def telecharger_image(url, timeout=15, taille_max=8 * 1024 * 1024):
    if not image_autorisee(url):
        raise ScanErreur("Adresse d'image non autorisée")
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as rep:
            contenu = rep.read(taille_max + 1)
    except OSError as e:
        raise ScanErreur(f"Image indisponible ({e})")
    if len(contenu) > taille_max:
        raise ScanErreur("Image trop volumineuse")
    return contenu
