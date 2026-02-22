import os
import uuid
from datetime import datetime, timezone

import psycopg2.extras
from models.database import get_db

TEMPLATE_IMAGES_FOLDER = 'template_images'


def _to_dict(r):
    return {
        "id": r["id"],
        "name": r["name"],
        "prompt": r["prompt"],
        "image_url": f"/api/template-images/{r['image_filename']}",
        "created_at": r["created_at"],
    }


def list_templates():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM templates ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [_to_dict(r) for r in rows]


def get_template(template_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM templates WHERE id = %s", (template_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return _to_dict(row) if row else None


def create_template(name, prompt_text, image_filename):
    template_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO templates (id, name, prompt, image_filename, created_at) VALUES (%s, %s, %s, %s, %s)",
        (template_id, name.strip(), prompt_text.strip(), image_filename, created_at),
    )
    conn.commit()
    cur.close()
    conn.close()

    print(f"[Template] Created: {name} (id={template_id})")

    return {
        "id": template_id,
        "name": name.strip(),
        "prompt": prompt_text.strip(),
        "image_url": f"/api/template-images/{image_filename}",
        "created_at": created_at,
    }


def delete_template(template_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT image_filename FROM templates WHERE id = %s", (template_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return False

    image_path = os.path.join(TEMPLATE_IMAGES_FOLDER, row["image_filename"])
    if os.path.exists(image_path):
        os.remove(image_path)

    cur.execute("DELETE FROM templates WHERE id = %s", (template_id,))
    conn.commit()
    cur.close()
    conn.close()

    print(f"[Template] Deleted: {template_id}")
    return True
