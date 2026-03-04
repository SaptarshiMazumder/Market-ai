import os
import uuid
import threading

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from nodes.inpainting import run as inpainting_run, NodeFailed
from services.r2 import download_image

INPAINTED_FOLDER = 'inpainted'

inpainting_bp = Blueprint('inpainting', __name__)

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


def _run_node(job_id, scene_url, reference_url, subject):
    try:
        result = inpainting_run(masked_r2=scene_url, product_r2=reference_url, subject=subject)
        image_bytes = download_image(result["r2_path"])
        filename = f"{uuid.uuid4()}.png"
        with open(os.path.join(INPAINTED_FOLDER, filename), 'wb') as f:
            f.write(image_bytes)
        _set_job(job_id, status="completed", result={
            "image_url": f"/api/inpainted/{filename}",
            "r2_path": result["r2_path"],
            "prompt": result["prompt"],
            "score": result["score"],
            "reason": result["reason"],
            "attempts_used": result["attempts_used"],
        })
    except NodeFailed as e:
        _set_job(job_id, status="failed", error=str(e))
    except Exception as e:
        print(f"[Inpaint] {job_id} error: {e}")
        _set_job(job_id, status="failed", error=str(e))


@inpainting_bp.route('/api/inpaint/submit', methods=['POST'])
def submit():
    try:
        body = request.json or {}
        scene_url = body.get("scene_url", "").strip()
        reference_url = body.get("reference_url", "").strip()
        subject = body.get("subject", "product").strip() or "product"

        if not scene_url:
            return jsonify({"error": "scene_url is required"}), 400
        if not reference_url:
            return jsonify({"error": "reference_url is required"}), 400

        job_id = str(uuid.uuid4())
        _set_job(job_id, status="processing", scene_url=scene_url, reference_url=reference_url)

        threading.Thread(
            target=_run_node,
            args=(job_id, scene_url, reference_url, subject),
            daemon=True,
        ).start()

        return jsonify({"job_id": job_id, "status": "processing"}), 202

    except Exception as e:
        print(f"[Inpaint] Submit error: {e}")
        return jsonify({"error": str(e)}), 500


@inpainting_bp.route('/api/inpaint/status/<job_id>', methods=['GET'])
def status(job_id):
    job = _get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    response = {
        "job_id": job_id,
        "status": job.get("status"),
        "scene_url": job.get("scene_url"),
        "reference_url": job.get("reference_url"),
    }
    if job.get("result"):
        response["result"] = job["result"]
    if job.get("error"):
        response["error"] = job["error"]

    return jsonify(response)


@inpainting_bp.route('/api/inpainted/<filename>', methods=['GET'])
def serve_inpainted(filename):
    filepath = os.path.join(INPAINTED_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')
