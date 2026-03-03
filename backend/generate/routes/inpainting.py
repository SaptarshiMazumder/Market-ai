import os
import time
import uuid
import threading

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from services.inpainting.runpod import submit_job, get_job_status
from services.r2 import download_image
from routes.config import INPAINTING_ENDPOINT_ID

INPAINTED_FOLDER = 'inpainted'
TERMINAL_FAILED = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}

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


def _poll_and_finish(job_id, runpod_job_id):
    start = time.time()
    timeout = 600
    try:
        while time.time() - start < timeout:
            data = get_job_status(INPAINTING_ENDPOINT_ID, runpod_job_id)
            status = data.get("status")
            print(f"[Inpaint] {job_id} RunPod status: {status}")

            if status == "COMPLETED":
                output = data.get("output", {})
                images = output.get("images", [])
                if not images:
                    _set_job(job_id, status="failed", error="No images returned from RunPod")
                    return

                r2_path = images[0]["r2_path"]
                image_bytes = download_image(r2_path)

                filename = f"{uuid.uuid4()}.png"
                with open(os.path.join(INPAINTED_FOLDER, filename), 'wb') as f:
                    f.write(image_bytes)

                worker_params = output.get("params", {})
                duration = round(time.time() - start, 2)

                _set_job(job_id, status="completed", result={
                    "image_url": f"/api/inpainted/{filename}",
                    "r2_path": r2_path,
                    "params": worker_params,
                    "duration_seconds": duration,
                })
                return

            elif status in TERMINAL_FAILED:
                error_detail = data.get("error") or data.get("output", {}).get("error") or status.lower()
                print(f"[Inpaint] {job_id} RunPod full response: {data}")
                _set_job(job_id, status="failed", error=f"RunPod {status.lower()}: {error_detail}")
                return

            time.sleep(5)

        _set_job(job_id, status="failed", error="Timed out waiting for RunPod")

    except Exception as e:
        print(f"[Inpaint] {job_id} error: {e}")
        _set_job(job_id, status="failed", error=str(e))


@inpainting_bp.route('/api/inpaint/submit', methods=['POST'])
def submit():
    try:
        body = request.json or {}
        scene_url = body.get("scene_url", "").strip()
        reference_url = body.get("reference_url", "").strip()
        prompt = body.get("prompt", "product on a surface").strip() or "product on a surface"
        seed_raw = body.get("seed")
        seed = int(seed_raw) if seed_raw not in (None, "", "null") else None
        steps_raw = body.get("steps")
        steps = int(steps_raw) if steps_raw not in (None, "", "null") else None
        denoise_raw = body.get("denoise")
        denoise = float(denoise_raw) if denoise_raw not in (None, "", "null") else None
        guidance_raw = body.get("guidance")
        guidance = float(guidance_raw) if guidance_raw not in (None, "", "null") else None

        if not scene_url:
            return jsonify({"error": "scene_url is required"}), 400
        if not reference_url:
            return jsonify({"error": "reference_url is required"}), 400

        runpod_job_id = submit_job(
            endpoint_id=INPAINTING_ENDPOINT_ID,
            scene_url=scene_url,
            reference_url=reference_url,
            prompt=prompt,
            seed=seed,
            steps=steps,
            denoise=denoise,
            guidance=guidance,
        )
        print(f"[Inpaint] RunPod job submitted: {runpod_job_id}")

        job_id = str(uuid.uuid4())
        _set_job(job_id, status="processing", scene_url=scene_url, reference_url=reference_url)

        threading.Thread(target=_poll_and_finish, args=(job_id, runpod_job_id), daemon=True).start()

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
