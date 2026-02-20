import os
import uuid
from datetime import datetime, timezone

from models.database import get_db

TEMPLATE_IMAGES_FOLDER = 'template_images'


def list_templates():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM templates ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    templates = []
    for r in rows:
        templates.append({
            "id": r["id"],
            "name": r["name"],
            "prompt": r["prompt"],
            "image_url": f"/api/template-images/{r['image_filename']}",
            "created_at": r["created_at"],
        })
    return templates


def create_template(name, prompt_text, image_filename):
    template_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    conn = get_db()
    conn.execute(
        "INSERT INTO templates (id, name, prompt, image_filename, created_at) VALUES (?, ?, ?, ?, ?)",
        (template_id, name.strip(), prompt_text.strip(), image_filename, created_at),
    )
    conn.commit()
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
    row = conn.execute(
        "SELECT image_filename FROM templates WHERE id = ?", (template_id,)
    ).fetchone()

    if not row:
        conn.close()
        return False

    image_path = os.path.join(TEMPLATE_IMAGES_FOLDER, row["image_filename"])
    if os.path.exists(image_path):
        os.remove(image_path)

    conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()

    print(f"[Template] Deleted: {template_id}")
    return True
