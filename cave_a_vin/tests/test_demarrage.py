"""La cave doit démarrer même quand les bibliothèques de détourage ne peuvent pas se charger
(par exemple NumPy 2 sur un processeur sans SSE4.2, fréquent dans une machine virtuelle Proxmox)."""
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def lancer(code, faux_numpy=False):
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ)
        chemin = [str(RACINE)]
        if faux_numpy:
            # un « numpy » qui refuse de se charger, comme sur un processeur trop ancien
            (Path(tmp) / "numpy").mkdir()
            (Path(tmp) / "numpy" / "__init__.py").write_text(
                "raise RuntimeError('NumPy was built with baseline optimizations: (X86_V2) but your machine "
                "doesn\\'t support: (X86_V2).')\n")
            chemin.insert(0, tmp)
        env["PYTHONPATH"] = os.pathsep.join(chemin)
        return subprocess.run([sys.executable, "-c", textwrap.dedent(code)], env=env, capture_output=True, text=True, timeout=60)


class TestDemarrage(unittest.TestCase):
    def test_numpy_incompatible_ne_bloque_pas(self):
        r = lancer("""
            import tempfile
            from pathlib import Path
            from app import photo
            from app.db import Database
            from app.server import Application
            assert not photo.detourage_disponible()
            assert "inutilisables" in photo.RAISON_SANS_DETOURAGE, photo.RAISON_SANS_DETOURAGE
            d = tempfile.mkdtemp()
            Application(Database(Path(d) / "cave.db"), d)
            print("OK")
        """, faux_numpy=True)
        self.assertIn("OK", r.stdout, r.stderr)

    def test_processeur_sans_sse42_detecte(self):
        r = lancer("""
            import builtins, io, platform
            platform.machine = lambda: "x86_64"
            vrai_open = builtins.open
            def faux_open(f, *a, **k):
                if str(f) == "/proc/cpuinfo":
                    return io.StringIO("flags\\t\\t: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr sse sse2 pni\\n")
                return vrai_open(f, *a, **k)
            builtins.open = faux_open
            from app import photo
            builtins.open = vrai_open
            assert not photo.detourage_disponible()
            assert "SSE4.2" in photo.RAISON_SANS_DETOURAGE
            print("OK")
        """)
        self.assertIn("OK", r.stdout, r.stderr)


if __name__ == "__main__":
    unittest.main()
