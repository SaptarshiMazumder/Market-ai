import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'training.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trained_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            trigger_word TEXT NOT NULL,
            model_url TEXT,
            runpod_job_id TEXT,
            status TEXT DEFAULT 'training',
            created_at TEXT NOT NULL
        );
    """)

    # No seed data — models are created via training jobs

    conn.commit()
    conn.close()
    print("[DB] Training database initialized.")
