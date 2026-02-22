import os
import time
import uuid
import threading
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from services.runpod import submit_job, get_job_status
from services.r2 import download_image
from services.db import get_model_url, create_generation_job, update_generation_job, get_generation_job

GENERATED_FOLDER = 'generated'

generate_bp = Blueprint('generate', __name__)

TERMINAL_FAILED = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}


def _parse_gen_params(src):
    """Extract generation parameters from request form data or JSON dict."""
    def _get(key, default=None):
        return src.get(key, default)

    return {
        "model_id": _get("model_id"),
        "prompt": _get("prompt"),
        "lora_scale": float(_get("lora_scale", 1.0)),
        "num_inference_steps": int(_get("num_inference_steps", 25)),
        "width": int(_get("width", 1024)),
        "height": int(_get("height", 1024)),
        "seed": int(_get("seed")) if _get("seed") is not None else None,
        "guidance_scale": float(_get("guidance_scale")) if _get("guidance_scale") is not None else None,
        "negative_prompt": _get("negative_prompt"),
    }


def _run_generation(params):
    """Submit to RunPod, poll until done, download image, return result dict."""
    model_id = params["model_id"]
    lora_key = get_model_url(int(model_id))
    if not lora_key:
        return None, f"No succeeded model found for id {model_id}"

    print(f"[Generate] model_id={model_id}  lora_key={lora_key}")

    start_time = time.time()

    job_id = submit_job(
        lora_key=lora_key,
        prompt=params["prompt"],
        width=params["width"],
        height=params["height"],
        steps=params["num_inference_steps"],
        lora_scale=params["lora_scale"],
        seed=params["seed"],
        guidance_scale=params["guidance_scale"],
        negative_prompt=params["negative_prompt"],
    )
    print(f"[Generate] RunPod job submitted: {job_id}")

    timeout = 300
    while time.time() - start_time < timeout:
        data = get_job_status(job_id)
        status = data.get("status")
        print(f"[Generate] Job {job_id} status: {status}")

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

    duration = round(time.time() - start_time, 2)
    worker_params = output.get("params", {})

    result = {
        "success": True,
        "image_url": f"/api/images/{out_filename}",
        "r2_path": r2_path,
        "model_id": int(model_id),
        "prompt": params["prompt"],
        "generation_params": {
            "lora_scale": params["lora_scale"],
            "width": params["width"],
            "height": params["height"],
            "steps": params["num_inference_steps"],
            "seed": worker_params.get("seed", params["seed"]),
            "guidance_scale": worker_params.get("guidance_scale", params["guidance_scale"]),
            "negative_prompt": params["negative_prompt"],
        },
        "duration_seconds": duration,
    }
    return result, None


@generate_bp.route('/api/generate', methods=['POST'])
def generate_image():
    """Generate an image using a trained Flux LoRA via RunPod + ComfyUI."""
    try:
        if request.content_type and 'multipart/form-data' in request.content_type:
            params = _parse_gen_params(request.form)
        else:
            params = _parse_gen_params(request.json or {})

        if not params["model_id"] or not params["prompt"]:
            return jsonify({"error": "model_id and prompt are required"}), 400

        result, error = _run_generation(params)
        if error:
            return jsonify({"error": error}), 500 if "not found" not in error.lower() else 404

        return jsonify(result)

    except Exception as e:
        print(f"[Generate] Error: {e}")
        return jsonify({"error": str(e)}), 500



@generate_bp.route('/api/generate/async', methods=['POST'])
def generate_image_async():
    """Submit an image generation job and return immediately with a job ID."""
    try:
        if request.content_type and 'multipart/form-data' in request.content_type:
            params = _parse_gen_params(request.form)
        else:
            params = _parse_gen_params(request.json or {})

        if not params["model_id"] or not params["prompt"]:
            return jsonify({"error": "model_id and prompt are required"}), 400

        lora_key = get_model_url(int(params["model_id"]))
        if not lora_key:
            return jsonify({"error": f"No succeeded model found for id {params['model_id']}"}), 404

        gen_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        create_generation_job(gen_id, int(params["model_id"]), params["prompt"], params, now)

        thread = threading.Thread(
            target=_async_worker, args=(gen_id, params), daemon=True
        )
        thread.start()

        return jsonify({"job_id": gen_id, "status": "pending"}), 202

    except Exception as e:
        print(f"[GenerateAsync] Error: {e}")
        return jsonify({"error": str(e)}), 500


@generate_bp.route('/api/generate/<job_id>', methods=['GET'])
def get_generation_status(job_id):
    """Poll the status and result of an async generation job."""
    try:
        job = get_generation_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        response = {
            "job_id": job["id"],
            "status": job["status"],
            "model_id": job["model_id"],
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
    """Background thread: runs the generation and updates the DB."""
    now = lambda: datetime.now(timezone.utc).isoformat()
    try:
        update_generation_job(gen_id, "processing", updated_at=now())
        result, error = _run_generation(params)
        if error:
            update_generation_job(gen_id, "failed", error=error, updated_at=now())
        else:
            update_generation_job(gen_id, "completed", result=result, updated_at=now())
    except Exception as e:
        print(f"[AsyncWorker] {gen_id} error: {e}")
        update_generation_job(gen_id, "failed", error=str(e), updated_at=now())


@generate_bp.route('/api/images/<filename>', methods=['GET'])
def serve_image(filename):
    """Serve a generated image."""
    filepath = os.path.join(GENERATED_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')
