import os
import psycopg2
import psycopg2.extras


def get_db():
    conn = psycopg2.connect(
        host=os.environ.get("PGHOST", "postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "training"),
        user=os.environ.get("PGUSER", "training"),
        password=os.environ.get("PGPASSWORD", "training"),
    )
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            prompt TEXT NOT NULL,
            image_filename TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("[DB] Templates table initialized.")
