import os
import time
import uuid
import threading

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from services.masking.runpod import submit_job, get_job_status
from services.r2 import download_image, upload_image
from routes.config import MASKING_ENDPOINT_ID

MASKS_FOLDER = 'masks'
TERMINAL_FAILED = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}

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


def _poll_and_finish(job_id, runpod_job_id):
    start = time.time()
    timeout = 600
    try:
        while time.time() - start < timeout:
            data = get_job_status(MASKING_ENDPOINT_ID, runpod_job_id)
            status = data.get("status")
            print(f"[Mask] {job_id} RunPod status: {status}")

            if status == "COMPLETED":
                output = data.get("output", {})
                images = output.get("images", [])
                if not images:
                    _set_job(job_id, status="failed", error="No images returned from RunPod")
                    return

                r2_path = images[0]["r2_path"]
                image_bytes = download_image(r2_path)

                filename = f"{uuid.uuid4()}.png"
                with open(os.path.join(MASKS_FOLDER, filename), 'wb') as f:
                    f.write(image_bytes)

                worker_params = output.get("params", {})
                duration = round(time.time() - start, 2)

                _set_job(job_id, status="completed", result={
                    "image_url": f"/api/masks/{filename}",
                    "r2_path": r2_path,
                    "params": worker_params,
                    "duration_seconds": duration,
                })
                return

            elif status in TERMINAL_FAILED:
                error_detail = data.get("error") or data.get("output", {}).get("error") or status.lower()
                print(f"[Mask] {job_id} RunPod full response: {data}")
                _set_job(job_id, status="failed", error=f"RunPod {status.lower()}: {error_detail}")
                return

            time.sleep(5)

        _set_job(job_id, status="failed", error="Timed out waiting for RunPod")

    except Exception as e:
        print(f"[Mask] {job_id} error: {e}")
        _set_job(job_id, status="failed", error=str(e))


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
        seed_raw = body.get("seed")
        seed = int(seed_raw) if seed_raw not in (None, "", "null") else None
        mask_dilation_raw = body.get("mask_dilation")
        mask_dilation = int(mask_dilation_raw) if mask_dilation_raw not in (None, "", "null") else None
        mask_blur_raw = body.get("mask_blur")
        mask_blur = int(mask_blur_raw) if mask_blur_raw not in (None, "", "null") else None

        if not image_url:
            return jsonify({"error": "image_url is required"}), 400
        if not object_name:
            return jsonify({"error": "object_name is required"}), 400

        runpod_job_id = submit_job(
            endpoint_id=MASKING_ENDPOINT_ID,
            image_url=image_url,
            object_name=object_name,
            seed=seed,
            mask_dilation=mask_dilation,
            mask_blur=mask_blur,
        )
        print(f"[Mask] RunPod job submitted: {runpod_job_id}")

        job_id = str(uuid.uuid4())
        _set_job(job_id, status="processing", image_url=image_url, object_name=object_name)

        threading.Thread(target=_poll_and_finish, args=(job_id, runpod_job_id), daemon=True).start()

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
