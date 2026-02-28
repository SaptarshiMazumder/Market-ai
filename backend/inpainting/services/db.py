import os
import json
import psycopg2
import psycopg2.extras


def _get_conn():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "postgres"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "training"),
        user=os.environ.get("PGUSER", "training"),
        password=os.environ.get("PGPASSWORD", "training"),
    )


def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inpainting_jobs (
            id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'pending',
            scene_url TEXT NOT NULL,
            reference_url TEXT NOT NULL,
            prompt TEXT,
            params JSONB,
            runpod_job_id TEXT,
            result JSONB,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


def create_job(job_id, scene_url, reference_url, prompt, params, created_at):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO inpainting_jobs (id, status, scene_url, reference_url, prompt, params, created_at)
           VALUES (%s, 'pending', %s, %s, %s, %s, %s)""",
        (job_id, scene_url, reference_url, prompt, json.dumps(params), created_at),
    )
    conn.commit()
    cur.close()
    conn.close()


def update_job(job_id, status, runpod_job_id=None, result=None, error=None, updated_at=None):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """UPDATE inpainting_jobs
           SET status = %s, runpod_job_id = COALESCE(%s, runpod_job_id),
               result = COALESCE(%s, result), error = COALESCE(%s, error),
               updated_at = COALESCE(%s, updated_at)
           WHERE id = %s""",
        (status, runpod_job_id, json.dumps(result) if result else None,
         error, updated_at, job_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_job(job_id):
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM inpainting_jobs WHERE id = %s", (job_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    result = dict(row)
    if isinstance(result.get("params"), str):
        result["params"] = json.loads(result["params"])
    if isinstance(result.get("result"), str):
        result["result"] = json.loads(result["result"])
    return result
