"""Estimation de la garde par l'IA (et de la valeur des vins qui n'en ont pas) : à la demande, à l'ajout d'un vin,
et automatiquement chaque mois."""

import logging
import threading
import time
from datetime import datetime, timedelta

from . import cave, ia
from .db import maintenant

log = logging.getLogger("cave_a_vin")

PERIODE = timedelta(days=30)


def annee_achat(db, vin_id):
    """Année de la première entrée en cave (référence pour un vin sans millésime)."""
    premiere = db.scalar("SELECT MIN(date) FROM mouvements WHERE vin_id = ? AND type = 'entree'", (vin_id,))
    vin = db.one("SELECT created_at FROM vins WHERE id = ?", (vin_id,))
    return int((premiere or (vin or {}).get("created_at") or maintenant())[:4])


def estimer_vin(db, reglages, vin_id, appliquer=None):
    """Interroge l'IA pour un vin et enregistre sa suggestion.

    La suggestion remplace la garde du vin, sauf si celle-ci a été saisie à la main (elle reste alors
    proposée sur la fiche). `appliquer="forcer"` remplace même une garde saisie à la main (demande
    explicite de l'utilisateur) ; `appliquer=False` enregistre seulement la suggestion.
    """
    vin = cave.lire_vin(db, vin_id, details=False)
    estimation = ia.estimer_garde(reglages, vin, annee_achat(db, vin_id), cave.annee_courante())
    if appliquer is None:
        appliquer = vin.get("garde_source") != "manuel"
    suggestion = {"garde_ia_debut": estimation["garde_debut"], "garde_ia_apogee": estimation["garde_apogee"],
                  "garde_ia_fin": estimation["garde_fin"], "garde_ia_note": estimation["note"],
                  "garde_ia_date": maintenant()}
    garde = {**{c: estimation[c] for c in cave.CHAMPS_GARDE}, "garde_source": "ia"}
    with db.transaction() as conn:
        conn.execute(f"UPDATE vins SET {', '.join(f'{k} = ?' for k in suggestion)} WHERE id = ?",
                     [*suggestion.values(), vin_id])
        if appliquer:
            # « garde_source » est relue au moment d'écrire : une saisie à la main faite pendant que l'IA
            # réfléchissait n'est jamais écrasée (sauf demande explicite).
            condition = "" if appliquer == "forcer" else " AND garde_source != 'manuel'"
            conn.execute(f"UPDATE vins SET {', '.join(f'{k} = ?' for k in garde)} WHERE id = ?{condition}",
                         [*garde.values(), vin_id])
    return cave.lire_vin(db, vin_id)


def estimer_valeur_vin(db, reglages, vin_id):
    """Interroge l'IA pour la valeur d'un vin, dans la devise choisie, et l'enregistre."""
    vin = cave.lire_vin(db, vin_id, details=False)
    valeur = ia.estimer_valeur(reglages, vin, annee_achat(db, vin_id))
    with db.transaction() as conn:
        conn.execute("UPDATE vins SET valeur = ? WHERE id = ?", (valeur, vin_id))
    return valeur


def completer_valeur(db, reglages, vin_id):
    """Vin sans valeur estimée : l'IA la remplit (une valeur existante, saisie ou non, n'est jamais remplacée ici)."""
    if db.scalar("SELECT valeur FROM vins WHERE id = ?", (vin_id,)):
        return None
    try:
        return estimer_valeur_vin(db, reglages, vin_id)
    except (ia.IAErreur, cave.ErreurAPI) as e:
        log.warning("Valeur IA du vin %s : %s", vin_id, e)
        return None


class Planificateur:
    """Tâche de fond : réestime chaque mois la garde des vins en cave."""

    def __init__(self, app, intervalle_verification=3600, pause_entre_vins=2.0):
        self.app = app
        self.intervalle = intervalle_verification
        self.pause = pause_entre_vins
        self._arret = threading.Event()
        self._verrou = threading.Lock()
        self._verrou_valeurs = threading.Lock()
        self._en_cours = None
        self.etat = {"en_cours": False, "fait": 0, "total": 0, "erreurs": [], "termine_le": None}
        self.etat_valeurs = {"en_cours": False, "fait": 0, "total": 0, "erreurs": [], "termine_le": None}

    # ---------------------------------------------------------------- planification

    def demarrer(self):
        threading.Thread(target=self._boucle, name="garde-ia", daemon=True).start()

    def arreter(self):
        self._arret.set()

    def _boucle(self):
        self._arret.wait(30)  # laisse l'application démarrer
        while not self._arret.is_set():
            try:
                if self.a_faire():
                    self.tout_estimer()
            except Exception:  # noqa: BLE001 - la tâche de fond ne doit jamais s'arrêter
                log.exception("Estimation mensuelle de la garde")
            self._arret.wait(self.intervalle)

    def a_faire(self):
        reglages = self.app.reglages()
        if reglages.get("ia_garde_auto", "1") != "1" or not ia.etat(reglages, image=False)["possible"]:
            return False
        derniere = reglages.get("ia_garde_derniere")
        if not derniere:
            return True
        try:
            return datetime.now() - datetime.fromisoformat(derniere) >= PERIODE
        except ValueError:
            return True

    # ---------------------------------------------------------------- exécution

    def lancer(self):
        """Lance une estimation complète en tâche de fond (sans attendre la fin)."""
        if self.etat["en_cours"]:
            return False
        threading.Thread(target=self.tout_estimer, name="garde-ia-manuel", daemon=True).start()
        return True

    def tout_estimer(self):
        if not self._verrou.acquire(blocking=False):
            return
        try:
            db = self.app.db
            ids = [r["id"] for r in db.all(
                """SELECT v.id FROM vins v JOIN bouteilles b ON b.vin_id = v.id
                   GROUP BY v.id ORDER BY LOWER(v.nom)""")]
            self.etat = {"en_cours": True, "fait": 0, "total": len(ids), "erreurs": [], "termine_le": None}
            log.info("Estimation de la garde par l'IA : %d vin(s)", len(ids))
            for vin_id in ids:
                if self._arret.is_set():
                    break
                try:
                    estimer_vin(db, self.app.reglages(), vin_id)
                    completer_valeur(db, self.app.reglages(), vin_id)
                except (ia.IAErreur, cave.ErreurAPI) as e:
                    nom = (db.one("SELECT nom FROM vins WHERE id = ?", (vin_id,)) or {}).get("nom", vin_id)
                    self.etat["erreurs"].append(f"{nom} : {e}")
                    log.warning("Garde IA de « %s » : %s", nom, e)
                self.etat["fait"] += 1
                time.sleep(self.pause)
            if ids and len(self.etat["erreurs"]) == len(ids):
                # tout a échoué (IA indisponible ?) : on réessaiera demain plutôt que dans un mois
                self.app.ecrire_reglage("ia_garde_derniere",
                                        (datetime.now() - PERIODE + timedelta(days=1)).isoformat(timespec="seconds"))
            else:
                self.app.ecrire_reglage("ia_garde_derniere", maintenant())
            self.etat.update(en_cours=False, termine_le=maintenant())
            log.info("Estimation de la garde terminée (%d erreur(s))", len(self.etat["erreurs"]))
        finally:
            self.etat["en_cours"] = False
            self._verrou.release()

    def lancer_valeurs(self):
        """Réestime la valeur de tous les vins dans la devise choisie, en tâche de fond (après un changement de devise)."""
        if self.etat_valeurs["en_cours"]:
            return False
        ids = [r["id"] for r in self.app.db.all("SELECT id FROM vins ORDER BY LOWER(nom)")]
        self.etat_valeurs = {"en_cours": True, "fait": 0, "total": len(ids), "erreurs": [], "termine_le": None}
        threading.Thread(target=self.toutes_les_valeurs, args=(ids,), name="valeurs-ia", daemon=True).start()
        return True

    def toutes_les_valeurs(self, ids):
        if not self._verrou_valeurs.acquire(blocking=False):
            return
        try:
            db = self.app.db
            log.info("Estimation de la valeur par l'IA : %d vin(s)", len(ids))
            for vin_id in ids:
                if self._arret.is_set():
                    break
                try:
                    estimer_valeur_vin(db, self.app.reglages(), vin_id)
                except (ia.IAErreur, cave.ErreurAPI) as e:
                    nom = (db.one("SELECT nom FROM vins WHERE id = ?", (vin_id,)) or {}).get("nom", vin_id)
                    self.etat_valeurs["erreurs"].append(f"{nom} : {e}")
                    log.warning("Valeur IA de « %s » : %s", nom, e)
                self.etat_valeurs["fait"] += 1
                time.sleep(self.pause)
            log.info("Estimation de la valeur terminée (%d erreur(s))", len(self.etat_valeurs["erreurs"]))
        finally:
            self.etat_valeurs.update(en_cours=False, termine_le=maintenant())
            self._verrou_valeurs.release()

    def estimer_en_arriere_plan(self, vin_id):
        """Après l'ajout d'un vin : estimation par l'IA sans faire attendre l'utilisateur."""
        reglages = self.app.reglages()
        if reglages.get("ia_garde_auto", "1") != "1" or not ia.etat(reglages, image=False)["possible"]:
            return

        def tache():
            try:
                estimer_vin(self.app.db, self.app.reglages(), vin_id)
            except (ia.IAErreur, cave.ErreurAPI) as e:
                log.warning("Garde IA du vin %s : %s", vin_id, e)
            completer_valeur(self.app.db, self.app.reglages(), vin_id)  # vin saisi à la main, sans prix

        threading.Thread(target=tache, name=f"garde-ia-{vin_id}", daemon=True).start()
