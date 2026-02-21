from datetime import datetime, timezone
import psycopg2.extras
from models.database import get_db
from services.r2 import lora_exists


def _reconcile_pending(conn):
    """For any model still in 'training' status, check R2. If the LoRA exists, mark it succeeded."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, name, runpod_job_id FROM trained_models WHERE status = 'training'")
    pending = cur.fetchall()
    cur.close()

    for model in pending:
        key = lora_exists(model["name"])
        if key:
            cur2 = conn.cursor()
            cur2.execute(
                "UPDATE trained_models SET model_url = %s, status = 'succeeded' WHERE id = %s",
                (key, model["id"])
            )
            cur2.close()
            print(f"[Reconcile] {model['name']} found in R2 → marked succeeded")

    conn.commit()


def list_models():
    conn = get_db()
    try:
        _reconcile_pending(conn)
    except Exception as e:
        print(f"[Reconcile] skipped: {e}")
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM trained_models ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [_to_dict(r) for r in rows]


def create_model(name, trigger_word, job_id=None):
    """Insert a new training record (status=training, no model_url yet)."""
    created_at = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO trained_models (name, trigger_word, runpod_job_id, status, created_at)
           VALUES (%s, %s, %s, 'training', %s) RETURNING id""",
        (name, trigger_word, job_id, created_at)
    )
    row_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return row_id


def set_model_url(job_id, model_url):
    """Mark a training as succeeded and store its R2 model path."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE trained_models SET model_url = %s, status = 'succeeded' WHERE runpod_job_id = %s",
        (model_url, job_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def set_model_failed(job_id):
    """Mark a training as failed."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE trained_models SET status = 'failed' WHERE runpod_job_id = %s",
        (job_id,)
    )
    conn.commit()
    cur.close()
    conn.close()


def get_model_by_job_id(job_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM trained_models WHERE runpod_job_id = %s",
        (job_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return _to_dict(row) if row else None


def _to_dict(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "trigger_word": row["trigger_word"],
        "model_string": row["model_url"],   # frontend expects model_string
        "destination": row["name"],
        "status": row["status"],
        "runpod_job_id": row["runpod_job_id"],
        "created_at": row["created_at"],
    }
