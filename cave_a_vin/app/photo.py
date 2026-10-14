"""Photos de bouteilles : détourage automatique et mise en scène sur un fond « cave ».

Le détourage utilise un petit réseau de neurones (famille U²-Net / IS-Net, modèles publiés
par le projet rembg) exécuté localement avec onnxruntime : aucune photo ne quitte la maison.
Le modèle est téléchargé une seule fois, au premier usage.
"""

import io
import logging
import threading
import urllib.request
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter, ImageOps
except ImportError:  # installation minimale : photos acceptées telles quelles
    np = Image = None

try:
    import onnxruntime as ort
except ImportError:
    ort = None

log = logging.getLogger("cave_a_vin")

IMAGENET = ((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
QUALITES = {
    # qualité : (fichier du modèle, taille d'entrée, normalisation, taille en octets)
    "rapide": ("u2netp", 320, IMAGENET, 4_574_861),
    "standard": ("silueta", 320, IMAGENET, 44_173_029),
    "precis": ("isnet-general-use", 1024, ((0.5, 0.5, 0.5), (1.0, 1.0, 1.0)), 178_648_008),
}
URL_MODELE = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/{}.onnx"
FONDS = {
    "cave-voutee": "Cave voûtée",
    "casier-bois": "Casier en bois",
    "studio": "Studio bordeaux",
    "pierre-claire": "Pierre claire",
}
TAILLE_MAX = 1800  # côté le plus long conservé pour l'original


class PhotoErreur(Exception):
    pass


def pil_disponible():
    return Image is not None


def detourage_disponible():
    return Image is not None and ort is not None


def ouvrir(contenu):
    """Ouvre une image (JPEG, PNG, WebP…), la redresse selon l'EXIF et la réduit si besoin."""
    if not pil_disponible():
        raise PhotoErreur("Traitement d'image indisponible sur cette installation")
    try:
        img = Image.open(io.BytesIO(contenu))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception as e:  # noqa: BLE001 - Pillow lève des exceptions variées
        raise PhotoErreur(f"Image illisible ({e})")
    img.thumbnail((TAILLE_MAX, TAILLE_MAX), Image.LANCZOS)
    return img


def jpeg(img, qualite=88):
    tampon = io.BytesIO()
    img.convert("RGB").save(tampon, "JPEG", quality=qualite, optimize=True)
    return tampon.getvalue()


class Atelier:
    """Détoure et compose les photos. Une instance par application."""

    def __init__(self, dossier_donnees, dossier_fonds, qualite=lambda: "standard"):
        self.dossier_modeles = Path(dossier_donnees) / "modeles"
        self.dossier_fonds = Path(dossier_fonds)
        self.qualite = qualite
        self._sessions = {}
        self._verrou = threading.Lock()

    # ------------------------------------------------------------------ modèle

    def _chemin_modele(self, qualite):
        nom, _, _, taille = QUALITES[qualite]
        chemin = self.dossier_modeles / f"{nom}.onnx"
        if chemin.exists() and chemin.stat().st_size == taille:
            return chemin
        self.dossier_modeles.mkdir(parents=True, exist_ok=True)
        temporaire = chemin.with_suffix(".part")
        log.info("Téléchargement du modèle de détourage « %s » (%d Mo)…", nom, taille // 1_000_000)
        try:
            req = urllib.request.Request(URL_MODELE.format(nom), headers={"User-Agent": "CaveAVin"})
            with urllib.request.urlopen(req, timeout=60) as rep, open(temporaire, "wb") as f:
                while bloc := rep.read(1 << 20):
                    f.write(bloc)
        except OSError as e:
            temporaire.unlink(missing_ok=True)
            raise PhotoErreur(f"Téléchargement du modèle de détourage impossible ({e})")
        if temporaire.stat().st_size != taille:
            temporaire.unlink(missing_ok=True)
            raise PhotoErreur("Modèle de détourage incomplet, réessayez")
        temporaire.replace(chemin)
        return chemin

    def _session(self, qualite):
        with self._verrou:
            if qualite not in self._sessions:
                options = ort.SessionOptions()
                options.intra_op_num_threads = 2  # reste raisonnable sur un Raspberry Pi
                self._sessions[qualite] = ort.InferenceSession(
                    str(self._chemin_modele(qualite)), options, providers=["CPUExecutionProvider"])
            return self._sessions[qualite]

    def masque(self, img):
        """Masque de saillance (0-255) de la même taille que l'image."""
        if not detourage_disponible():
            raise PhotoErreur("Détourage indisponible sur cette installation")
        qualite = self.qualite() if self.qualite() in QUALITES else "standard"
        _, taille, (moyenne, ecart), _ = QUALITES[qualite]
        session = self._session(qualite)
        x = np.asarray(img.resize((taille, taille), Image.LANCZOS), dtype=np.float32)
        x = x / max(float(x.max()), 1e-6)
        x = ((x - moyenne) / ecart).transpose(2, 0, 1)[None].astype(np.float32)
        sortie = session.run(None, {session.get_inputs()[0].name: x})[0][0, 0]
        sortie = (sortie - sortie.min()) / max(float(sortie.max() - sortie.min()), 1e-6)
        return Image.fromarray((sortie * 255).astype(np.uint8)).resize(img.size, Image.LANCZOS)

    # ------------------------------------------------------------------ traitement

    def detourer(self, img):
        """Renvoie la bouteille détourée (RGBA), recadrée au plus près."""
        masque = self.masque(img)
        boite = masque.point(lambda v: 255 if v > 40 else 0).getbbox()
        if not boite:
            raise PhotoErreur("Aucune bouteille détectée sur la photo")
        largeur, hauteur = boite[2] - boite[0], boite[3] - boite[1]
        if largeur * hauteur < 0.02 * img.width * img.height:
            raise PhotoErreur("La bouteille est trop petite sur la photo : rapprochez-vous")
        sujet = img.convert("RGBA")
        sujet.putalpha(masque)
        return sujet.crop(boite)

    def composer(self, sujet, fond):
        """Pose la bouteille détourée sur un fond, avec ombre de contact et léger reflet."""
        if fond not in FONDS:
            raise PhotoErreur("Fond inconnu")
        toile = Image.open(self.dossier_fonds / f"{fond}.jpg").convert("RGBA")
        W, H = toile.size
        sol = int(H * 0.86)
        h = int(H * 0.74)
        w = max(1, int(sujet.width * h / sujet.height))
        if w > W * 0.8:  # bouteille couchée ou photo très large
            w = int(W * 0.8)
            h = max(1, int(sujet.height * w / sujet.width))
        sujet = sujet.resize((w, h), Image.LANCZOS)
        x, y = (W - w) // 2, sol - h

        ombre = Image.new("L", (W, H), 0)
        ImageDraw.Draw(ombre).ellipse((x + w * 0.05, sol - h * 0.025, x + w * 0.95, sol + h * 0.03), fill=170)
        noir = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        noir.putalpha(ombre.filter(ImageFilter.GaussianBlur(max(2, h * 0.02))))
        toile.alpha_composite(noir)

        reflet = ImageOps.flip(sujet).crop((0, 0, w, max(1, int(h * 0.25))))
        degrade = Image.linear_gradient("L").resize(reflet.size).point(lambda v: int((255 - v) * 0.22))
        reflet.putalpha(Image.fromarray(np.minimum(np.asarray(reflet.getchannel("A")), np.asarray(degrade))))
        toile.alpha_composite(reflet, (x, sol))
        toile.alpha_composite(sujet, (x, y))
        return toile.convert("RGB")


class Brouillons:
    """Photos en cours d'ajout (avant la création de la fiche du vin)."""

    def __init__(self, dossier, atelier):
        self.dossier = Path(dossier)
        self.dossier.mkdir(parents=True, exist_ok=True)
        self.atelier = atelier

    def _chemin(self, ident, suffixe):
        if not ident.isalnum() or len(ident) > 40:
            raise PhotoErreur("Brouillon inconnu")
        return self.dossier / f"{ident}-{suffixe}"

    def existe(self, ident):
        return self._chemin(ident, "original.jpg").exists()

    def creer(self, contenu):
        import secrets
        ident = secrets.token_hex(8)
        self._chemin(ident, "original.jpg").write_bytes(jpeg(ouvrir(contenu), 90))
        self.nettoyer()
        return ident

    def original(self, ident):
        chemin = self._chemin(ident, "original.jpg")
        if not chemin.exists():
            raise PhotoErreur("Brouillon introuvable ou expiré")
        return chemin

    def rendu(self, ident, fond):
        """Chemin de l'image composée (détourage mis en cache pour changer de fond instantanément)."""
        if not fond:
            return self.original(ident)
        cible = self._chemin(ident, f"{fond}.jpg")
        if not cible.exists():
            cible.write_bytes(jpeg(self.atelier.composer(self.sujet(ident), fond)))
        return cible

    def sujet(self, ident):
        cache = self._chemin(ident, "detour.png")
        if cache.exists():
            return Image.open(cache).convert("RGBA")
        sujet = self.atelier.detourer(Image.open(self.original(ident)).convert("RGB"))
        sujet.save(cache)
        return sujet

    def supprimer(self, ident):
        for f in self.dossier.glob(f"{ident}-*"):
            f.unlink(missing_ok=True)

    def nettoyer(self, age_max=86400):
        import time
        limite = time.time() - age_max
        for f in self.dossier.iterdir():
            if f.stat().st_mtime < limite:
                f.unlink(missing_ok=True)
