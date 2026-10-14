"""Fixtures : lance l'application Cave à vin dans un processus séparé."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def _port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def cave_url(socket_enabled):
    with tempfile.TemporaryDirectory() as dossier:
        port = _port_libre()
        env = {**os.environ, "CAVE_DATA_DIR": dossier, "CAVE_PORT": str(port)}
        proc = subprocess.Popen([sys.executable, "-m", "app"], cwd=RACINE / "cave_a_vin", env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        url = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                urllib.request.urlopen(url + "/api/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)

        def appel(methode, chemin, corps=None):
            req = urllib.request.Request(f"{url}/api/{chemin}", method=methode,
                                         data=json.dumps(corps).encode() if corps is not None else None,
                                         headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req).read())

        cave = appel("POST", "caves", {"nom": "Sous-sol", "rangees": 4, "colonnes": 5})
        appel("POST", "vins", {"nom": "Château Test", "millesime": 2010, "region": "Bordeaux", "couleur": "rouge",
                               "garde_debut": 2015, "garde_fin": 2026, "prix_achat": 30, "quantite": 3,
                               "cave_id": cave["id"]})
        appel("POST", "vins", {"nom": "Chablis", "couleur": "blanc", "appellation": "Chablis",
                               "garde_debut": 2024, "garde_fin": 2030, "prix_achat": 20, "quantite": 2})
        appel("POST", "envies", {"nom": "Meursault"})
        yield url
        proc.terminate()
        proc.wait(5)
