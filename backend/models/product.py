from models.database import get_db


def save_product(product_name, model_slug, trigger_word=None):
    db = get_db()
    db.execute(
        """INSERT OR REPLACE INTO products (product_name, model_slug, trigger_word, updated_at)
           VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
        (product_name, model_slug, trigger_word)
    )
    db.commit()
    db.close()


def update_training(product_name, training_id, trigger_word):
    db = get_db()
    db.execute(
        """UPDATE products SET training_id = ?, trigger_word = ?, training_status = 'training',
           updated_at = CURRENT_TIMESTAMP WHERE product_name = ?""",
        (training_id, trigger_word, product_name)
    )
    db.commit()
    db.close()


def update_training_status(training_id, status, version_id=None):
    db = get_db()
    if version_id:
        db.execute(
            """UPDATE products SET training_status = ?, version_id = ?,
               updated_at = CURRENT_TIMESTAMP WHERE training_id = ?""",
            (status, version_id, training_id)
        )
    else:
        db.execute(
            """UPDATE products SET training_status = ?,
               updated_at = CURRENT_TIMESTAMP WHERE training_id = ?""",
            (status, training_id)
        )
    db.commit()
    db.close()


def get_product(product_name):
    db = get_db()
    row = db.execute(
        "SELECT * FROM products WHERE product_name = ?", (product_name,)
    ).fetchone()
    db.close()
    return dict(row) if row else None


def get_product_by_training_id(training_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM products WHERE training_id = ?", (training_id,)
    ).fetchone()
    db.close()
    return dict(row) if row else None


def list_products():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM products ORDER BY updated_at DESC"
    ).fetchall()
    db.close()
    return [dict(row) for row in rows]


def get_trained_products():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM products WHERE training_status = 'succeeded' AND version_id IS NOT NULL ORDER BY updated_at DESC"
    ).fetchall()
    db.close()
    return [dict(row) for row in rows]


def upsert_trained_product(product_name, model_slug, trigger_word, version_id, training_id=None):
    db = get_db()
    db.execute(
        """INSERT INTO products
           (product_name, model_slug, trigger_word, training_id, training_status, version_id, updated_at)
           VALUES (?, ?, ?, ?, 'succeeded', ?, CURRENT_TIMESTAMP)
           ON CONFLICT(product_name) DO UPDATE SET
             model_slug = excluded.model_slug,
             trigger_word = excluded.trigger_word,
             training_id = COALESCE(excluded.training_id, products.training_id),
             training_status = 'succeeded',
             version_id = excluded.version_id,
             updated_at = CURRENT_TIMESTAMP""",
        (product_name, model_slug, trigger_word, training_id, version_id)
    )
    db.commit()
    db.close()


# Batch job helpers

def create_batch_job(batch_job_id, product_name, total_items):
    db = get_db()
    db.execute(
        "INSERT INTO batch_jobs (id, product_name, total_items) VALUES (?, ?, ?)",
        (batch_job_id, product_name, total_items)
    )
    for i in range(total_items):
        db.execute(
            "INSERT INTO batch_items (batch_job_id, item_index, status) VALUES (?, ?, 'pending')",
            (batch_job_id, i)
        )
    db.commit()
    db.close()


def update_batch_item(batch_job_id, item_index, status, output_path=None, error=None, template_url=None):
    db = get_db()
    if template_url:
        db.execute(
            "UPDATE batch_items SET template_url = ?, status = ?, output_path = ?, error = ? WHERE batch_job_id = ? AND item_index = ?",
            (template_url, status, output_path, error, batch_job_id, item_index)
        )
    else:
        db.execute(
            "UPDATE batch_items SET status = ?, output_path = ?, error = ? WHERE batch_job_id = ? AND item_index = ?",
            (status, output_path, error, batch_job_id, item_index)
        )

    # Update completed count
    completed = db.execute(
        "SELECT COUNT(*) FROM batch_items WHERE batch_job_id = ? AND status IN ('completed', 'failed')",
        (batch_job_id,)
    ).fetchone()[0]
    total = db.execute(
        "SELECT total_items FROM batch_jobs WHERE id = ?", (batch_job_id,)
    ).fetchone()[0]

    batch_status = 'completed' if completed >= total else 'processing'
    db.execute(
        "UPDATE batch_jobs SET completed_items = ?, status = ? WHERE id = ?",
        (completed, batch_status, batch_job_id)
    )
    db.commit()
    db.close()


def get_batch_status(batch_job_id):
    db = get_db()
    job = db.execute("SELECT * FROM batch_jobs WHERE id = ?", (batch_job_id,)).fetchone()
    if not job:
        db.close()
        return None
    items = db.execute(
        "SELECT * FROM batch_items WHERE batch_job_id = ? ORDER BY item_index",
        (batch_job_id,)
    ).fetchall()
    db.close()
    return {
        "job": dict(job),
        "items": [dict(item) for item in items]
    }
