import os
import uuid

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename
import replicate
import requests as http_requests

from config import UPLOAD_FOLDER, GENERATED_FOLDER
from services.gemini import generate_prompt as gemini_generate_prompt, generate_upscale_prompts

generate_bp = Blueprint('generate', __name__)


@generate_bp.route('/api/generate', methods=['POST'])
def generate_image():
    """Generate an image using a trained Flux LoRA model."""
    try:
        # Handle multipart form data (for file upload) or JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            model_string = request.form.get('model_string')
            prompt = request.form.get('prompt')
            lora_scale = float(request.form.get('lora_scale', 1.0))
            prompt_strength = float(request.form.get('prompt_strength', 0.8))
            guidance_scale = float(request.form.get('guidance_scale', 3))
            num_inference_steps = int(request.form.get('num_inference_steps', 28))
            width = int(request.form.get('width', 1024))
            height = int(request.form.get('height', 1024))
            ref_file = request.files.get('image')
        else:
            data = request.json or {}
            model_string = data.get('model_string')
            prompt = data.get('prompt')
            lora_scale = float(data.get('lora_scale', 1.0))
            prompt_strength = float(data.get('prompt_strength', 0.8))
            guidance_scale = float(data.get('guidance_scale', 3))
            num_inference_steps = int(data.get('num_inference_steps', 28))
            width = int(data.get('width', 1024))
            height = int(data.get('height', 1024))
            ref_file = None

        if not model_string or not prompt:
            return jsonify({"error": "model_string and prompt are required"}), 400

        # Build input params
        input_params = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_outputs": 1,
            "lora_scale": lora_scale,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "output_format": "png",
            "output_quality": 100,
        }

        # If reference image uploaded, save it and pass as file URI
        if ref_file:
            filename = f"{uuid.uuid4()}_{secure_filename(ref_file.filename)}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            ref_file.save(filepath)
            input_params["image"] = open(filepath, "rb")
            input_params["prompt_strength"] = prompt_strength

        print(f"[Generate] Model: {model_string}")
        print(f"[Generate] Prompt: {prompt}")
        print(f"[Generate] Params: lora_scale={lora_scale}, guidance={guidance_scale}, steps={num_inference_steps}")

        output = replicate.run(model_string, input=input_params)

        # Download the result
        image_url = output[0] if isinstance(output, list) else output
        resp = http_requests.get(str(image_url))

        if resp.status_code != 200:
            return jsonify({"error": "Failed to download generated image"}), 500

        out_filename = f"{uuid.uuid4()}.png"
        out_path = os.path.join(GENERATED_FOLDER, out_filename)
        with open(out_path, 'wb') as f:
            f.write(resp.content)

        print(f"[Generate] Saved to {out_path}")

        return jsonify({
            "success": True,
            "image_url": f"/api/images/{out_filename}",
        })

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

        # Save and open the sample image
        filename = f"{uuid.uuid4()}_{secure_filename(sample_file.filename)}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        sample_file.save(filepath)

        generated_prompt = gemini_generate_prompt(filepath, trigger_word)

        return jsonify({"prompt": generated_prompt})

    except Exception as e:
        print(f"[PromptGen] Error: {e}")
        return jsonify({"error": str(e)}), 500


@generate_bp.route('/api/upscale', methods=['POST'])
def upscale_image():
    """Upscale a generated image using Gemini prompts + Clarity Upscaler."""
    try:
        data = request.json or {}
        image_filename = data.get("image_filename")

        if not image_filename:
            return jsonify({"error": "image_filename is required"}), 400

        image_path = os.path.join(GENERATED_FOLDER, secure_filename(image_filename))
        if not os.path.exists(image_path):
            return jsonify({"error": "Image not found"}), 404

        # Step 1: Generate prompts with Gemini
        print(f"[Upscale] Generating prompts with Gemini for {image_filename}")
        prompt, negative_prompt = generate_upscale_prompts(image_path)
        print(f"[Upscale] Prompt: {prompt}")
        print(f"[Upscale] Negative: {negative_prompt}")

        # Step 2: Run Clarity Upscaler
        print(f"[Upscale] Running clarity-upscaler...")
        output = replicate.run(
            "philz1337x/clarity-upscaler:dfad41707589d68ecdccd1dfa600d55a208f9310748e44bfe35b4a6291453d5e",
            input={
                "image": open(image_path, "rb"),
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "scale_factor": 2,
                "num_inference_steps": 18,
                "seed": 1337,
                "dynamic": 6,
                "creativity": 0.35,
                "resemblance": 0.6,
            }
        )

        # Download upscaled result
        upscaled_url = output[0] if isinstance(output, list) else output
        resp = http_requests.get(str(upscaled_url))

        if resp.status_code != 200:
            return jsonify({"error": "Failed to download upscaled image"}), 500

        out_filename = f"upscaled_{uuid.uuid4()}.png"
        out_path = os.path.join(GENERATED_FOLDER, out_filename)
        with open(out_path, 'wb') as f:
            f.write(resp.content)

        print(f"[Upscale] Saved to {out_path}")

        return jsonify({
            "success": True,
            "image_url": f"/api/images/{out_filename}",
            "prompt": prompt,
            "negative_prompt": negative_prompt,
        })

    except Exception as e:
        print(f"[Upscale] Error: {e}")
        return jsonify({"error": str(e)}), 500


@generate_bp.route('/api/images/<filename>', methods=['GET'])
def serve_image(filename):
    """Serve a generated image."""
    filepath = os.path.join(GENERATED_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')
