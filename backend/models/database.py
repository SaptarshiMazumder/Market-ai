import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'market_ai.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT UNIQUE NOT NULL,
            model_slug TEXT NOT NULL,
            trigger_word TEXT,
            training_id TEXT,
            training_status TEXT DEFAULT 'pending',
            version_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS batch_jobs (
            id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL,
            status TEXT DEFAULT 'processing',
            total_items INTEGER,
            completed_items INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_name) REFERENCES products(product_name)
        );

        CREATE TABLE IF NOT EXISTS batch_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_job_id TEXT NOT NULL,
            item_index INTEGER NOT NULL,
            template_url TEXT,
            status TEXT DEFAULT 'pending',
            output_path TEXT,
            error TEXT,
            FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(id)
        );

        CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            prompt TEXT NOT NULL,
            image_filename TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    print("Database initialized successfully.")
