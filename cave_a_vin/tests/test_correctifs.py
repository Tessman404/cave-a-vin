"""Correctifs signalés sur GitHub : schéma de réponse de l'IA (#3), tâche IA jamais utilisée (#10),
healthcheck avec clé d'API (#10), accords mets-vins par mots entiers (#10)."""

import json
import unittest
from unittest import mock

from app import cave, ia


class TestSchemaIA(unittest.TestCase):
    def test_pas_de_bornes_min_max(self):
        # l'API Anthropic refuse minimum/maximum sur les nombres du schéma de réponse
        for structure in (ia.STRUCTURE, ia.STRUCTURE_GARDE, ia.structure_etiquette("EUR")):
            texte = json.dumps(structure)
            self.assertNotIn('"min"', texte)
            self.assertNotIn('"max"', texte)

    def test_valeurs_toujours_verifiees(self):
        propre = ia._nettoyer({"nom": "X", "millesime": 1500, "degre": 13.5, "valeur": 5_000_000})
        self.assertNotIn("millesime", propre)
        self.assertNotIn("valeur", propre)
        self.assertEqual(propre["degre"], 13.5)


class TestTacheIA(unittest.TestCase):
    def test_tache_jamais_utilisee(self):
        entites = [{"entity_id": "ai_task.google", "etat": "unknown"}]
        with mock.patch.object(ia, "entites", return_value=entites):
            self.assertEqual(ia.entite_a_utiliser({}), "ai_task.google")
        with mock.patch.object(ia, "entites", return_value=[{"entity_id": "ai_task.x", "etat": "unavailable"}]):
            self.assertIsNone(ia.entite_a_utiliser({}))


class TestAccords(unittest.TestCase):
    def note(self, plat, accords):
        return cave._accord(cave.PLATS[plat], {"couleur": "autre", "accords": accords})[0]

    def test_mots_entiers(self):
        self.assertEqual(self.note("dessert", "fruits de mer, huîtres"), 0)
        self.assertEqual(self.note("poisson", "barbecue, grillades"), 0)
        self.assertEqual(self.note("boeuf", "poulet rôti"), 0)
        self.assertGreater(self.note("volaille", "poulet rôti"), 0)
        self.assertGreater(self.note("fruits_de_mer", "fruits de mer"), 0)
        self.assertGreater(self.note("dessert", "tarte aux pommes"), 0)
        self.assertGreater(self.note("fromage", "Agneau, fromages affinés".lower()), 0)


if __name__ == "__main__":
    unittest.main()
