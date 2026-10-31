"""Statuts de garde (plateau d'apogée) et estimation de la garde par l'IA de Home Assistant."""

import json
import unittest
from datetime import datetime, timedelta

from test_ajout import FauxServeur
from test_api import BaseTest

from app import cave, garde_ia


class TestStatuts(unittest.TestCase):
    def test_plateau_puis_declin(self):
        vin = {"garde_debut": 2020, "garde_apogee": 2025, "garde_fin": 2035}  # plateau 2025-2028
        attendus = {2019: "trop_jeune", 2022: "a_boire", 2025: "apogee", 2028: "apogee", 2029: "declin",
                    2034: "declin", 2035: "urgent", 2036: "depasse"}
        for annee, statut in attendus.items():
            self.assertEqual(cave.statut_garde(vin, annee), statut, annee)

    def test_vin_courant(self):
        # Médoc à 5 € : 2024 → apogée 2025 → 2028 ; en 2026 il n'est plus « à l'apogée » mais à boire
        vin = {"garde_debut": 2024, "garde_apogee": 2025, "garde_fin": 2028}
        self.assertEqual(cave.statut_garde(vin, 2025), "apogee")
        self.assertEqual(cave.statut_garde(vin, 2026), "declin")
        self.assertEqual(cave.statut_garde({"garde_debut": 2024, "garde_fin": 2030}, 2026), "a_boire")


class TestGardeIA(BaseTest):
    def setUp(self):
        super().setUp()
        self.reponses = []  # réponses successives de l'IA
        self.demandes = []

        def repondre(methode, chemin, corps):
            if chemin.startswith("/api/services/ai_task/generate_data"):
                self.demandes.append(json.loads(corps))
                reponse = self.reponses.pop(0) if self.reponses else {"garde_debut": 2024, "garde_apogee": 2027,
                                                                       "garde_fin": 2032, "justification": "Médoc classique.",
                                                                       "confiance": "moyenne"}
                if reponse == "erreur":
                    return 500, {"message": "panne"}
                return 200, {"service_response": {"data": reponse}}
            return 404, {}

        self.ha = FauxServeur(repondre)
        self.addCleanup(self.ha.arreter)
        self.appel("PUT", "api/reglages", {"ha_url": self.ha.url, "ha_token": "jeton"})
        self.app = self.serveur.RequestHandlerClass.app
        self.app.planificateur.pause = 0
        self.en_arriere_plan = []
        # l'estimation automatique à la création est testée à part (test_estimation_a_la_creation)
        self.app.planificateur.estimer_en_arriere_plan = self.en_arriere_plan.append

    def creer(self, **champs):
        data = {"nom": "Château Test", "millesime": 2022, "appellation": "Médoc", "quantite": 2, "garde_source": ""}
        data.update(champs)
        return self.appel("POST", "api/vins", data, attendu=201)

    def test_estimation_appliquee(self):
        vin = self.creer(prix_achat=12)
        vin = self.appel("POST", f"api/vins/{vin['id']}/garde-ia", {}, attendu=200)
        self.assertEqual((vin["garde_debut"], vin["garde_apogee"], vin["garde_fin"]), (2024, 2027, 2032))
        self.assertEqual(vin["garde_source"], "ia")
        self.assertEqual(vin["garde_ia_note"], "Médoc classique. (confiance moyenne)")
        consigne = self.demandes[-1]["instructions"]
        self.assertIn("Millésime : 2022", consigne)
        self.assertIn("Appellation : Médoc", consigne)
        self.assertIn("Prix : environ 12 EUR", consigne)
        self.assertNotIn("attachments", self.demandes[-1])

    def test_garde_saisie_a_la_main_respectee(self):
        vin = self.creer(garde_debut=2030, garde_fin=2050, garde_source="manuel")
        self.app.planificateur.tout_estimer()
        vin = self.appel("GET", f"api/vins/{vin['id']}")
        self.assertEqual((vin["garde_debut"], vin["garde_fin"]), (2030, 2050))  # intacte…
        self.assertEqual((vin["garde_ia_debut"], vin["garde_ia_fin"]), (2024, 2032))  # … suggestion gardée à côté
        # modifier la garde dans le formulaire la protège aussi
        autre = self.creer(nom="Autre")
        self.appel("PUT", f"api/vins/{autre['id']}", {"garde_fin": 2040})
        self.assertEqual(self.appel("GET", f"api/vins/{autre['id']}")["garde_source"], "manuel")
        # modifier autre chose ne change pas l'origine
        self.appel("PUT", f"api/vins/{vin['id']}", {"notes": "x", "garde_debut": 2030, "garde_fin": 2050})
        self.assertEqual(self.appel("GET", f"api/vins/{vin['id']}")["garde_source"], "manuel")

    def test_estimation_a_la_creation(self):
        vin = self.creer(nom="Nouveau")
        self.assertEqual(self.en_arriere_plan, [vin["id"]])
        manuel = self.creer(nom="Manuel", garde_debut=2030, garde_fin=2040, garde_source="manuel")
        self.assertEqual(self.en_arriere_plan, [vin["id"]])  # pas d'IA pour une garde saisie à la main
        del self.app.planificateur.estimer_en_arriere_plan  # vraie méthode : un fil d'exécution séparé
        vin = self.creer(nom="Vrai")
        import time
        for _ in range(50):
            if self.appel("GET", f"api/vins/{vin['id']}")["garde_source"] == "ia":
                break
            time.sleep(0.1)
        self.assertEqual(self.appel("GET", f"api/vins/{vin['id']}")["garde_fin"], 2032)
        self.assertEqual(self.appel("GET", f"api/vins/{manuel['id']}")["garde_fin"], 2040)

    def test_saisie_pendant_que_l_ia_reflechit(self):
        vin = self.creer()
        reponse_ia = garde_ia.ia.estimer_garde

        def ia_lente(*args, **kwargs):
            resultat = reponse_ia(*args, **kwargs)
            self.appel("PUT", f"api/vins/{vin['id']}", {"garde_fin": 2050})  # l'utilisateur corrige entre-temps
            return resultat

        from unittest import mock
        with mock.patch.object(garde_ia.ia, "estimer_garde", ia_lente):
            garde_ia.estimer_vin(self.app.db, self.app.reglages(), vin["id"])
        vin = self.appel("GET", f"api/vins/{vin['id']}")
        self.assertEqual((vin["garde_fin"], vin["garde_source"], vin["garde_ia_fin"]), (2050, "manuel", 2032))
        # la demande explicite depuis la fiche remplace, elle
        vin = self.appel("POST", f"api/vins/{vin['id']}/garde-ia", {}, attendu=200)
        self.assertEqual((vin["garde_fin"], vin["garde_source"]), (2032, "ia"))

    def test_passage_mensuel(self):
        self.creer(nom="A")
        self.creer(nom="B", garde_debut=2023, garde_fin=2026)
        self.creer(nom="Épuisé", quantite=0)
        planif = self.app.planificateur
        self.assertTrue(planif.a_faire())
        planif.tout_estimer()
        self.assertEqual((planif.etat["fait"], planif.etat["total"], planif.etat["erreurs"]), (2, 2, []))
        self.assertFalse(planif.a_faire())  # rien avant un mois
        self.assertEqual(len(self.demandes), 2)  # le vin épuisé n'est pas estimé
        self.assertEqual([v["garde_source"] for v in self.appel("GET", "api/vins")], ["ia", "ia"])
        self.app.ecrire_reglage("ia_garde_derniere", (datetime.now() - timedelta(days=31)).isoformat())
        self.assertTrue(planif.a_faire())
        self.appel("PUT", "api/reglages", {"ia_garde_auto": "0"})
        self.assertFalse(planif.a_faire())

    def test_reponses_invalides_et_panne(self):
        vin = self.creer()
        self.reponses = [{"garde_debut": 2040, "garde_fin": 2030}]
        self.appel("POST", f"api/vins/{vin['id']}/garde-ia", {}, attendu=422)
        self.reponses = [{"garde_debut": 2023, "garde_apogee": 2099, "garde_fin": 2027}]
        vin = self.appel("POST", f"api/vins/{vin['id']}/garde-ia", {}, attendu=200)
        self.assertIsNone(vin["garde_apogee"])  # apogée hors fenêtre ignorée
        # panne de l'IA pendant le passage mensuel : on réessaiera demain, pas dans un mois
        self.reponses = ["erreur"]
        self.app.planificateur.tout_estimer()
        derniere = datetime.fromisoformat(self.app.reglages()["ia_garde_derniere"])
        self.assertLess(derniere, datetime.now() - timedelta(days=28))
        self.assertEqual(len(self.app.planificateur.etat["erreurs"]), 1)

    def test_api_lancement(self):
        self.creer()
        etat = self.appel("POST", "api/ia/gardes", {}, attendu=202)
        self.assertTrue(etat["ia"]["possible"])
        for _ in range(50):
            etat = self.appel("GET", "api/ia/gardes")
            if not etat["en_cours"] and etat["termine_le"]:
                break
            import time
            time.sleep(0.1)
        self.assertEqual(etat["fait"], 1)
        self.assertIsNotNone(etat["derniere"])

    def test_sans_millesime(self):
        vin = self.creer(millesime="", couleur="effervescent", appellation="Champagne")
        self.appel("POST", f"api/vins/{vin['id']}/garde-ia", {}, attendu=422)  # 2024 < achat 2026 - 1 : incohérent
        self.reponses = [{"garde_debut": cave.annee_courante(), "garde_apogee": cave.annee_courante() + 3,
                          "garde_fin": cave.annee_courante() + 8, "confiance": "faible"}]
        vin = self.appel("POST", f"api/vins/{vin['id']}/garde-ia", {}, attendu=200)
        self.assertIn(f"acheté en {cave.annee_courante()}", self.demandes[-1]["instructions"])
        self.assertEqual(vin["garde_ia_note"], "(confiance faible)")

    def test_devise_dans_la_consigne_de_garde(self):
        self.appel("PUT", "api/reglages", {"devise": "DKK"})
        vin = self.creer(prix_achat=90)
        self.appel("POST", f"api/vins/{vin['id']}/garde-ia", {}, attendu=200)
        self.assertIn("Prix : environ 90 DKK", self.demandes[-1]["instructions"])

    def test_devise_inconnue_refusee(self):
        self.appel("PUT", "api/reglages", {"devise": "XYZ"}, attendu=400)
        self.appel("PUT", "api/reglages", {"devise": "DKK"})
        self.assertEqual(self.appel("GET", "api/referentiel")["devise"], "DKK")

    def test_niveau_du_vin_selon_la_devise(self):
        # 100 DKK ≈ 13 € : un vin de milieu de gamme, pas un grand vin comme le serait 100 €
        self.assertEqual(cave.niveau_du_vin(prix=100, devise="DKK"), "moyen")
        self.assertEqual(cave.niveau_du_vin(prix=100, devise="EUR"), "grand")
        self.appel("PUT", "api/reglages", {"devise": "DKK"})
        garde = self.appel("GET", "api/garde?couleur=rouge&millesime=2020&prix_achat=100")
        self.assertEqual(garde["niveau"], "moyen")

    def test_reestimation_des_valeurs(self):
        a = self.creer(nom="A", valeur=15)
        b = self.creer(nom="B", valeur=40, quantite=0)  # épuisé : sa valeur est aussi réestimée
        self.appel("PUT", "api/reglages", {"devise": "DKK"})
        self.reponses = [{"valeur": "110 DKK"}, {"valeur": 300}]
        self.appel("POST", "api/ia/valeurs", {}, attendu=202)
        etat = {}
        for _ in range(50):
            etat = self.appel("GET", "api/ia/valeurs")
            if not etat["en_cours"] and etat["termine_le"]:
                break
            import time
            time.sleep(0.1)
        self.assertEqual((etat["fait"], etat["total"], etat["erreurs"]), (2, 2, []))
        consigne = self.demandes[0]["instructions"]
        self.assertIn("en DKK", consigne)
        self.assertNotIn("Prix :", consigne)  # l'ancien prix, dans une autre devise, ne doit pas orienter l'IA
        self.assertIn("DKK", self.demandes[0]["structure"]["valeur"]["description"])
        self.assertEqual(self.appel("GET", f"api/vins/{a['id']}")["valeur"], 110)
        self.assertEqual(self.appel("GET", f"api/vins/{b['id']}")["valeur"], 300)

    def test_reestimation_valeur_invalide_garde_l_ancienne(self):
        vin = self.creer(valeur=15)
        self.reponses = [{"valeur": "inconnue"}]
        self.app.planificateur.lancer_valeurs()
        for _ in range(50):
            if self.app.planificateur.etat_valeurs["termine_le"]:
                break
            import time
            time.sleep(0.1)
        self.assertEqual(len(self.app.planificateur.etat_valeurs["erreurs"]), 1)
        self.assertEqual(self.appel("GET", f"api/vins/{vin['id']}")["valeur"], 15)


if __name__ == "__main__":
    unittest.main()
