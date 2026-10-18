"""Ajout assisté : code-barres (Open Food Facts), photo détourée sur fond, lecture d'étiquette par l'IA."""

import base64
import io
import json
import os
import sqlite3
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from test_api import BaseTest

from app import ia, photo, scan
from app.db import Database

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None

PRODUIT_OFF = {
    "product_name": "Baron de Lestac Réserve 2023",
    "brands": "Baron de Lestac,Castel",
    "categories": "Boissons, Boissons alcoolisées, Vins, Vins français, Vins rouges, Vins de Bordeaux, Médoc",
    "categories_tags": ["en:beverages", "en:wines", "en:red-wines", "en:bordeaux-wines", "fr:medoc"],
    "quantity": "75 cl",
    "nutriments": {"alcohol_100g": 13.5},
    "image_front_url": "https://images.openfoodfacts.org/images/products/326/front_fr.jpg",
}


def photo_de_bouteille():
    """Bouteille sombre sur un fond clair et chargé, en JPEG."""
    img = Image.new("RGB", (600, 800), (215, 205, 190))
    d = ImageDraw.Draw(img)
    d.rectangle((20, 40, 200, 80), fill=(160, 60, 50))
    d.rectangle((260, 120, 340, 260), fill=(30, 45, 25))
    d.rectangle((220, 260, 380, 740), fill=(30, 45, 25))
    d.rectangle((235, 450, 365, 600), fill=(240, 230, 210))
    tampon = io.BytesIO()
    img.save(tampon, "JPEG")
    return tampon.getvalue()


def masque_sombre(img):
    """Remplace le réseau de neurones : tout ce qui est sombre ou l'étiquette fait partie de la bouteille."""
    gris = img.convert("L")
    masque = gris.point(lambda v: 255 if v < 80 else 0)
    ImageDraw.Draw(masque).rectangle((235, 450, 365, 600), fill=255)
    return masque


class FauxServeur:
    """Petit serveur HTTP de test : renvoie des réponses programmées et mémorise les requêtes."""

    def __init__(self, repondre):
        self.requetes = []
        exterieur = self

        class Gestion(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _traiter(self):
                corps = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                exterieur.requetes.append((self.command, self.path, corps, dict(self.headers)))
                status, reponse = repondre(self.command, self.path, corps)
                donnees = json.dumps(reponse).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(donnees)))
                self.end_headers()
                self.wfile.write(donnees)

            do_GET = do_POST = _traiter

        self.serveur = ThreadingHTTPServer(("127.0.0.1", 0), Gestion)
        self.url = f"http://127.0.0.1:{self.serveur.server_address[1]}"
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def arreter(self):
        self.serveur.shutdown()
        self.serveur.server_close()


class TestOpenFoodFacts(unittest.TestCase):
    def test_conversion(self):
        r = scan.depuis_off(PRODUIT_OFF, "3263280122573")
        self.assertEqual(r["vin"], {
            "nom": "Baron de Lestac Réserve", "domaine": "Baron de Lestac", "appellation": "Médoc",
            "region": "Bordeaux", "pays": "France", "couleur": "rouge", "millesime": 2023, "degre": 13.5,
            "format": "75 cl", "code_barre": "3263280122573"})
        self.assertTrue(r["image_url"].startswith("https://images.openfoodfacts.org/"))

    def test_formats_et_couleurs(self):
        self.assertEqual(scan._format("1,5 L"), "Magnum 1,5 L")
        self.assertEqual(scan._format("750 ml"), "75 cl")
        self.assertEqual(scan._format("37.5cl"), "37,5 cl")
        champagne = {"product_name": "Brut", "categories_tags": ["en:champagnes", "en:white-wines"]}
        self.assertEqual(scan.depuis_off(champagne, "1")["vin"]["couleur"], "effervescent")

    def test_securite(self):
        self.assertFalse(scan.image_autorisee("http://images.openfoodfacts.org/x.jpg"))
        self.assertFalse(scan.image_autorisee("https://evil.example/openfoodfacts.org.jpg"))
        self.assertFalse(scan.image_autorisee("https://openfoodfacts.org.evil.example/x.jpg"))
        with self.assertRaises(scan.ScanErreur):
            scan.nettoyer_code("abc")
        with self.assertRaises(scan.ScanErreur):
            scan.nettoyer_code("3263280122577")  # faute de frappe : mauvais chiffre de contrôle
        self.assertEqual(scan.nettoyer_code("3 263280 122573"), "3263280122573")
        self.assertEqual(scan.nettoyer_code("96385074"), "96385074")  # EAN-8


class TestScan(BaseTest):
    def setUp(self):
        super().setUp()

        def repondre(methode, chemin, corps):
            if "/3263280122573.json" in chemin:
                return 200, {"status": 1, "product": PRODUIT_OFF}
            return 404, {"status": 0}

        self.off = FauxServeur(repondre)
        patch = mock.patch.object(scan, "URL_OFF", self.off.url)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.off.arreter)

    def test_code_connu_d_open_food_facts(self):
        r = self.appel("GET", "api/scan/3263280122573", attendu=200)
        self.assertIsNone(r["local"])
        self.assertEqual(r["externe"]["vin"]["nom"], "Baron de Lestac Réserve")
        self.assertIn("CaveAVin", self.off.requetes[0][3]["User-Agent"])

    def test_code_inconnu(self):
        r = self.appel("GET", "api/scan/3000000000014", attendu=200)
        self.assertEqual((r["local"], r["externe"], r["erreur"]), (None, None, None))

    def test_code_deja_dans_la_cave(self):
        self.appel("POST", "api/vins", {"nom": "Mon Lestac", "code_barre": "3263-2801-22573", "quantite": 2}, attendu=201)
        r = self.appel("GET", "api/scan/3263280122573", attendu=200)
        self.assertEqual(r["local"]["nom"], "Mon Lestac")
        self.assertEqual(r["local"]["stock"], 2)
        self.assertEqual(len(self.off.requetes), 0)  # pas besoin d'Internet
        self.assertEqual([v["nom"] for v in self.appel("GET", "api/vins?q=3263280122573")], ["Mon Lestac"])

    def test_off_injoignable(self):
        with mock.patch.object(scan, "URL_OFF", "http://127.0.0.1:1"):
            r = self.appel("GET", "api/scan/3263280122573", attendu=200)
        self.assertIn("injoignable", r["erreur"])


@unittest.skipUnless(Image, "Pillow non installé")
class TestPhotos(BaseTest):
    def setUp(self):
        super().setUp()
        app = self.serveur.RequestHandlerClass.app
        patch = mock.patch.object(app.atelier, "masque", masque_sombre)
        patch.start()
        self.addCleanup(patch.stop)
        patch2 = mock.patch.object(photo, "detourage_disponible", lambda: True)
        patch2.start()
        self.addCleanup(patch2.stop)
        self.image = "data:image/jpeg;base64," + base64.b64encode(photo_de_bouteille()).decode()

    def test_capacites(self):
        c = self.appel("GET", "api/capacites", attendu=200)
        self.assertEqual([f["id"] for f in c["fonds"]], list(photo.FONDS))
        self.assertFalse(c["ia"]["possible"])
        for f in photo.FONDS:  # chaque fond annoncé existe bien
            self.assertTrue(self.appel("GET", f"fonds/{f}.jpg", attendu=200).startswith(b"\xff\xd8"))

    def test_brouillon_detoure_puis_vin(self):
        ident = self.appel("POST", "api/brouillons", {"image": self.image}, attendu=201)["id"]
        self.appel("POST", f"api/brouillons/{ident}/rendu", {"fond": "cave-voutee"}, attendu=200)
        rendu = Image.open(io.BytesIO(self.appel("GET", f"api/brouillons/{ident}/image?fond=cave-voutee", attendu=200)))
        self.assertEqual(rendu.size, (1200, 1600))
        # le centre de l'image est la bouteille (sombre), les côtés le fond de cave (pas le mur clair d'origine)
        self.assertLess(sum(rendu.getpixel((600, 1200))), 200)
        self.assertNotEqual(rendu.getpixel((40, 400)), (215, 205, 190))
        self.appel("POST", f"api/brouillons/{ident}/rendu", {"fond": "inexistant"}, attendu=422)
        self.appel("POST", f"api/brouillons/{ident}/rendu", {"fond": "studio", "cadrage": "entiere"}, attendu=200)
        self.appel("GET", f"api/brouillons/{ident}/image?fond=studio&cadrage=entiere", attendu=200)

        vin = self.appel("POST", "api/vins", {"nom": "Photo test", "quantite": 1,
                                              "photo": {"brouillon": ident, "fond": "studio"}}, attendu=201)
        self.assertTrue(vin["a_photo"] and vin["a_photo_originale"])
        self.appel("GET", f"api/brouillons/{ident}/image", attendu=422)  # brouillon consommé
        originale = Image.open(io.BytesIO(self.appel("GET", f"api/vins/{vin['id']}/photo?original=1")))
        self.assertEqual(originale.size, (600, 800))

        # changer de fond, puis revenir à la photo d'origine
        self.appel("POST", f"api/vins/{vin['id']}/photo/fond", {"fond": "casier-bois"}, attendu=200)
        self.assertEqual(Image.open(io.BytesIO(self.appel("GET", f"api/vins/{vin['id']}/photo"))).size, (1200, 1600))
        self.appel("POST", f"api/vins/{vin['id']}/photo/fond", {"fond": "studio", "cadrage": "entiere"}, attendu=200)
        self.appel("POST", f"api/vins/{vin['id']}/photo/fond", {"fond": ""}, attendu=200)
        self.assertEqual(Image.open(io.BytesIO(self.appel("GET", f"api/vins/{vin['id']}/photo"))).size, (600, 800))

        # suppression : plus aucun fichier photo ne traîne
        dossier = Path(self.tmp.name) / "photos"
        self.appel("DELETE", f"api/vins/{vin['id']}", attendu=200)
        self.assertEqual(list(dossier.iterdir()), [])

    def test_photo_sur_fond_depuis_la_fiche(self):
        vin = self.appel("POST", "api/vins", {"nom": "Fiche"}, attendu=201)
        r = self.appel("PUT", f"api/vins/{vin['id']}/photo", {"image": self.image, "fond": "pierre-claire"}, attendu=200)
        self.assertIsNone(r["avertissement"])
        self.assertEqual(Image.open(io.BytesIO(self.appel("GET", f"api/vins/{vin['id']}/photo"))).size, (1200, 1600))

    def test_gros_plan_agrandit_l_etiquette(self):
        """Le cadrage « etiquette » rend l'étiquette (rectangle clair) bien plus grande que « entiere »."""
        ident = self.appel("POST", "api/brouillons", {"image": self.image}, attendu=201)["id"]

        def hauteur_etiquette(cadrage):
            img = Image.open(io.BytesIO(self.appel("GET", f"api/brouillons/{ident}/image?fond=studio&cadrage={cadrage}")))
            colonne = [img.getpixel((600, y)) for y in range(img.height)]
            return sum(1 for p in colonne if min(p) > 200)  # pixels de l'étiquette claire sur la colonne centrale

        entiere, gros_plan = hauteur_etiquette("entiere"), hauteur_etiquette("etiquette")
        self.assertGreater(entiere, 100)
        self.assertGreater(gros_plan, 1.7 * entiere)
        self.assertEqual(self.appel("GET", "api/capacites")["cadrage_defaut"], "etiquette")
        self.appel("PUT", "api/reglages", {"cadrage_defaut": "entiere"})
        self.assertEqual(self.appel("GET", "api/capacites")["cadrage_defaut"], "entiere")

    def test_aucune_bouteille(self):
        vide = Image.new("RGB", (300, 400), (230, 230, 230))
        tampon = io.BytesIO()
        vide.save(tampon, "JPEG")
        ident = self.appel("POST", "api/brouillons", {"image": "data:image/jpeg;base64," + base64.b64encode(tampon.getvalue()).decode()})["id"]
        with mock.patch.object(self.serveur.RequestHandlerClass.app.atelier, "masque", lambda img: img.convert("L").point(lambda v: 0)):
            r = self.appel("POST", f"api/brouillons/{ident}/rendu", {"fond": "studio"}, attendu=422)
        self.assertIn("Aucune bouteille", r["erreur"])

    def test_brouillon_securite(self):
        self.appel("GET", "api/brouillons/..%2F..%2Fcave/image", attendu=404)
        self.appel("POST", "api/brouillons", {"url": "https://evil.example/x.jpg"}, attendu=422)
        self.appel("POST", "api/brouillons", {"image": "data:text/html;base64,PGgxPg=="}, attendu=400)


@unittest.skipUnless(Image, "Pillow non installé")
class TestLectureEtiquette(BaseTest):
    def setUp(self):
        super().setUp()
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.reponse_ia = {"nom": "Château de Cach", "domaine": "Henri Musso", "appellation": "Haut-Médoc",
                           "region": "Bordeaux", "couleur": "Vin rouge", "millesime": 2019.0, "degre": "13,5",
                           "cepages": ["Merlot", "Cabernet sauvignon"], "pays": "inconnu", "valeur": "15 €",
                           "accords": "Agneau, entrecôte, fromages affinés", "description": "Haut-Médoc classique."}
        self.fichiers_vus = []
        self.entites_ha = [{"entity_id": "ai_task.claude", "state": "2026-10-18T10:00:00",
                            "attributes": {"friendly_name": "Claude AI Task"}}]
        ia._cache_entites["cle"] = None

        def repondre(methode, chemin, corps):
            if chemin.startswith("/api/services/ai_task/generate_data?return_response"):
                demande = json.loads(corps)
                if "entity_id" not in demande:  # comportement réel de Home Assistant sans IA préférée
                    return 500, {"message": "No entity_id provided and no preferred entity set"}
                fichier = demande["attachments"][0]["media_content_id"].split("/local/")[1]
                self.fichiers_vus.append((Path(self.media.name) / fichier).exists())
                return 200, {"changed_states": [], "service_response": {"conversation_id": "x", "data": self.reponse_ia}}
            if chemin == "/api/states":
                return 200, self.entites_ha + [{"entity_id": "sensor.cave", "state": "12", "attributes": {}}]
            return 404, {}

        self.ha = FauxServeur(repondre)
        self.addCleanup(self.ha.arreter)
        env = mock.patch.dict(os.environ, {"HA_MEDIA_DIR": self.media.name})
        env.start()
        self.addCleanup(env.stop)
        self.appel("PUT", "api/reglages", {"ha_url": self.ha.url, "ha_token": "jeton", "ia_entite": "ai_task.claude"})

    def test_lecture(self):
        self.assertTrue(self.appel("GET", "api/capacites")["ia"]["possible"])
        self.assertEqual(self.appel("GET", "api/ia/entites"),
                         [{"entity_id": "ai_task.claude", "nom": "Claude AI Task", "etat": "2026-10-18T10:00:00"}])
        image = "data:image/jpeg;base64," + base64.b64encode(photo_de_bouteille()).decode()
        ident = self.appel("POST", "api/brouillons", {"image": image})["id"]
        champs = self.appel("POST", f"api/brouillons/{ident}/lire", attendu=200)["champs"]
        self.assertEqual(champs, {"nom": "Château de Cach", "domaine": "Henri Musso", "appellation": "Haut-Médoc",
                                  "region": "Bordeaux", "couleur": "rouge", "millesime": 2019, "degre": 13.5,
                                  "cepages": "Merlot, Cabernet sauvignon", "valeur": 15.0,
                                  "accords": "Agneau, entrecôte, fromages affinés", "notes": "Haut-Médoc classique."})
        demande = json.loads(self.ha.requetes[-1][2])
        self.assertTrue(all(demande["structure"][c].get("required") for c in ("nom", "domaine", "couleur", "region", "accords")))
        self.assertNotIn("N'invente rien", demande["instructions"])
        self.assertEqual(self.fichiers_vus, [True])  # la photo était bien disponible pour l'IA…
        self.assertEqual(list((Path(self.media.name) / "cave_a_vin").iterdir()), [])  # … puis supprimée
        demande = json.loads(self.ha.requetes[-1][2])
        self.assertEqual(demande["entity_id"], "ai_task.claude")
        self.assertEqual(self.ha.requetes[-1][3]["Authorization"], "Bearer jeton")

    def test_lecture_avec_verso(self):
        image = "data:image/jpeg;base64," + base64.b64encode(photo_de_bouteille()).decode()
        ident = self.appel("POST", "api/brouillons", {"image": image})["id"]
        self.reponse_ia = {**self.reponse_ia, "code_barre": "3 760 123 456 789"}
        champs = self.appel("POST", f"api/brouillons/{ident}/lire", {"verso": image}, attendu=200)["champs"]
        self.assertEqual(champs["code_barre"], "3760123456789")
        demande = json.loads(self.ha.requetes[-1][2])
        self.assertEqual(len(demande["attachments"]), 2)  # étiquette + contre-étiquette en une seule demande
        self.assertIn("verso", demande["attachments"][1]["media_content_id"])
        self.assertEqual(list((Path(self.media.name) / "cave_a_vin").iterdir()), [])  # rien n'est conservé
        self.reponse_ia = {**self.reponse_ia, "code_barre": "illisible"}
        self.assertNotIn("code_barre", self.appel("POST", f"api/brouillons/{ident}/lire", attendu=200)["champs"])

    def test_couleurs_en_texte_libre(self):
        attendus = {"Vin rouge": "rouge", "Blanc sec": "blanc", "Rosé": "rose", "Champagne brut": "effervescent",
                    "Crémant de Loire": "effervescent", "Moelleux": "liquoreux", "rose": "rose", "violet": None}
        for texte, couleur in attendus.items():
            self.assertEqual(ia.couleur_depuis(texte), couleur, texte)

    def test_choix_automatique_de_l_ia(self):
        """Sans IA choisie ni IA préférée dans Home Assistant : la cave prend la première « tâche IA » disponible."""
        self.appel("PUT", "api/reglages", {"ia_entite": ""})
        self.entites_ha = [{"entity_id": "ai_task.hors_ligne", "state": "unavailable", "attributes": {}}] + self.entites_ha
        image = "data:image/jpeg;base64," + base64.b64encode(photo_de_bouteille()).decode()
        ident = self.appel("POST", "api/brouillons", {"image": image})["id"]
        self.appel("POST", f"api/brouillons/{ident}/lire", attendu=200)
        self.assertEqual(json.loads(self.ha.requetes[-1][2])["entity_id"], "ai_task.claude")

    def test_aucune_ia_dans_home_assistant(self):
        self.appel("PUT", "api/reglages", {"ia_entite": ""})
        self.entites_ha = []
        image = "data:image/jpeg;base64," + base64.b64encode(photo_de_bouteille()).decode()
        ident = self.appel("POST", "api/brouillons", {"image": image})["id"]
        erreur = self.appel("POST", f"api/brouillons/{ident}/lire", attendu=422)["erreur"]
        self.assertIn("aucune intégration d'IA", erreur)
        self.assertNotIn("No entity_id", erreur)
        # avec un agent de conversation IA mais sans tâche IA : on nomme l'intégration à compléter
        ia._cache_entites["cle"] = None
        self.entites_ha = [{"entity_id": "conversation.claude", "state": "x", "attributes": {"friendly_name": "Claude conversation"}}]
        diag = self.appel("GET", "api/ia/diagnostic")
        self.assertEqual((diag["taches_ia"], diag["agents_conversation"]), ([], ["Claude conversation"]))
        self.assertIn("Ajouter une tâche IA", diag["conseil"])

    def test_ia_desactivee(self):
        self.appel("PUT", "api/reglages", {"ia_active": "0"})
        self.assertFalse(self.appel("GET", "api/capacites")["ia"]["possible"])
        image = "data:image/jpeg;base64," + base64.b64encode(photo_de_bouteille()).decode()
        ident = self.appel("POST", "api/brouillons", {"image": image})["id"]
        self.appel("POST", f"api/brouillons/{ident}/lire", attendu=422)


class TestMigration(unittest.TestCase):
    def test_base_version_1_0(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "cave.db"
            ancienne = sqlite3.connect(chemin)
            ancienne.execute("""CREATE TABLE vins (id INTEGER PRIMARY KEY, nom TEXT NOT NULL, domaine TEXT NOT NULL DEFAULT '',
                appellation TEXT NOT NULL DEFAULT '', region TEXT NOT NULL DEFAULT '', pays TEXT NOT NULL DEFAULT 'France',
                couleur TEXT NOT NULL DEFAULT 'rouge', millesime INTEGER, cepages TEXT NOT NULL DEFAULT '',
                format TEXT NOT NULL DEFAULT '75 cl', degre REAL, prix_achat REAL, valeur REAL,
                fournisseur TEXT NOT NULL DEFAULT '', garde_debut INTEGER, garde_apogee INTEGER, garde_fin INTEGER,
                accords TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', photo TEXT,
                favori INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            ancienne.execute("INSERT INTO vins (nom, created_at, updated_at) VALUES ('Ancien', 'x', 'x')")
            ancienne.commit()
            ancienne.close()
            db = Database(chemin)
            self.assertEqual(db.one("SELECT nom, code_barre, photo_originale FROM vins"),
                             {"nom": "Ancien", "code_barre": "", "photo_originale": None})
            db.close()


if __name__ == "__main__":
    unittest.main()
