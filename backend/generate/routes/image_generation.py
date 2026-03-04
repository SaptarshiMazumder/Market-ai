import os
import uuid
import threading

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from nodes.image_gen import run as image_gen_run, NodeFailed
from services.r2 import download_image, list_product_images

GENERATED_FOLDER = 'generated'

image_generation_bp = Blueprint('image_generation', __name__)

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


def _run_node(job_id, **kwargs):
    try:
        result = image_gen_run(**kwargs)
        image_bytes = download_image(result["r2_path"])
        filename = f"{uuid.uuid4()}.png"
        with open(os.path.join(GENERATED_FOLDER, filename), 'wb') as f:
            f.write(image_bytes)
        _set_job(job_id, status="completed", result={
            "image_url": f"/api/generate/images/{filename}",
            "r2_path": result["r2_path"],
            "prompt": result["prompt"],
            "score": result["score"],
            "reason": result["reason"],
            "attempts_used": result["attempts_used"],
        })
    except NodeFailed as e:
        _set_job(job_id, status="failed", error=str(e))
    except Exception as e:
        print(f"[ImageGen] {job_id} error: {e}")
        _set_job(job_id, status="failed", error=str(e))


@image_generation_bp.route('/api/generate/image/submit', methods=['POST'])
def submit():
    try:
        body = request.json or {}
        subject = body.get("subject", "").strip()
        scenario = body.get("scenario", "").strip() or None
        lora_name = body.get("lora_name", "").strip()
        keyword = body.get("keyword", "").strip()
        width = int(body.get("width", 1024))
        height = int(body.get("height", 1024))

        if not subject:
            return jsonify({"error": "subject is required"}), 400
        if not lora_name:
            return jsonify({"error": "lora_name is required"}), 400

        job_id = str(uuid.uuid4())
        _set_job(job_id, status="processing")

        threading.Thread(
            target=_run_node,
            kwargs=dict(
                job_id=job_id, subject=subject, mode="template",
                lora_name=lora_name, keyword=keyword, scenario=scenario,
                width=width, height=height,
            ),
            daemon=True,
        ).start()

        return jsonify({"job_id": job_id, "status": "processing"}), 202

    except Exception as e:
        print(f"[ImageGen/LoraZTurbo] Submit error: {e}")
        return jsonify({"error": str(e)}), 500


@image_generation_bp.route('/api/generate/image/status/<job_id>', methods=['GET'])
def status(job_id):
    job = _get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    response = {
        "job_id": job_id,
        "status": job.get("status"),
    }
    if job.get("result"):
        response["result"] = job["result"]
        response["generated_prompt"] = job["result"].get("prompt")
    if job.get("error"):
        response["error"] = job["error"]

    return jsonify(response)


@image_generation_bp.route('/api/generate/image/submit/no-template', methods=['POST'])
def submit_no_template():
    try:
        body = request.json or {}
        subject = body.get("subject", "").strip()
        scenario = body.get("scenario", "").strip() or None
        width = int(body.get("width", 1024))
        height = int(body.get("height", 1024))

        if not subject:
            return jsonify({"error": "subject is required"}), 400

        job_id = str(uuid.uuid4())
        _set_job(job_id, status="processing")

        threading.Thread(
            target=_run_node,
            kwargs=dict(
                job_id=job_id, subject=subject, mode="no_template",
                scenario=scenario, width=width, height=height,
            ),
            daemon=True,
        ).start()

        return jsonify({"job_id": job_id, "status": "processing"}), 202

    except Exception as e:
        print(f"[ImageGen/ZTurbo] Submit error: {e}")
        return jsonify({"error": str(e)}), 500


@image_generation_bp.route('/api/generate/image/list', methods=['GET'])
def list_images():
    try:
        images = list_product_images()
        return jsonify({"images": images})
    except Exception as e:
        print(f"[ImageGen] List error: {e}")
        return jsonify({"error": str(e)}), 500


@image_generation_bp.route('/api/generate/images/<filename>', methods=['GET'])
def serve_image(filename):
    filepath = os.path.join(GENERATED_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')
