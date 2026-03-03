import os
import uuid

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from models.template import (
    list_templates as db_list,
    get_template as db_get,
    create_template as db_create,
    delete_template as db_delete,
)

TEMPLATE_IMAGES_FOLDER = 'template_images'

templates_bp = Blueprint('templates', __name__)


@templates_bp.route('/api/templates', methods=['GET'])
def list_templates():
    try:
        return jsonify({"templates": db_list()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@templates_bp.route('/api/templates', methods=['POST'])
def create_template():
    try:
        name = request.form.get('name')
        lora_filename = request.form.get('lora_filename')
        keyword = request.form.get('keyword')
        image_file = request.files.get('preview_image')

        if not name or not lora_filename or not keyword or not image_file:
            return jsonify({"error": "name, lora_filename, keyword, and preview_image are required"}), 400

        template_id = str(uuid.uuid4())
        ext = os.path.splitext(secure_filename(image_file.filename))[1] or '.png'
        image_filename = f"{template_id}{ext}"
        image_file.save(os.path.join(TEMPLATE_IMAGES_FOLDER, image_filename))

        result = db_create(name, lora_filename, keyword, image_filename)
        return jsonify(result), 201

    except Exception as e:
        print(f"[Template] Error: {e}")
        return jsonify({"error": str(e)}), 500


@templates_bp.route('/api/templates/<template_id>', methods=['GET'])
def get_template(template_id):
    try:
        template = db_get(template_id)
        if not template:
            return jsonify({"error": "Template not found"}), 404
        return jsonify(template)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@templates_bp.route('/api/templates/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    try:
        if not db_delete(template_id):
            return jsonify({"error": "Template not found"}), 404
        return jsonify({"success": True})
    except Exception as e:
        print(f"[Template] Error: {e}")
        return jsonify({"error": str(e)}), 500


@templates_bp.route('/api/template-images/<filename>', methods=['GET'])
def serve_template_image(filename):
    filepath = os.path.join(TEMPLATE_IMAGES_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    ext = os.path.splitext(filepath)[1].lower()
    mimetypes = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
    return send_file(filepath, mimetype=mimetypes.get(ext, "application/octet-stream"))
