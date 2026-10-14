"""Base de données SQLite de la cave."""

import sqlite3
import threading
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS caves (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT    NOT NULL,
    rangees     INTEGER NOT NULL DEFAULT 0,
    colonnes    INTEGER NOT NULL DEFAULT 0,
    description TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS vins (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nom           TEXT    NOT NULL,
    domaine       TEXT    NOT NULL DEFAULT '',
    appellation   TEXT    NOT NULL DEFAULT '',
    region        TEXT    NOT NULL DEFAULT '',
    pays          TEXT    NOT NULL DEFAULT 'France',
    couleur       TEXT    NOT NULL DEFAULT 'rouge',
    millesime     INTEGER,
    cepages       TEXT    NOT NULL DEFAULT '',
    format        TEXT    NOT NULL DEFAULT '75 cl',
    degre         REAL,
    prix_achat    REAL,
    valeur        REAL,
    fournisseur   TEXT    NOT NULL DEFAULT '',
    garde_debut   INTEGER,
    garde_apogee  INTEGER,
    garde_fin     INTEGER,
    accords       TEXT    NOT NULL DEFAULT '',
    notes         TEXT    NOT NULL DEFAULT '',
    photo         TEXT,
    favori        INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS bouteilles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vin_id      INTEGER NOT NULL REFERENCES vins(id) ON DELETE CASCADE,
    cave_id     INTEGER REFERENCES caves(id) ON DELETE SET NULL,
    rangee      INTEGER,
    colonne     INTEGER,
    date_entree TEXT    NOT NULL,
    UNIQUE (cave_id, rangee, colonne)
);
CREATE INDEX IF NOT EXISTS idx_bouteilles_vin ON bouteilles(vin_id);

CREATE TABLE IF NOT EXISTS mouvements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    vin_id      INTEGER REFERENCES vins(id) ON DELETE SET NULL,
    vin_nom     TEXT    NOT NULL,
    millesime   INTEGER,
    type        TEXT    NOT NULL CHECK (type IN ('entree', 'sortie')),
    quantite    INTEGER NOT NULL,
    raison      TEXT    NOT NULL DEFAULT '',
    note        REAL,
    commentaire TEXT    NOT NULL DEFAULT '',
    date        TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mouvements_vin ON mouvements(vin_id);

CREATE TABLE IF NOT EXISTS envies (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    nom        TEXT    NOT NULL,
    details    TEXT    NOT NULL DEFAULT '',
    fait       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS reglages (
    cle    TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);
"""


def maintenant():
    return datetime.now().isoformat(timespec="seconds")


class Database:
    """Connexion unique protégée par un verrou : largement suffisant pour une cave."""

    def __init__(self, chemin):
        self.conn = sqlite3.connect(chemin, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.executescript(SCHEMA)
        self._migrer()
        self.conn.commit()
        self.lock = threading.RLock()

    def _migrer(self):
        """Ajoute les colonnes apparues après la première version."""
        colonnes = {r[1] for r in self.conn.execute("PRAGMA table_info(vins)")}
        for nom, definition in (("code_barre", "TEXT NOT NULL DEFAULT ''"), ("photo_originale", "TEXT")):
            if nom not in colonnes:
                self.conn.execute(f"ALTER TABLE vins ADD COLUMN {nom} {definition}")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_vins_code_barre ON vins(code_barre)")

    def all(self, sql, params=()):
        with self.lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def one(self, sql, params=()):
        with self.lock:
            row = self.conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def scalar(self, sql, params=()):
        with self.lock:
            row = self.conn.execute(sql, params).fetchone()
            return row[0] if row else None

    def transaction(self):
        return _Transaction(self)

    def close(self):
        with self.lock:
            self.conn.close()


class _Transaction:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        self.db.lock.acquire()
        return self.db.conn

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.db.conn.commit()
            else:
                self.db.conn.rollback()
        finally:
            self.db.lock.release()
        return False
