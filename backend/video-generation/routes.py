import os
import time
import uuid
import threading
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from services.runpod import submit_job, get_job_status
from services.r2 import download_video
from services.db import create_job, update_job, get_job

VIDEOS_FOLDER = 'videos'

video_bp = Blueprint('video', __name__)

TERMINAL_FAILED = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}


def _parse_params(src):
    def _get(key, default=None):
        return src.get(key, default)

    return {
        "image_url": _get("image_url"),
        "prompt": _get("prompt"),
        "width": int(_get("width")) if _get("width") is not None else None,
        "height": int(_get("height")) if _get("height") is not None else None,
        "length": int(_get("length")) if _get("length") is not None else None,
        "steps": int(_get("steps")) if _get("steps") is not None else None,
        "seed": int(_get("seed")) if _get("seed") is not None else None,
    }


def _run_video_generation(params):
    image_url = params["image_url"]

    print(f"[Video] image_url={image_url}")

    start_time = time.time()

    job_id = submit_job(
        image_url=image_url,
        prompt=params["prompt"],
        width=params["width"],
        height=params["height"],
        length=params["length"],
        steps=params["steps"],
        seed=params["seed"],
    )
    print(f"[Video] RunPod job submitted: {job_id}")

    timeout = 600
    while time.time() - start_time < timeout:
        data = get_job_status(job_id)
        status = data.get("status")
        print(f"[Video] Job {job_id} status: {status}")

        if status == "COMPLETED":
            break
        elif status in TERMINAL_FAILED:
            return None, f"RunPod job {status.lower()}"

        time.sleep(5)
    else:
        return None, "RunPod job timed out"

    output = data.get("output", {})
    videos = output.get("videos", [])
    if not videos:
        return None, "No videos returned from RunPod"

    r2_path = videos[0]["r2_path"]
    video_bytes = download_video(r2_path)

    out_filename = f"{uuid.uuid4()}.mp4"
    out_path = os.path.join(VIDEOS_FOLDER, out_filename)
    with open(out_path, 'wb') as f:
        f.write(video_bytes)

    duration = round(time.time() - start_time, 2)
    worker_params = output.get("params", {})

    result = {
        "success": True,
        "video_url": f"/api/videos/{out_filename}",
        "r2_path": r2_path,
        "video_params": {
            "prompt": worker_params.get("prompt", params["prompt"]),
            "seed": worker_params.get("seed", params["seed"]),
            "width": worker_params.get("width", params["width"]),
            "height": worker_params.get("height", params["height"]),
            "length": worker_params.get("length", params["length"]),
            "steps": worker_params.get("steps", params["steps"]),
        },
        "duration_seconds": duration,
    }
    return result, None


@video_bp.route('/api/video', methods=['POST'])
def generate_video():
    """Generate a video from an image (synchronous)."""
    try:
        data = request.json or {}
        params = _parse_params(data)

        if not params["image_url"]:
            return jsonify({"error": "image_url is required"}), 400

        result, error = _run_video_generation(params)
        if error:
            return jsonify({"error": error}), 500

        return jsonify(result)

    except Exception as e:
        print(f"[Video] Error: {e}")
        return jsonify({"error": str(e)}), 500


@video_bp.route('/api/video/async', methods=['POST'])
def generate_video_async():
    """Submit a video generation job and return immediately with a job ID."""
    try:
        data = request.json or {}
        params = _parse_params(data)

        if not params["image_url"]:
            return jsonify({"error": "image_url is required"}), 400

        gen_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        create_job(gen_id, params["image_url"], params["prompt"], params, now)

        thread = threading.Thread(
            target=_async_worker, args=(gen_id, params), daemon=True
        )
        thread.start()

        return jsonify({"job_id": gen_id, "status": "pending"}), 202

    except Exception as e:
        print(f"[VideoAsync] Error: {e}")
        return jsonify({"error": str(e)}), 500


@video_bp.route('/api/video/<job_id>', methods=['GET'])
def get_video_status(job_id):
    """Poll the status and result of an async video generation job."""
    try:
        job = get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        response = {
            "job_id": job["id"],
            "status": job["status"],
            "image_url": job["image_url"],
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
        result, error = _run_video_generation(params)
        if error:
            update_job(gen_id, "failed", error=error, updated_at=now())
        else:
            update_job(gen_id, "completed", result=result, updated_at=now())
    except Exception as e:
        print(f"[AsyncWorker] {gen_id} error: {e}")
        update_job(gen_id, "failed", error=str(e), updated_at=now())


@video_bp.route('/api/videos/<filename>', methods=['GET'])
def serve_video(filename):
    """Serve a generated video."""
    filepath = os.path.join(VIDEOS_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Video not found"}), 404
    return send_file(filepath, mimetype='video/mp4')
