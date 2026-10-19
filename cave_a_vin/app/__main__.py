"""Point d'entrée : python -m app"""

import json
import logging
import os
import socket
import threading
import urllib.request
from pathlib import Path

from . import __version__, photo
from .db import Database
from .server import Application, creer_serveur


def options_addon():
    """Options saisies dans l'onglet « Configuration » du module complémentaire Home Assistant."""
    chemin = Path("/data/options.json")
    if chemin.exists():
        try:
            return json.loads(chemin.read_text())
        except ValueError:
            pass
    return {}


def annoncer_a_home_assistant(port, api_key):
    """Découverte automatique : Home Assistant propose alors d'ajouter l'intégration Tessvine."""
    jeton = os.environ.get("SUPERVISOR_TOKEN")
    if not jeton:
        return
    corps = {"service": "cave_a_vin", "config": {"host": socket.gethostname(), "port": port, "api_key": api_key}}
    req = urllib.request.Request("http://supervisor/discovery", data=json.dumps(corps).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {jeton}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10):
            logging.info("Cave annoncée à Home Assistant (%s:%s)", corps["config"]["host"], port)
    except OSError as e:
        logging.warning("Découverte automatique impossible (%s) : ajoutez l'intégration à la main", e)


def main():
    opts = options_addon()
    niveau = (opts.get("log_level") or os.environ.get("LOG_LEVEL") or "info").upper()
    logging.basicConfig(level=getattr(logging, niveau, logging.INFO),
                        format="%(asctime)s %(levelname)s %(message)s")
    dossier = Path(os.environ.get("CAVE_DATA_DIR") or ("/data" if Path("/data/options.json").exists() else "data"))
    dossier.mkdir(parents=True, exist_ok=True)
    port = int(os.environ.get("CAVE_PORT") or 8099)
    api_key = opts.get("api_key") or os.environ.get("CAVE_API_KEY") or ""

    db = Database(dossier / "cave.db")
    application = Application(db, dossier, api_key)
    serveur = creer_serveur(application, port=port)
    application.planificateur.demarrer()  # estimation mensuelle de la garde par l'IA
    application.surveillance.demarrer()  # notifications de fin de garde
    logging.info("Tessvine %s démarrée sur le port %s (données : %s)%s", __version__, port, dossier.resolve(),
                 " — clé d'API activée" if api_key else "")
    if photo.RAISON_SANS_DETOURAGE:
        logging.warning("Détourage des photos désactivé : %s. La cave fonctionne normalement, les photos sont gardées "
                        "telles quelles.", photo.RAISON_SANS_DETOURAGE)
    threading.Thread(target=annoncer_a_home_assistant, args=(port, api_key), daemon=True).start()
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        application.planificateur.arreter()
        serveur.server_close()
        db.close()


if __name__ == "__main__":
    main()
