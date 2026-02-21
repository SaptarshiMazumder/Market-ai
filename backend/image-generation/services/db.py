import os
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


def get_model_url(model_id: int) -> str | None:
    """Look up the R2 model_url for a trained model by its database ID."""
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT model_url FROM trained_models WHERE id = %s AND status = 'succeeded'",
            (model_id,),
        )
        row = cur.fetchone()
        cur.close()
        return row["model_url"] if row else None
    finally:
        conn.close()
