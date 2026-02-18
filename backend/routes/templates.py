import os
import uuid

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from config import TEMPLATE_IMAGES_FOLDER
from models.template import (
    list_templates as db_list_templates,
    create_template as db_create_template,
    delete_template as db_delete_template,
)

templates_bp = Blueprint('templates', __name__)


@templates_bp.route('/api/templates', methods=['GET'])
def list_templates():
    """List all prompt templates."""
    try:
        templates = db_list_templates()
        return jsonify({"templates": templates})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@templates_bp.route('/api/templates', methods=['POST'])
def create_template():
    """Create a new prompt template with an image and prompt containing trigger_keyword."""
    try:
        name = request.form.get('name')
        prompt_text = request.form.get('prompt')
        image_file = request.files.get('image')

        if not name or not prompt_text or not image_file:
            return jsonify({"error": "name, prompt, and image are required"}), 400

        template_id = str(uuid.uuid4())
        ext = os.path.splitext(secure_filename(image_file.filename))[1] or '.png'
        image_filename = f"{template_id}{ext}"
        image_path = os.path.join(TEMPLATE_IMAGES_FOLDER, image_filename)
        image_file.save(image_path)

        result = db_create_template(name, prompt_text, image_filename)
        return jsonify(result)

    except Exception as e:
        print(f"[Template] Error: {e}")
        return jsonify({"error": str(e)}), 500


@templates_bp.route('/api/templates/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    """Delete a prompt template."""
    try:
        success = db_delete_template(template_id)
        if not success:
            return jsonify({"error": "Template not found"}), 404
        return jsonify({"success": True})
    except Exception as e:
        print(f"[Template] Error: {e}")
        return jsonify({"error": str(e)}), 500


@templates_bp.route('/api/template-images/<filename>', methods=['GET'])
def serve_template_image(filename):
    """Serve a template preview image."""
    filepath = os.path.join(TEMPLATE_IMAGES_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    ext = os.path.splitext(filepath)[1].lower()
    mimetypes = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    return send_file(filepath, mimetype=mimetypes.get(ext, "application/octet-stream"))
