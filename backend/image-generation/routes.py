import os
import time
import uuid

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

from services.gemini import generate_prompt as gemini_generate_prompt
from services.runpod import submit_job, get_job_status
from services.r2 import download_image

UPLOAD_FOLDER = 'uploads'
GENERATED_FOLDER = 'generated'

generate_bp = Blueprint('generate', __name__)

TERMINAL_FAILED = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}


@generate_bp.route('/api/generate', methods=['POST'])
def generate_image():
    """Generate an image using a trained Flux LoRA via RunPod + ComfyUI."""
    try:
        if request.content_type and 'multipart/form-data' in request.content_type:
            model_string = request.form.get('model_string')
            prompt = request.form.get('prompt')
            lora_scale = float(request.form.get('lora_scale', 1.0))
            num_inference_steps = int(request.form.get('num_inference_steps', 25))
            width = int(request.form.get('width', 1024))
            height = int(request.form.get('height', 1024))
        else:
            data = request.json or {}
            model_string = data.get('model_string')
            prompt = data.get('prompt')
            lora_scale = float(data.get('lora_scale', 1.0))
            num_inference_steps = int(data.get('num_inference_steps', 25))
            width = int(data.get('width', 1024))
            height = int(data.get('height', 1024))

        if not model_string or not prompt:
            return jsonify({"error": "model_string and prompt are required"}), 400

        print(f"[Generate] LoRA: {model_string}")
        print(f"[Generate] Prompt: {prompt}")

        job_id = submit_job(
            lora_key=model_string,
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


@generate_bp.route('/api/generate-prompt', methods=['POST'])
def generate_prompt():
    """Use Gemini to analyze a sample image and generate an optimized prompt."""
    try:
        trigger_word = request.form.get("trigger_word", "")
        sample_file = request.files.get("sample_image")

        if not sample_file:
            return jsonify({"error": "sample_image is required"}), 400

        filename = f"{uuid.uuid4()}_{secure_filename(sample_file.filename)}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        sample_file.save(filepath)

        generated_prompt = gemini_generate_prompt(filepath, trigger_word)
        return jsonify({"prompt": generated_prompt})

    except Exception as e:
        print(f"[PromptGen] Error: {e}")
        return jsonify({"error": str(e)}), 500


@generate_bp.route('/api/images/<filename>', methods=['GET'])
def serve_image(filename):
    """Serve a generated image."""
    filepath = os.path.join(GENERATED_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')
