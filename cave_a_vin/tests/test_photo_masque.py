"""Détourage : un objet posé à côté de la bouteille (fruit, verre…) ne doit pas rester sur la photo."""
import unittest

from app import photo


@unittest.skipUnless(photo.Image is not None and photo.np is not None, "Pillow et numpy nécessaires")
class TestGarderLaBouteille(unittest.TestCase):
    def masque(self, *formes):
        from PIL import Image, ImageDraw
        m = Image.new("L", (1200, 1600), 0)
        d = ImageDraw.Draw(m)
        for f, boite, v in formes:
            getattr(d, f)(boite, fill=v)
        return m

    def test_objet_a_cote_retire(self):
        m = self.masque(("rectangle", (400, 200, 600, 1500), 255), ("ellipse", (800, 700, 950, 900), 230),
                        ("rectangle", (480, 120, 520, 190), 200))
        r = photo.garder_la_bouteille(m)
        self.assertEqual(r.crop((800, 700, 950, 900)).getextrema(), (0, 0))  # l'objet jaune a disparu
        self.assertEqual(r.getpixel((500, 800)), 255)  # la bouteille est intacte
        self.assertEqual(r.getpixel((500, 150)), 200)  # la capsule, dans l'axe, est gardée

    def test_bouteille_seule_inchangee(self):
        m = self.masque(("rectangle", (300, 100, 500, 1100), 255))
        self.assertIs(photo.garder_la_bouteille(m), m)


if __name__ == "__main__":
    unittest.main()
