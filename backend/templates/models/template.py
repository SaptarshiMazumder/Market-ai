import json
import os
import uuid
from datetime import datetime, timezone

DATA_FILE = 'templates_data.json'
TEMPLATE_IMAGES_FOLDER = 'template_images'


def _load():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r') as f:
        return json.load(f)


def _save(templates):
    with open(DATA_FILE, 'w') as f:
        json.dump(templates, f, indent=2)


def _to_dict(t):
    # Handle both hand-filled entries (preview_image_url set directly)
    # and API-created entries (preview_image filename → construct URL)
    if 'preview_image_url' in t:
        preview_url = t['preview_image_url']
    else:
        preview_url = f"/api/template-images/{t['preview_image']}"

    result = {
        "id": t["id"],
        "name": t["name"],
        "lora_filename": t["lora_filename"],
        "keyword": t.get("keyword", ""),
        "preview_image_url": preview_url,
        "created_at": t.get("created_at", ""),
    }
    if "url" in t:
        result["url"] = t["url"]
    return result


def list_templates():
    return [_to_dict(t) for t in _load()]


def get_template(template_id):
    for t in _load():
        if t["id"] == template_id:
            return _to_dict(t)
    return None


def create_template(name, lora_filename, keyword, preview_image_filename):
    templates = _load()
    entry = {
        "id": str(uuid.uuid4()),
        "name": name.strip(),
        "lora_filename": lora_filename.strip(),
        "keyword": keyword.strip(),
        "preview_image": preview_image_filename,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    templates.append(entry)
    _save(templates)
    print(f"[Template] Created: {name}")
    return _to_dict(entry)


def delete_template(template_id):
    templates = _load()
    match = next((t for t in templates if t["id"] == template_id), None)
    if not match:
        return False

    # Only delete file if it was API-created (has preview_image field)
    if 'preview_image' in match:
        image_path = os.path.join(TEMPLATE_IMAGES_FOLDER, match["preview_image"])
        if os.path.exists(image_path):
            os.remove(image_path)

    _save([t for t in templates if t["id"] != template_id])
    print(f"[Template] Deleted: {template_id}")
    return True
