from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
from dotenv import load_dotenv
import replicate
import requests as http_requests

load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
GENERATED_FOLDER = 'generated'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(GENERATED_FOLDER, exist_ok=True)


@app.route('/api/models', methods=['GET'])
def get_models():
    """Fetch all trained Flux LoRA models from Replicate."""
    try:
        trainings = replicate.trainings.list()
        models = []

        for t in trainings:
            if "ostris/flux-dev-lora-trainer" in t.model:
                entry = {
                    "trainer": t.model,
                    "status": t.status,
                    "destination": t.destination,
                }
                if t.status == "succeeded":
                    entry["model_string"] = f"{t.destination}:{t.version}"
                    entry["version"] = t.version
                models.append(entry)

        return jsonify({"models": models})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/generate', methods=['POST'])
def generate_image():
    """Generate an image using a trained Flux LoRA model."""
    try:
        # Handle multipart form data (for file upload) or JSON
        if request.content_type and 'multipart/form-data' in request.content_type:
            model_string = request.form.get('model_string')
            prompt = request.form.get('prompt')
            lora_scale = float(request.form.get('lora_scale', 1.0))
            prompt_strength = float(request.form.get('prompt_strength', 0.8))
            guidance_scale = float(request.form.get('guidance_scale', 3.5))
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
            guidance_scale = float(data.get('guidance_scale', 3.5))
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


@app.route('/api/images/<filename>', methods=['GET'])
def serve_image(filename):
    """Serve a generated image."""
    filepath = os.path.join(GENERATED_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
