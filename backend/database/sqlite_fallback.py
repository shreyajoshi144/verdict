"""
Dev-only SQLite fallback for backend/database/database.py.

This is NOT meant for production — it exists purely so `python start.py` can run
the whole app with zero setup when no MySQL server is configured or reachable.
start.py patches backend.database.database.execute_query/execute_many to point
here *before* any service module imports them, so the rest of the codebase
(product_service, wishlist_service, history_service, budget_service, auth_service)
runs completely unmodified against this instead.

Query translation is intentionally dumb and specific to the exact queries this
codebase issues (see backend/services/*.py) — it is not a general MySQL->SQLite
shim:
  - "%s" placeholders -> "?"
  - INTEGER PRIMARY KEY AUTOINCREMENT instead of AUTO_INCREMENT
  - a hand-written schema instead of parsing schema.sql (which uses MySQL-only
    syntax like CREATE DATABASE / CHARACTER SET / INSERT IGNORE)
"""
import re
import sqlite3
from pathlib import Path
from backend.utils.logger import get_logger

logger = get_logger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent.parent / "verdict_dev.db"

# Same bcrypt hash as schema.sql's demo user, so the demo login works identically
# whether you're on MySQL or this fallback.
_DEMO_PASSWORD_HASH = "$2b$12$1/8L94WfHpJn1JG6AugLweu2lMgaNpsCYbkhCJyciWyRn1OnPM3Z."

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    website TEXT NOT NULL,
    price REAL NOT NULL,
    original_price REAL,
    discount REAL DEFAULT 0,
    rating REAL DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    image_url TEXT,
    product_url TEXT NOT NULL,
    brand TEXT,
    category TEXT,
    search_query TEXT,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wishlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    website TEXT NOT NULL,
    price REAL NOT NULL,
    discount REAL DEFAULT 0,
    rating REAL DEFAULT 0,
    image_url TEXT,
    product_url TEXT NOT NULL,
    brand TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    query TEXT NOT NULL,
    filters TEXT,
    result_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS budget_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    budget REAL NOT NULL,
    category TEXT,
    description TEXT,
    ai_plan TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

INSERT OR IGNORE INTO users (id, name, email, password_hash)
VALUES (1, 'Demo User', 'demo@verdict.ai', '{demo_hash}');
""".format(demo_hash=_DEMO_PASSWORD_HASH)


def init_db():
    is_new = not DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()
    logger.info(f"{'Created' if is_new else 'Using existing'} SQLite dev database at {DB_PATH}")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _translate(query: str) -> str:
    return query.replace("%s", "?")


def execute_query(query: str, params: tuple = None, fetch: bool = True):
    conn = _connect()
    try:
        cur = conn.execute(_translate(query), params or ())
        if fetch:
            return [dict(row) for row in cur.fetchall()]
        conn.commit()
        return cur.lastrowid
    except Exception as e:
        conn.rollback()
        logger.error(f"[sqlite] Query error: {e} | Query: {query}")
        raise
    finally:
        conn.close()


def execute_many(query: str, params_list: list):
    conn = _connect()
    try:
        cur = conn.executemany(_translate(query), params_list)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        conn.rollback()
        logger.error(f"[sqlite] Batch query error: {e}")
        raise
    finally:
        conn.close()
