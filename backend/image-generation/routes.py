import os
import time
import uuid

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from services.runpod import submit_job, get_job_status
from services.r2 import download_image
from services.db import get_model_url

GENERATED_FOLDER = 'generated'

generate_bp = Blueprint('generate', __name__)

TERMINAL_FAILED = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}


@generate_bp.route('/api/generate', methods=['POST'])
def generate_image():
    """Generate an image using a trained Flux LoRA via RunPod + ComfyUI."""
    try:
        if request.content_type and 'multipart/form-data' in request.content_type:
            model_id = request.form.get('model_id')
            prompt = request.form.get('prompt')
            lora_scale = float(request.form.get('lora_scale', 1.0))
            num_inference_steps = int(request.form.get('num_inference_steps', 25))
            width = int(request.form.get('width', 1024))
            height = int(request.form.get('height', 1024))
        else:
            data = request.json or {}
            model_id = data.get('model_id')
            prompt = data.get('prompt')
            lora_scale = float(data.get('lora_scale', 1.0))
            num_inference_steps = int(data.get('num_inference_steps', 25))
            width = int(data.get('width', 1024))
            height = int(data.get('height', 1024))

        if not model_id or not prompt:
            return jsonify({"error": "model_id and prompt are required"}), 400

        lora_key = get_model_url(int(model_id))
        if not lora_key:
            return jsonify({"error": f"No succeeded model found for id {model_id}"}), 404

        print(f"[Generate] model_id={model_id}  lora_key={lora_key}")
        print(f"[Generate] Prompt: {prompt}")

        job_id = submit_job(
            lora_key=lora_key,
            prompt=prompt,
            width=width,
            height=height,
            steps=num_inference_steps,
            lora_scale=lora_scale,
        )
        print(f"[Generate] RunPod job submitted: {job_id}")

        # Poll until terminal state (image generation ~30-120s)
        timeout = 300
        start = time.time()
        while time.time() - start < timeout:
            data = get_job_status(job_id)
            status = data.get("status")
            print(f"[Generate] Job {job_id} status: {status}")

            if status == "COMPLETED":
                break
            elif status in TERMINAL_FAILED:
                return jsonify({"error": f"RunPod job {status.lower()}"}), 500

            time.sleep(5)
        else:
            return jsonify({"error": "RunPod job timed out"}), 500

        output = data.get("output", {})
        images = output.get("images", [])
        if not images:
            return jsonify({"error": "No images returned from RunPod"}), 500

        r2_path = images[0]["r2_path"]
        print(f"[Generate] Downloading image from R2: {r2_path}")

        image_bytes = download_image(r2_path)

        out_filename = f"{uuid.uuid4()}.png"
        out_path = os.path.join(GENERATED_FOLDER, out_filename)
        with open(out_path, 'wb') as f:
            f.write(image_bytes)

        print(f"[Generate] Saved to {out_path}")
        return jsonify({"success": True, "image_url": f"/api/images/{out_filename}"})

    except Exception as e:
        print(f"[Generate] Error: {e}")
        return jsonify({"error": str(e)}), 500



@generate_bp.route('/api/images/<filename>', methods=['GET'])
def serve_image(filename):
    """Serve a generated image."""
    filepath = os.path.join(GENERATED_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')
