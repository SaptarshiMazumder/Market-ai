import os
import uuid
import threading

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from nodes.masking import run as masking_run, NodeFailed
from services.r2 import download_image, upload_image, list_masked_images

MASKS_FOLDER = 'masks'

masking_bp = Blueprint('masking', __name__)

# In-memory job store
_jobs = {}
_lock = threading.Lock()


def _set_job(job_id, **fields):
    with _lock:
        if job_id not in _jobs:
            _jobs[job_id] = {}
        _jobs[job_id].update(fields)


def _get_job(job_id):
    with _lock:
        return dict(_jobs.get(job_id, {}))


def _run_node(job_id, image_url, object_name):
    try:
        result = masking_run(generated_r2=image_url, subject=object_name)
        image_bytes = download_image(result["r2_path"])
        filename = f"{uuid.uuid4()}.png"
        with open(os.path.join(MASKS_FOLDER, filename), 'wb') as f:
            f.write(image_bytes)
        _set_job(job_id, status="completed", result={
            "image_url": f"/api/masks/{filename}",
            "r2_path": result["r2_path"],
            "score": result["score"],
            "reason": result["reason"],
            "attempts_used": result["attempts_used"],
        })
    except NodeFailed as e:
        _set_job(job_id, status="failed", error=str(e))
    except Exception as e:
        print(f"[Mask] {job_id} error: {e}")
        _set_job(job_id, status="failed", error=str(e))


@masking_bp.route('/api/mask/list', methods=['GET'])
def list_masks_r2():
    try:
        images = list_masked_images()
        return jsonify({"images": images})
    except Exception as e:
        print(f"[Mask] List error: {e}")
        return jsonify({"error": str(e)}), 500


@masking_bp.route('/api/mask/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "file is required"}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({"error": "file is required"}), 400
    r2_path = upload_image(f.read(), secure_filename(f.filename))
    return jsonify({"r2_path": r2_path})


@masking_bp.route('/api/mask/submit', methods=['POST'])
def submit():
    try:
        body = request.json or {}
        image_url = body.get("image_url", "").strip()
        object_name = body.get("object_name", "").strip()

        if not image_url:
            return jsonify({"error": "image_url is required"}), 400
        if not object_name:
            return jsonify({"error": "object_name is required"}), 400

        job_id = str(uuid.uuid4())
        _set_job(job_id, status="processing", image_url=image_url, object_name=object_name)

        threading.Thread(
            target=_run_node,
            args=(job_id, image_url, object_name),
            daemon=True,
        ).start()

        return jsonify({"job_id": job_id, "status": "processing"}), 202

    except Exception as e:
        print(f"[Mask] Submit error: {e}")
        return jsonify({"error": str(e)}), 500


@masking_bp.route('/api/mask/status/<job_id>', methods=['GET'])
def status(job_id):
    job = _get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    response = {
        "job_id": job_id,
        "status": job.get("status"),
        "image_url": job.get("image_url"),
        "object_name": job.get("object_name"),
    }
    if job.get("result"):
        response["result"] = job["result"]
    if job.get("error"):
        response["error"] = job["error"]

    return jsonify(response)


@masking_bp.route('/api/masks/<filename>', methods=['GET'])
def serve_mask(filename):
    filepath = os.path.join(MASKS_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')
