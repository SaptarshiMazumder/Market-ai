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
            replicate_training_id TEXT,
            status TEXT DEFAULT 'training',
            created_at TEXT NOT NULL
        );
    """)

    # Seed existing model if table is empty
    existing = conn.execute("SELECT COUNT(*) FROM trained_models").fetchone()[0]
    if existing == 0:
        conn.execute(
            "INSERT INTO trained_models (name, trigger_word, model_url, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                "myProd",
                "MY_PROD",
                "https://storage.googleapis.com/products-market-ai/myProd.safetensors",
                "succeeded",
                datetime.now(timezone.utc).isoformat(),
            )
        )

    conn.commit()
    conn.close()
    print("[DB] Training database initialized.")
