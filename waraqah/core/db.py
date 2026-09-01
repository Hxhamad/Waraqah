"""SQLite database initialization and connection."""
import os
import sqlite3
from contextlib import contextmanager
from waraqah.core.config import DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS symbols (
    code TEXT PRIMARY KEY,
    name_ar TEXT,
    name_en TEXT,
    sector TEXT
);

CREATE TABLE IF NOT EXISTS snapshots (
    code TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS annual_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    year INTEGER NOT NULL,
    close REAL,
    ret REAL,
    vol REAL,
    maxdd REAL,
    divs REAL,
    div_yield REAL,
    momentum REAL,
    eps REAL,
    UNIQUE(symbol, year)
);

CREATE TABLE IF NOT EXISTS statements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    year INTEGER NOT NULL,
    revenue REAL,
    net_income REAL,
    eps REAL,
    roe REAL,
    de REAL,
    payout REAL,
    UNIQUE(symbol, year)
);

CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    added_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL CHECK(direction IN ('above', 'below')),
    target REAL NOT NULL,
    triggered INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS macro_cache (
    symbol TEXT PRIMARY KEY,
    price REAL,
    change_1d REAL,
    updated_at TEXT NOT NULL
);
"""


def get_connection(db_path: str = None) -> sqlite3.Connection:
    # Resolve at call time so tests (and deploys) can repoint the DB via env
    # without re-importing modules.
    path = db_path or os.environ.get("DATABASE_PATH") or DATABASE_PATH
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db(db_path: str = None):
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: str = None):
    with get_db(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
