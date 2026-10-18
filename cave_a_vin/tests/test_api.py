"""Tests de bout en bout de l'API : python -m unittest discover -s tests"""

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import cave  # noqa: E402
from app.db import Database  # noqa: E402
from app.server import Application, creer_serveur  # noqa: E402

PIXEL_PNG = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
             "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


class BaseTest(unittest.TestCase):
    api_key = ""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "cave.db")
        self.serveur = creer_serveur(Application(self.db, self.tmp.name, self.api_key), "127.0.0.1", 0)
        self.base = f"http://127.0.0.1:{self.serveur.server_address[1]}/"
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def tearDown(self):
        self.serveur.shutdown()
        self.serveur.server_close()
        self.db.close()
        self.tmp.cleanup()

    def appel(self, methode, chemin, corps=None, brut=None, entetes=None, attendu=None):
        data = brut if brut is not None else (json.dumps(corps).encode() if corps is not None else None)
        req = urllib.request.Request(self.base + chemin, data=data, method=methode, headers=entetes or {})
        try:
            with urllib.request.urlopen(req) as rep:
                status, contenu, type_ = rep.status, rep.read(), rep.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            status, contenu, type_ = e.code, e.read(), e.headers.get("Content-Type", "")
        if attendu is not None:
            self.assertEqual(status, attendu, contenu[:300])
        return json.loads(contenu) if type_.startswith("application/json") else contenu


class TestCave(BaseTest):
    def creer_vin(self, **champs):
        data = {"nom": "Château Test", "couleur": "rouge", "millesime": 2018, "region": "Bordeaux",
                "garde_debut": 2022, "garde_apogee": 2026, "garde_fin": 2035, "prix_achat": 20, "quantite": 6}
        data.update(champs)
        return self.appel("POST", "api/vins", data, attendu=201)

    def test_sante_et_interface(self):
        self.assertEqual(self.appel("GET", "api/health", attendu=200)["status"], "ok")
        page = self.appel("GET", "", attendu=200)
        self.assertIn(b"<title>Tessvine", page)
        self.assertIn(b"<title>Tessvine", self.appel("GET", "vins/12", attendu=200))  # repli SPA
        self.appel("GET", "../../etc/passwd", attendu=200)  # ne sort jamais du dossier static
        self.appel("GET", "api/inconnu", attendu=404)

    def test_cycle_de_vie_d_un_vin(self):
        vin = self.creer_vin()
        self.assertEqual(vin["stock"], 6)
        self.assertEqual(vin["mouvements"][0]["type"], "entree")
        vin = self.appel("POST", f"api/vins/{vin['id']}/sortie",
                         {"quantite": 2, "raison": "bue", "note": 4.5, "commentaire": "Superbe"}, attendu=200)
        self.assertEqual(vin["stock"], 4)
        self.assertEqual(vin["note_moyenne"], 4.5)
        self.appel("POST", f"api/vins/{vin['id']}/sortie", {"quantite": 10}, attendu=409)
        vin = self.appel("PUT", f"api/vins/{vin['id']}", {"domaine": "Domaine X", "favori": True}, attendu=200)
        self.assertEqual(vin["domaine"], "Domaine X")
        self.assertTrue(vin["favori"])
        self.assertEqual(vin["nom"], "Château Test")
        self.appel("POST", "api/vins", {"nom": ""}, attendu=400)
        self.appel("POST", "api/vins", {"nom": "X", "couleur": "violet"}, attendu=400)
        self.appel("DELETE", f"api/vins/{vin['id']}", attendu=200)
        self.appel("GET", f"api/vins/{vin['id']}", attendu=404)
        # l'historique reste, même après suppression du vin
        self.assertEqual(len(self.appel("GET", "api/mouvements")), 2)

    def test_plan_de_cave(self):
        c = self.appel("POST", "api/caves", {"nom": "Cave", "rangees": 2, "colonnes": 2}, attendu=201)
        vin = self.creer_vin(quantite=3, cave_id=c["id"])
        cases = sorted((b["rangee"], b["colonne"]) for b in vin["bouteilles"])
        self.assertEqual(cases, [(1, 1), (1, 2), (2, 1)])
        self.appel("POST", f"api/vins/{vin['id']}/entree", {"quantite": 2, "cave_id": c["id"]}, attendu=409)
        self.appel("POST", f"api/vins/{vin['id']}/entree",
                   {"quantite": 1, "cave_id": c["id"], "rangee": 1, "colonne": 1}, attendu=409)
        # un vin créé depuis une case du plan y est rangé ; les bouteilles suivantes vont dans les cases libres
        neuf = self.creer_vin(nom="Depuis le plan", quantite=1, cave_id=c["id"], rangee=2, colonne=2)
        self.assertEqual([(b["rangee"], b["colonne"]) for b in neuf["bouteilles"]], [(2, 2)])
        self.appel("DELETE", f"api/vins/{neuf['id']}", attendu=200)
        grand = self.appel("POST", "api/caves", {"nom": "Grande", "rangees": 3, "colonnes": 3}, attendu=201)
        trois = self.creer_vin(nom="Trois", quantite=3, cave_id=grand["id"], rangee=3, colonne=3)
        self.assertEqual(sorted((b["rangee"], b["colonne"]) for b in trois["bouteilles"]), [(1, 1), (1, 2), (3, 3)])
        self.appel("DELETE", f"api/caves/{grand['id']}", attendu=200)
        b = vin["bouteilles"][0]
        self.appel("PUT", f"api/bouteilles/{b['id']}", {"cave_id": c["id"], "rangee": 2, "colonne": 2}, attendu=200)
        self.appel("PUT", f"api/caves/{c['id']}", {"nom": "Cave", "rangees": 1, "colonnes": 2}, attendu=409)
        detail = self.appel("GET", f"api/caves/{c['id']}", attendu=200)
        self.assertEqual(len(detail["bouteilles"]), 3)
        self.assertEqual(self.appel("GET", f"api/vins?cave_id={c['id']}")[0]["id"], vin["id"])
        self.appel("DELETE", f"api/caves/{c['id']}", attendu=200)
        vin = self.appel("GET", f"api/vins/{vin['id']}")
        self.assertTrue(all(b["cave_id"] is None for b in vin["bouteilles"]))

    def test_etageres(self):
        cave = self.appel("POST", "api/caves", {"nom": "Armoire", "rangees": 3, "colonnes": 4}, attendu=201)
        etagere = self.appel("POST", "api/caves", {"parent_id": cave["id"], "position": "bas", "rangees": 2, "colonnes": 3},
                             attendu=201)
        self.assertEqual(etagere["nom"], "")  # nom facultatif
        self.appel("POST", "api/caves", {"parent_id": cave["id"], "position": "nulle", "rangees": 2, "colonnes": 2}, attendu=400)
        self.appel("POST", "api/caves", {"parent_id": etagere["id"], "rangees": 2, "colonnes": 2}, attendu=400)
        vin = self.creer_vin(quantite=2)
        bouteilles = self.appel("GET", f"api/vins/{vin['id']}")["bouteilles"]
        self.appel("PUT", f"api/bouteilles/{bouteilles[0]['id']}", {"cave_id": etagere["id"], "rangee": 2, "colonne": 3}, attendu=200)
        complete = self.appel("GET", f"api/caves/{cave['id']}")
        self.assertEqual([e["id"] for e in complete["etageres"]], [etagere["id"]])
        caves = {c["id"]: c for c in self.appel("GET", "api/caves")}
        self.assertEqual((caves[cave["id"]]["bouteilles"], caves[cave["id"]]["capacite"]), (1, 18))
        self.assertEqual(caves[etagere["id"]]["nom_complet"], "Armoire · étagère du bas")
        self.assertEqual(len(self.appel("GET", f"api/vins?cave_id={cave['id']}")), 1)  # le filtre inclut les étagères
        b = self.appel("GET", f"api/vins/{vin['id']}")["bouteilles"]
        self.assertIn(("Armoire · étagère du bas", cave["id"]), [(x["cave_nom"], x["cave_racine"]) for x in b])
        self.assertEqual([c["id"] for c in self.appel("GET", "api/stats")["par_cave"] if c["id"]], [cave["id"]])
        # supprimer l'étagère : sa bouteille reste dans la cave, sans emplacement précis
        self.appel("DELETE", f"api/caves/{etagere['id']}", attendu=200)
        b = [x for x in self.appel("GET", f"api/vins/{vin['id']}")["bouteilles"] if x["cave_id"]]
        self.assertEqual([(x["cave_id"], x["rangee"]) for x in b], [(cave["id"], None)])

    def test_ranger_sur_les_emplacements_choisis(self):
        cave = self.appel("POST", "api/caves", {"nom": "Casier", "rangees": 2, "colonnes": 3}, attendu=201)
        etagere = self.appel("POST", "api/caves", {"parent_id": cave["id"], "position": "droite", "rangees": 2, "colonnes": 2},
                             attendu=201)
        choix = [{"cave_id": cave["id"], "rangee": 2, "colonne": 3}, {"cave_id": etagere["id"], "rangee": 1, "colonne": 2}]
        vin = self.creer_vin(quantite=3, cave_id=cave["id"], emplacements=choix)
        places = sorted((b["cave_id"], b["rangee"], b["colonne"]) for b in self.appel("GET", f"api/vins/{vin['id']}")["bouteilles"])
        # les deux choisies, et la troisième dans la première place libre du casier du premier choix
        self.assertEqual(places, sorted([(cave["id"], 2, 3), (etagere["id"], 1, 2), (cave["id"], 1, 1)]))
        # emplacement déjà occupé, trop d'emplacements, doublon
        self.appel("POST", f"api/vins/{vin['id']}/entree", {"quantite": 1, "emplacements": choix[:1]}, attendu=409)
        libres = [{"cave_id": etagere["id"], "rangee": 2, "colonne": c} for c in (1, 2)]
        self.appel("POST", f"api/vins/{vin['id']}/entree", {"quantite": 1, "emplacements": libres}, attendu=400)
        self.appel("POST", f"api/vins/{vin['id']}/entree", {"quantite": 2, "emplacements": [libres[0], libres[0]]}, attendu=400)
        self.appel("POST", f"api/vins/{vin['id']}/entree", {"quantite": 2, "emplacements": libres}, attendu=200)
        self.assertEqual(self.appel("GET", f"api/vins/{vin['id']}")["stock"], 5)

    def test_garde_et_statuts(self):
        self.assertEqual(cave.statut_garde({"garde_debut": 2030, "garde_fin": 2040}, 2026), "trop_jeune")
        self.assertEqual(cave.statut_garde({"garde_debut": 2020, "garde_fin": 2030}, 2026), "a_boire")
        self.assertEqual(cave.statut_garde({"garde_debut": 2020, "garde_apogee": 2025, "garde_fin": 2030}, 2026), "apogee")
        self.assertEqual(cave.statut_garde({"garde_debut": 2020, "garde_fin": 2026}, 2026), "urgent")
        self.assertEqual(cave.statut_garde({"garde_debut": 2020, "garde_fin": 2024}, 2026), "depasse")
        self.assertEqual(cave.statut_garde({}, 2026), "inconnu")
        fenetre = lambda g: (g["garde_debut"], g["garde_apogee"], g["garde_fin"])
        # le prix l'emporte : un Médoc à 5 € n'est pas un vin de garde, un Pauillac à 120 € si
        g = self.appel("GET", "api/garde?couleur=rouge&millesime=2023&region=Bordeaux&appellation=M%C3%A9doc&prix_achat=4,69")
        self.assertEqual((fenetre(g), g["niveau"]), ((2024, 2025, 2028), "courant"))
        g = self.appel("GET", "api/garde?couleur=rouge&millesime=2015&appellation=Pauillac&valeur=120")
        self.assertEqual(fenetre(g), (2023, 2030, 2045))
        # sans prix : l'appellation décide, prudemment
        self.assertEqual(self.appel("GET", "api/garde?couleur=rouge&millesime=2015&appellation=Pauillac")["niveau"], "garde")
        self.assertEqual(self.appel("GET", "api/garde?couleur=rouge&millesime=2022&appellation=Bordeaux")["niveau"], "courant")
        self.assertEqual(self.appel("GET", "api/garde?couleur=rouge&millesime=2021&appellation=Haut-M%C3%A9doc")["niveau"], "moyen")
        # non millésimé : garde comptée à partir de l'achat, avec le même potentiel qu'un millésimé
        annee = cave.annee_courante()
        g = self.appel("GET", "api/garde?couleur=effervescent&appellation=Champagne&valeur=60")
        self.assertEqual((fenetre(g), g["reference"]), ((annee, annee + 4, annee + 9), "achat"))
        g = self.appel("GET", "api/garde?couleur=effervescent&appellation=Champagne&annee_achat=2020")
        self.assertEqual(fenetre(g), (2020, 2022, 2025))
        g = self.appel("GET", "api/garde?couleur=rose&prix_achat=6")
        self.assertEqual(fenetre(g), (annee, annee + 1, annee + 2))

    def test_suggestions_et_statistiques(self):
        annee = cave.annee_courante()
        self.creer_vin(nom="Vieux Bordeaux", garde_debut=annee - 10, garde_apogee=annee - 3, garde_fin=annee)
        self.creer_vin(nom="Chablis", couleur="blanc", region="Bourgogne", appellation="Chablis",
                       garde_debut=annee - 1, garde_apogee=None, garde_fin=annee + 3, quantite=2)
        self.creer_vin(nom="Trop jeune", garde_debut=annee + 5, garde_fin=annee + 20)
        noms = [s["vin"]["nom"] for s in self.appel("GET", "api/suggestion?plat=fruits_de_mer")]
        self.assertEqual(noms, ["Chablis"])
        noms = [s["vin"]["nom"] for s in self.appel("GET", "api/suggestion?plat=viande_rouge")]
        self.assertEqual(noms[0], "Vieux Bordeaux")
        self.assertNotIn("Trop jeune", noms)
        stats = self.appel("GET", "api/stats", attendu=200)
        self.assertEqual(stats["bouteilles"], 14)
        self.assertEqual(stats["references"], 3)
        self.assertEqual(stats["valeur"], 280)
        self.assertEqual([v["nom"] for v in stats["urgents"]], ["Vieux Bordeaux"])
        resume = self.appel("GET", "api/ha/resume", attendu=200)
        self.assertEqual(resume["climat"], {"configure": False})

    def test_recherche_et_filtres(self):
        self.creer_vin(nom="Pommard", region="Bourgogne", cepages="Pinot noir")
        self.creer_vin(nom="Sancerre", couleur="blanc", region="Loire", quantite=0)
        self.assertEqual([v["nom"] for v in self.appel("GET", "api/vins?q=pinot")], ["Pommard"])
        self.assertEqual(self.appel("GET", "api/vins"), self.appel("GET", "api/vins?stock=1"))
        self.assertEqual([v["nom"] for v in self.appel("GET", "api/vins?stock=0")], ["Sancerre"])
        self.assertEqual(len(self.appel("GET", "api/vins?stock=all&couleur=blanc")), 1)
        self.assertIn("Bourgogne", self.appel("GET", "api/referentiel")["autocompletion"]["regions"])

    def test_photo(self):
        vin = self.creer_vin()
        self.appel("PUT", f"api/vins/{vin['id']}/photo", {"image": "pas une image"}, attendu=400)
        self.appel("PUT", f"api/vins/{vin['id']}/photo", {"image": PIXEL_PNG}, attendu=200)
        self.assertTrue(self.appel("GET", f"api/vins/{vin['id']}")["a_photo"])
        self.assertTrue(self.appel("GET", f"api/vins/{vin['id']}/photo", attendu=200)[:2] in (b"\x89P", b"\xff\xd8"))
        self.appel("DELETE", f"api/vins/{vin['id']}/photo", attendu=200)
        self.appel("GET", f"api/vins/{vin['id']}/photo", attendu=404)

    def test_envies(self):
        e = self.appel("POST", "api/envies", {"nom": "Meursault 2020"}, attendu=201)
        self.appel("PUT", f"api/envies/{e['id']}", {"fait": True}, attendu=200)
        self.assertTrue(self.appel("GET", "api/envies")[0]["fait"])
        self.appel("DELETE", f"api/envies/{e['id']}", attendu=200)
        self.assertEqual(self.appel("GET", "api/envies"), [])

    def test_import_export(self):
        self.creer_vin(nom="Vin ; avec point-virgule", quantite=3)
        csv_texte = self.appel("GET", "api/export.csv", attendu=200).decode("utf-8-sig")
        sauvegarde = self.appel("GET", "api/export.json", attendu=200)
        res = self.appel("POST", "api/import.csv", brut=csv_texte.encode(), attendu=200)
        self.assertEqual(res, {"vins_crees": 1, "erreurs": []})
        self.assertEqual(self.appel("GET", "api/stats")["bouteilles"], 6)
        virgules = "nom,couleur,millesime,quantite\nTest virgule,blanc,2020,2\n"
        self.assertEqual(self.appel("POST", "api/import.csv", brut=virgules.encode())["vins_crees"], 1)
        self.appel("POST", "api/import.json", sauvegarde, attendu=200)
        self.assertEqual(self.appel("GET", "api/stats")["bouteilles"], 3)
        self.appel("POST", "api/import.json", {"autre": 1}, attendu=400)

    def test_sauvegarde_piegee(self):
        vin = self.creer_vin()
        sauvegarde = self.appel("GET", "api/export.json")
        sauvegarde["vins"][0]["photo"] = "../cave.db"
        self.appel("POST", "api/import.json", sauvegarde, attendu=200)
        self.appel("GET", f"api/vins/{vin['id']}/photo", attendu=404)
        self.appel("DELETE", f"api/vins/{vin['id']}", attendu=200)
        self.assertTrue((Path(self.tmp.name) / "cave.db").exists())

    def test_reglages(self):
        r = self.appel("PUT", "api/reglages", {"ha_url": "http://ha.local:8123", "ha_token": "secret",
                                               "capteur_temperature": "sensor.cave"}, attendu=200)
        self.assertTrue(r["ha_token_defini"])
        self.assertNotIn("ha_token", r)
        # un jeton vide ne remplace pas le jeton existant
        self.appel("PUT", "api/reglages", {"ha_token": ""}, attendu=200)
        self.assertTrue(self.appel("GET", "api/reglages")["ha_token_defini"])


class TestCleAPI(BaseTest):
    api_key = "s3cret"

    def test_cle_obligatoire(self):
        self.appel("GET", "api/stats", attendu=401)
        self.appel("GET", "api/stats", entetes={"X-API-Key": "mauvaise"}, attendu=401)
        self.appel("GET", "api/stats", entetes={"X-API-Key": "s3cret"}, attendu=200)
        self.appel("GET", "api/stats", entetes={"Authorization": "Bearer s3cret"}, attendu=200)
        self.appel("GET", "", attendu=200)  # l'interface elle-même reste accessible


if __name__ == "__main__":
    unittest.main()
