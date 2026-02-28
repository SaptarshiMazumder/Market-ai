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

MASKS_FOLDER = 'masks'

masking_bp = Blueprint('masking', __name__)

TERMINAL_FAILED = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}


def _parse_params(src):
    def _get(key, default=None):
        return src.get(key, default)

    return {
        "image_url": _get("image_url"),
        "object_name": _get("object_name"),
        "seed": int(_get("seed")) if _get("seed") is not None else None,
        "mask_dilation": int(_get("mask_dilation")) if _get("mask_dilation") is not None else None,
        "mask_blur": int(_get("mask_blur")) if _get("mask_blur") is not None else None,
    }


def _run_masking(params):
    image_url = params["image_url"]
    object_name = params["object_name"]

    print(f"[Mask] image_url={image_url}  object_name={object_name}")

    start_time = time.time()

    job_id = submit_job(
        image_url=image_url,
        object_name=object_name,
        seed=params["seed"],
        mask_dilation=params["mask_dilation"],
        mask_blur=params["mask_blur"],
    )
    print(f"[Mask] RunPod job submitted: {job_id}")

    timeout = 300
    while time.time() - start_time < timeout:
        data = get_job_status(job_id)
        status = data.get("status")
        print(f"[Mask] Job {job_id} status: {status}")

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
        return None, "No mask images returned from RunPod"

    r2_path = images[0]["r2_path"]
    image_bytes = download_image(r2_path)

    out_filename = f"{uuid.uuid4()}.png"
    out_path = os.path.join(MASKS_FOLDER, out_filename)
    with open(out_path, 'wb') as f:
        f.write(image_bytes)

    duration = round(time.time() - start_time, 2)
    worker_params = output.get("params", {})

    result = {
        "success": True,
        "image_url": f"/api/masks/{out_filename}",
        "r2_path": r2_path,
        "object_name": object_name,
        "masking_params": {
            "seed": worker_params.get("seed", params["seed"]),
            "mask_dilation": worker_params.get("mask_dilation", params["mask_dilation"]),
            "mask_blur": worker_params.get("mask_blur", params["mask_blur"]),
        },
        "duration_seconds": duration,
    }
    return result, None


@masking_bp.route('/api/mask', methods=['POST'])
def mask_image():
    """Generate a mask for an object in an image (synchronous)."""
    try:
        data = request.json or {}
        params = _parse_params(data)

        if not params["image_url"] or not params["object_name"]:
            return jsonify({"error": "image_url and object_name are required"}), 400

        result, error = _run_masking(params)
        if error:
            return jsonify({"error": error}), 500

        return jsonify(result)

    except Exception as e:
        print(f"[Mask] Error: {e}")
        return jsonify({"error": str(e)}), 500


@masking_bp.route('/api/mask/async', methods=['POST'])
def mask_image_async():
    """Submit a masking job and return immediately with a job ID."""
    try:
        data = request.json or {}
        params = _parse_params(data)

        if not params["image_url"] or not params["object_name"]:
            return jsonify({"error": "image_url and object_name are required"}), 400

        gen_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        create_job(gen_id, params["image_url"], params["object_name"], params, now)

        thread = threading.Thread(
            target=_async_worker, args=(gen_id, params), daemon=True
        )
        thread.start()

        return jsonify({"job_id": gen_id, "status": "pending"}), 202

    except Exception as e:
        print(f"[MaskAsync] Error: {e}")
        return jsonify({"error": str(e)}), 500


@masking_bp.route('/api/mask/<job_id>', methods=['GET'])
def get_mask_status(job_id):
    """Poll the status and result of an async masking job."""
    try:
        job = get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        response = {
            "job_id": job["id"],
            "status": job["status"],
            "image_url": job["image_url"],
            "object_name": job["object_name"],
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
        result, error = _run_masking(params)
        if error:
            update_job(gen_id, "failed", error=error, updated_at=now())
        else:
            update_job(gen_id, "completed", result=result, updated_at=now())
    except Exception as e:
        print(f"[AsyncWorker] {gen_id} error: {e}")
        update_job(gen_id, "failed", error=str(e), updated_at=now())


@masking_bp.route('/api/masks/<filename>', methods=['GET'])
def serve_mask(filename):
    """Serve a generated mask image."""
    filepath = os.path.join(MASKS_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')
