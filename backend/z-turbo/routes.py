import os
import time
import uuid
import threading
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from services.runpod import submit_job, get_job_status
from services.r2 import download_image
from services.db import create_job, update_job, get_job

GENERATED_FOLDER = 'generated'

zturbo_bp = Blueprint('zturbo', __name__)

TERMINAL_FAILED = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}


def _parse_params(src):
    def _get(key, default=None):
        return src.get(key, default)

    seed_raw = _get("seed")
    return {
        "prompt": _get("prompt"),
        "width": int(_get("width", 1024)),
        "height": int(_get("height", 1024)),
        "steps": int(_get("steps", 8)),
        "cfg": float(_get("cfg", 1.0)),
        "denoise": float(_get("denoise", 1.0)),
        "seed": int(seed_raw) if seed_raw is not None and str(seed_raw).strip() != "" else None,
    }


def _run_generation(params):
    """Submit to RunPod, poll until done, download image, return result dict."""
    start_time = time.time()

    job_id = submit_job(
        prompt=params["prompt"],
        width=params["width"],
        height=params["height"],
        steps=params["steps"],
        cfg=params["cfg"],
        denoise=params["denoise"],
        seed=params["seed"],
    )
    print(f"[Z-Turbo] RunPod job submitted: {job_id}")

    timeout = 300
    data = {}
    while time.time() - start_time < timeout:
        data = get_job_status(job_id)
        status = data.get("status")
        print(f"[Z-Turbo] Job {job_id} status: {status}")

        if status == "COMPLETED":
            break
        elif status in TERMINAL_FAILED:
            return None, f"RunPod job {status.lower()}"

        time.sleep(5)
    else:
        return None, "RunPod job timed out"

    output = data.get("output", {})
    images = output.get("images", [])
    if not images:
        return None, "No images returned from RunPod"

    r2_path = images[0]["r2_path"]
    image_bytes = download_image(r2_path)

    out_filename = f"{uuid.uuid4()}.png"
    out_path = os.path.join(GENERATED_FOLDER, out_filename)
    with open(out_path, 'wb') as f:
        f.write(image_bytes)

    worker_params = output.get("params", {})
    duration = round(time.time() - start_time, 2)

    result = {
        "success": True,
        "image_url": f"/api/z-turbo/images/{out_filename}",
        "r2_path": r2_path,
        "params": {
            "prompt": params["prompt"],
            "width": params["width"],
            "height": params["height"],
            "steps": params["steps"],
            "cfg": params["cfg"],
            "denoise": params["denoise"],
            "seed": worker_params.get("seed", params["seed"]),
        },
        "duration_seconds": duration,
    }
    return result, None


@zturbo_bp.route('/api/z-turbo/generate', methods=['POST'])
def generate():
    """Generate an image using Z-Turbo via RunPod (sync)."""
    try:
        params = _parse_params(request.json or {})

        if not params["prompt"]:
            return jsonify({"error": "prompt is required"}), 400

        result, error = _run_generation(params)
        if error:
            return jsonify({"error": error}), 500

        return jsonify(result)

    except Exception as e:
        print(f"[Z-Turbo] Error: {e}")
        return jsonify({"error": str(e)}), 500


@zturbo_bp.route('/api/z-turbo/generate/async', methods=['POST'])
def generate_async():
    """Submit a Z-Turbo generation job and return immediately with a job ID."""
    try:
        params = _parse_params(request.json or {})

        if not params["prompt"]:
            return jsonify({"error": "prompt is required"}), 400

        gen_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        create_job(gen_id, params["prompt"], params, now)

        thread = threading.Thread(
            target=_async_worker, args=(gen_id, params), daemon=True
        )
        thread.start()

        return jsonify({"job_id": gen_id, "status": "pending"}), 202

    except Exception as e:
        print(f"[Z-Turbo Async] Error: {e}")
        return jsonify({"error": str(e)}), 500


@zturbo_bp.route('/api/z-turbo/generate/<job_id>', methods=['GET'])
def get_generate_status(job_id):
    """Poll the status and result of an async generation job."""
    try:
        job = get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        response = {
            "job_id": job["id"],
            "status": job["status"],
            "prompt": job["prompt"],
            "params": job["params"],
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
        }
        if job["result"]:
            response["result"] = job["result"]
        if job["error"]:
            response["error"] = job["error"]

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def _async_worker(gen_id, params):
    now = lambda: datetime.now(timezone.utc).isoformat()
    try:
        update_job(gen_id, "processing", updated_at=now())
        result, error = _run_generation(params)
        if error:
            update_job(gen_id, "failed", error=error, updated_at=now())
        else:
            update_job(gen_id, "completed", result=result, updated_at=now())
    except Exception as e:
        print(f"[Z-Turbo AsyncWorker] {gen_id} error: {e}")
        update_job(gen_id, "failed", error=str(e), updated_at=now())


@zturbo_bp.route('/api/z-turbo/images/<filename>', methods=['GET'])
def serve_image(filename):
    """Serve a generated image."""
    filepath = os.path.join(GENERATED_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')
