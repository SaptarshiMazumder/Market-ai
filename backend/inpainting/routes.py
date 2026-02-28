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

INPAINTED_FOLDER = 'inpainted'

inpainting_bp = Blueprint('inpainting', __name__)

TERMINAL_FAILED = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}


def _parse_params(src):
    def _get(key, default=None):
        return src.get(key, default)

    return {
        "scene_url": _get("scene_url"),
        "reference_url": _get("reference_url"),
        "prompt": _get("prompt"),
        "seed": int(_get("seed")) if _get("seed") is not None else None,
        "steps": int(_get("steps")) if _get("steps") is not None else None,
        "denoise": float(_get("denoise")) if _get("denoise") is not None else None,
        "guidance": float(_get("guidance")) if _get("guidance") is not None else None,
    }


def _run_inpainting(params):
    scene_url = params["scene_url"]
    reference_url = params["reference_url"]

    print(f"[Inpaint] scene={scene_url}  reference={reference_url}")

    start_time = time.time()

    job_id = submit_job(
        scene_url=scene_url,
        reference_url=reference_url,
        prompt=params["prompt"],
        seed=params["seed"],
        steps=params["steps"],
        denoise=params["denoise"],
        guidance=params["guidance"],
    )
    print(f"[Inpaint] RunPod job submitted: {job_id}")

    timeout = 600
    while time.time() - start_time < timeout:
        data = get_job_status(job_id)
        status = data.get("status")
        print(f"[Inpaint] Job {job_id} status: {status}")

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
    out_path = os.path.join(INPAINTED_FOLDER, out_filename)
    with open(out_path, 'wb') as f:
        f.write(image_bytes)

    duration = round(time.time() - start_time, 2)
    worker_params = output.get("params", {})

    result = {
        "success": True,
        "image_url": f"/api/inpainted/{out_filename}",
        "r2_path": r2_path,
        "inpainting_params": {
            "prompt": worker_params.get("prompt", params["prompt"]),
            "seed": worker_params.get("seed", params["seed"]),
            "steps": worker_params.get("steps", params["steps"]),
            "denoise": worker_params.get("denoise", params["denoise"]),
            "guidance": worker_params.get("guidance", params["guidance"]),
        },
        "duration_seconds": duration,
    }
    return result, None


@inpainting_bp.route('/api/inpaint', methods=['POST'])
def inpaint_image():
    """Inpaint a product into a masked scene (synchronous)."""
    try:
        data = request.json or {}
        params = _parse_params(data)

        if not params["scene_url"] or not params["reference_url"]:
            return jsonify({"error": "scene_url and reference_url are required"}), 400

        result, error = _run_inpainting(params)
        if error:
            return jsonify({"error": error}), 500

        return jsonify(result)

    except Exception as e:
        print(f"[Inpaint] Error: {e}")
        return jsonify({"error": str(e)}), 500


@inpainting_bp.route('/api/inpaint/async', methods=['POST'])
def inpaint_image_async():
    """Submit an inpainting job and return immediately with a job ID."""
    try:
        data = request.json or {}
        params = _parse_params(data)

        if not params["scene_url"] or not params["reference_url"]:
            return jsonify({"error": "scene_url and reference_url are required"}), 400

        gen_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        create_job(gen_id, params["scene_url"], params["reference_url"],
                   params["prompt"], params, now)

        thread = threading.Thread(
            target=_async_worker, args=(gen_id, params), daemon=True
        )
        thread.start()

        return jsonify({"job_id": gen_id, "status": "pending"}), 202

    except Exception as e:
        print(f"[InpaintAsync] Error: {e}")
        return jsonify({"error": str(e)}), 500


@inpainting_bp.route('/api/inpaint/<job_id>', methods=['GET'])
def get_inpaint_status(job_id):
    """Poll the status and result of an async inpainting job."""
    try:
        job = get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        response = {
            "job_id": job["id"],
            "status": job["status"],
            "scene_url": job["scene_url"],
            "reference_url": job["reference_url"],
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
        result, error = _run_inpainting(params)
        if error:
            update_job(gen_id, "failed", error=error, updated_at=now())
        else:
            update_job(gen_id, "completed", result=result, updated_at=now())
    except Exception as e:
        print(f"[AsyncWorker] {gen_id} error: {e}")
        update_job(gen_id, "failed", error=str(e), updated_at=now())


@inpainting_bp.route('/api/inpainted/<filename>', methods=['GET'])
def serve_inpainted(filename):
    """Serve an inpainted image."""
    filepath = os.path.join(INPAINTED_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')
