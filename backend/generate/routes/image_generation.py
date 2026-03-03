import os
import time
import uuid
import threading

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from services.image_generation.shared.prompt import generate_prompt
from services.image_generation.lora_z_turbo_upscale.runpod import submit_job as lora_submit_job
from services.image_generation.lora_z_turbo_upscale.runpod import get_job_status as lora_get_job_status
from services.image_generation.z_turbo.runpod import submit_job as z_turbo_submit_job
from services.image_generation.z_turbo.runpod import get_job_status as z_turbo_get_job_status
from services.r2 import download_image
from routes.config import LORA_Z_TURBO_UPSCALE_ENDPOINT_ID, Z_TURBO_ENDPOINT_ID

GENERATED_FOLDER = 'generated'
TERMINAL_FAILED = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}

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


def _poll_and_finish(job_id, runpod_job_id, endpoint_id, get_status_fn):
    start = time.time()
    timeout = 600
    try:
        while time.time() - start < timeout:
            data = get_status_fn(endpoint_id, runpod_job_id)
            status = data.get("status")
            print(f"[ImageGen] {job_id} RunPod status: {status}")

            if status == "COMPLETED":
                output = data.get("output", {})
                images = output.get("images", [])
                if not images:
                    _set_job(job_id, status="failed", error="No images returned from RunPod")
                    return

                r2_path = images[0]["r2_path"]
                image_bytes = download_image(r2_path)

                filename = f"{uuid.uuid4()}.png"
                with open(os.path.join(GENERATED_FOLDER, filename), 'wb') as f:
                    f.write(image_bytes)

                params = output.get("params", {})
                duration = round(time.time() - start, 2)

                _set_job(job_id, status="completed", result={
                    "image_url": f"/api/generate/images/{filename}",
                    "r2_path": r2_path,
                    "params": params,
                    "duration_seconds": duration,
                })
                return

            elif status in TERMINAL_FAILED:
                error_detail = data.get("error") or data.get("output", {}).get("error") or status.lower()
                print(f"[ImageGen] {job_id} RunPod full response: {data}")
                _set_job(job_id, status="failed", error=f"RunPod {status.lower()}: {error_detail}")
                return

            time.sleep(5)

        _set_job(job_id, status="failed", error="Timed out waiting for RunPod")

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
        lora_strength = float(body.get("lora_strength", 1.0))
        upscale_lora_strength = float(body.get("upscale_lora_strength", 0.6))
        seed_raw = body.get("seed")
        seed = int(seed_raw) if seed_raw not in (None, "", "null") else None

        if not subject:
            return jsonify({"error": "subject is required"}), 400
        if not lora_name:
            return jsonify({"error": "lora_name is required"}), 400

        print(f"[ImageGen/LoraZTurbo] Generating prompt for subject='{subject}' keyword='{keyword}'")
        prompt = generate_prompt(subject=subject, keyword=keyword, scenario=scenario)
        print(f"[ImageGen/LoraZTurbo] Prompt: {prompt[:120]}...")

        runpod_job_id = lora_submit_job(
            endpoint_id=LORA_Z_TURBO_UPSCALE_ENDPOINT_ID,
            lora_name=lora_name,
            prompt=prompt,
            width=width,
            height=height,
            lora_strength=lora_strength,
            upscale_lora_strength=upscale_lora_strength,
            seed=seed,
        )
        print(f"[ImageGen/LoraZTurbo] RunPod job submitted: {runpod_job_id}")

        job_id = str(uuid.uuid4())
        _set_job(job_id, status="processing", generated_prompt=prompt, runpod_job_id=runpod_job_id)

        threading.Thread(
            target=_poll_and_finish,
            args=(job_id, runpod_job_id, LORA_Z_TURBO_UPSCALE_ENDPOINT_ID, lora_get_job_status),
            daemon=True,
        ).start()

        return jsonify({"job_id": job_id, "status": "processing", "generated_prompt": prompt}), 202

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
        "generated_prompt": job.get("generated_prompt"),
    }
    if job.get("result"):
        response["result"] = job["result"]
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
        seed_raw = body.get("seed")
        seed = int(seed_raw) if seed_raw not in (None, "", "null") else None

        if not subject:
            return jsonify({"error": "subject is required"}), 400

        print(f"[ImageGen/ZTurbo] Generating prompt for subject='{subject}'")
        prompt = generate_prompt(subject=subject, keyword="", scenario=scenario)
        print(f"[ImageGen/ZTurbo] Prompt: {prompt[:120]}...")

        runpod_job_id = z_turbo_submit_job(
            endpoint_id=Z_TURBO_ENDPOINT_ID,
            prompt=prompt,
            width=width,
            height=height,
            seed=seed,
        )
        print(f"[ImageGen/ZTurbo] RunPod job submitted: {runpod_job_id}")

        job_id = str(uuid.uuid4())
        _set_job(job_id, status="processing", generated_prompt=prompt, runpod_job_id=runpod_job_id)

        threading.Thread(
            target=_poll_and_finish,
            args=(job_id, runpod_job_id, Z_TURBO_ENDPOINT_ID, z_turbo_get_job_status),
            daemon=True,
        ).start()

        return jsonify({"job_id": job_id, "status": "processing", "generated_prompt": prompt}), 202

    except Exception as e:
        print(f"[ImageGen/ZTurbo] Submit error: {e}")
        return jsonify({"error": str(e)}), 500


@image_generation_bp.route('/api/generate/images/<filename>', methods=['GET'])
def serve_image(filename):
    filepath = os.path.join(GENERATED_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')
