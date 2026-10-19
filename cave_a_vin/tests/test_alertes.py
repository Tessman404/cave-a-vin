"""Notifications de fin de garde : 2 rappels au plus par vin, à 15 jours d'écart."""
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from app import alertes, cave
from app.db import Database
from app.server import Application


class TestAlertes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "cave.db")
        self.app = Application(self.db, self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.db.close)
        annee = cave.annee_courante()
        self.urgent = cave.creer_vin(self.db, {"nom": "Vieux Médoc", "couleur": "rouge", "garde_debut": annee - 5,
                                               "garde_fin": annee, "quantite": 2})
        cave.creer_vin(self.db, {"nom": "Dépassé", "couleur": "rouge", "garde_debut": annee - 8, "garde_fin": annee - 1, "quantite": 1})
        cave.creer_vin(self.db, {"nom": "Jeune", "couleur": "rouge", "garde_debut": annee, "garde_fin": annee + 10, "quantite": 1})
        self.envois = []
        patch = mock.patch.object(alertes, "envoyer", lambda r, s, t, m: self.envois.append((s, t, m)))
        patch.start()
        self.addCleanup(patch.stop)

    def test_desactivees_par_defaut(self):
        self.assertEqual(alertes.verifier(self.app), 0)
        self.assertEqual(self.envois, [])

    def test_deux_rappels_a_quinze_jours(self):
        self.app.ecrire_reglage("notif_service", "notify.mobile_app_iphone")
        j0 = date(cave.annee_courante(), 3, 1)
        self.assertEqual(alertes.verifier(self.app, j0), 1)  # seul le vin « à boire vite » est signalé
        self.assertIn("Vieux Médoc", self.envois[0][2])
        self.assertNotIn("Dépassé", self.envois[0][2])
        self.assertEqual(alertes.verifier(self.app, j0 + timedelta(days=14)), 0)  # trop tôt
        self.assertEqual(alertes.verifier(self.app, j0 + timedelta(days=15)), 1)  # second rappel
        self.assertIn("dernier rappel", self.envois[1][2])
        self.assertEqual(alertes.verifier(self.app, j0 + timedelta(days=60)), 0)  # plus jamais
        self.assertEqual(len(self.envois), 2)

    def test_rappel_d_occasion_une_seule_fois(self):
        self.app.ecrire_reglage("notif_service", "notify.mobile_app_iphone")
        jour = date(cave.annee_courante() + 1, 3, 12)
        cave.modifier_vin(self.db, self.urgent["id"], {"note_perso": "Anniversaire de mariage", "note_date": jour.isoformat()})
        self.assertEqual(alertes.verifier_occasions(self.app, jour - timedelta(days=8)), 0)  # trop tôt
        self.assertEqual(alertes.verifier_occasions(self.app, jour - timedelta(days=7)), 1)
        self.assertIn("Anniversaire de mariage : dans 7 jours", self.envois[-1][1])
        self.assertEqual(alertes.verifier_occasions(self.app, jour - timedelta(days=2)), 0)  # déjà prévenu

    def test_vin_sorti_n_est_plus_rappele(self):
        self.app.ecrire_reglage("notif_service", "notify.mobile_app_iphone")
        cave.sortir_bouteilles(self.db, self.urgent["id"], {"quantite": 2, "raison": "bue"})
        self.assertEqual(alertes.verifier(self.app, date(cave.annee_courante(), 3, 1)), 0)


    def test_notifications_en_anglais(self):
        self.app.ecrire_reglage("notif_service", "notify.mobile_app_iphone")
        self.app.ecrire_reglage("langue", "en")
        self.assertEqual(alertes.verifier(self.app, date(cave.annee_courante(), 3, 1)), 1)
        self.assertIn("reaching the end of its window", self.envois[0][1])
        self.assertIn("Drink before the end of", self.envois[0][2])
        jour = date(cave.annee_courante() + 1, 3, 12)
        cave.modifier_vin(self.db, self.urgent["id"], {"note_perso": "Wedding anniversary", "note_date": jour.isoformat()})
        self.assertEqual(alertes.verifier_occasions(self.app, jour - timedelta(days=1)), 1)
        self.assertEqual(self.envois[-1][1], "📌 Wedding anniversary: tomorrow")
        self.assertIn("for March 12", self.envois[-1][2])

    def test_consignes_ia_dans_la_langue(self):
        from app import ia
        self.assertIn("en français", ia.langue_texte({}))
        self.assertIn("English", ia.langue_texte({"langue": "en"}))
        self.assertNotIn("{langue}", ia.INSTRUCTIONS.replace("{langue}", ia.langue_texte({})))


if __name__ == "__main__":
    unittest.main()
