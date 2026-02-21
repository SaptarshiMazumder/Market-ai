from datetime import datetime, timezone
from models.database import get_db


def list_models():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM trained_models ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [_to_dict(r) for r in rows]


def create_model(name, trigger_word, replicate_training_id=None):
    """Insert a new training record (status=training, no model_url yet)."""
    created_at = datetime.now(timezone.utc).isoformat()
    conn = get_db()
    cursor = conn.execute(
        """INSERT INTO trained_models (name, trigger_word, replicate_training_id, status, created_at)
           VALUES (?, ?, ?, 'training', ?)""",
        (name, trigger_word, replicate_training_id, created_at)
    )
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def set_model_url(replicate_training_id, model_url):
    """Mark a training as succeeded and store its GCS model URL."""
    conn = get_db()
    conn.execute(
        "UPDATE trained_models SET model_url = ?, status = 'succeeded' WHERE replicate_training_id = ?",
        (model_url, replicate_training_id)
    )
    conn.commit()
    conn.close()


def get_model_by_training_id(replicate_training_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM trained_models WHERE replicate_training_id = ?",
        (replicate_training_id,)
    ).fetchone()
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
        "created_at": row["created_at"],
    }
