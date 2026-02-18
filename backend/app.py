from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
from dotenv import load_dotenv
import replicate
import requests as http_requests
from datetime import datetime, timezone
from services.replicate_models import ensure_model_exists
import google.generativeai as genai
import json
from PIL import Image

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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

        def _parse_dt(value):
            if not value:
                return None
            if isinstance(value, datetime):
                return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
            if isinstance(value, str):
                try:
                    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    return None
            return None

        def _duration_seconds(start, end):
            if not start or not end:
                return None
            return max(0.0, (end - start).total_seconds())

        for t in trainings:
            if "ostris/flux-dev-lora-trainer" in t.model:
                created_at = _parse_dt(getattr(t, "created_at", None))
                started_at = _parse_dt(getattr(t, "started_at", None))
                completed_at = _parse_dt(getattr(t, "completed_at", None))
                now = datetime.now(timezone.utc)

                queued_seconds = _duration_seconds(created_at, started_at)
                running_end = completed_at or (now if started_at else None)
                total_end = completed_at or (now if created_at else None)
                running_seconds = _duration_seconds(started_at, running_end)
                total_seconds = _duration_seconds(created_at, total_end)

                urls = getattr(t, "urls", {}) or {}
                output = getattr(t, "output", None) or {}

                # The real model string lives in output['version']
                # e.g. "saptarshimazumder/joystick:8d38a755..."
                output_version = output.get("version") if isinstance(output, dict) else None

                # Parse the name from the model string (before the colon)
                display_name = None
                if output_version and ":" in output_version:
                    display_name = output_version.split(":")[0]

                entry = {
                    "id": getattr(t, "id", None),
                    "trainer": t.model,
                    "model": t.model,
                    "source": getattr(t, "source", None),
                    "status": t.status,
                    "destination": display_name or t.destination,
                    "created_at": getattr(t, "created_at", None),
                    "started_at": getattr(t, "started_at", None),
                    "completed_at": getattr(t, "completed_at", None),
                    "queued_seconds": queued_seconds,
                    "running_seconds": running_seconds,
                    "total_seconds": total_seconds,
                    "training_url": urls.get("web"),
                }
                if t.status == "succeeded" and output_version:
                    entry["model_string"] = output_version
                    entry["version"] = output_version.split(":")[-1] if ":" in output_version else None
                models.append(entry)

        return jsonify({"models": models})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


FLUX_TRAINER_MODEL = "ostris/flux-dev-lora-trainer"
FLUX_TRAINER_VERSION = "e440909d3512c31646ee2e0c7d6f6f4923224863a6a10c494606e79fb5844497"
REPLICATE_OWNER = os.getenv("REPLICATE_OWNER", "saptarshimazumder")


@app.route('/api/train', methods=['POST'])
def start_training():
    """Start a new Flux LoRA training job."""
    try:
        model_name = request.form.get('model_name')
        trigger_word = request.form.get('trigger_word', 'TOK')
        zip_file = request.files.get('images')

        if not model_name or not zip_file:
            return jsonify({"error": "model_name and images (zip) are required"}), 400

        # Save the zip file
        filename = f"{uuid.uuid4()}_{secure_filename(zip_file.filename)}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        zip_file.save(filepath)

        # Ensure destination model exists in Replicate
        destination, _ = ensure_model_exists(model_name)

        print(f"[Train] Starting training: {destination}")
        print(f"[Train] Trigger word: {trigger_word}")

        training = replicate.trainings.create(
            model=FLUX_TRAINER_MODEL,
            version=FLUX_TRAINER_VERSION,
            input={
                "input_images": open(filepath, "rb"),
                "trigger_word": trigger_word,
                "steps": 1000,
                "lora_rank": 16,
                "optimizer": "adamw8bit",
                "batch_size": 1,
                "resolution": "512,768,1024",
                "autocaption": True,
                "learning_rate": 0.0004,
                "caption_dropout_rate": 0.05,
            },
            destination=destination
        )

        print(f"[Train] Training started with ID: {training.id}")

        return jsonify({
            "training_id": training.id,
            "destination": destination,
        })

    except Exception as e:
        print(f"[Train] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/training-status/<training_id>', methods=['GET'])
def training_status(training_id):
    """Poll training status."""
    try:
        training = replicate.trainings.get(training_id)

        result = {
            "status": training.status,
            "logs": "",
            "model_string": None,
        }

        if training.logs:
            log_lines = training.logs.strip().split('\n')
            result["logs"] = '\n'.join(log_lines[-20:])

        if training.status == "succeeded":
            output = getattr(training, "output", None) or {}
            version_str = output.get("version") if isinstance(output, dict) else None
            result["model_string"] = version_str

        if training.status == "failed":
            result["error"] = str(getattr(training, "error", "Unknown error"))

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/debug/trainings', methods=['GET'])
def debug_trainings():
    """Dump raw training data to figure out available fields."""
    try:
        trainings = replicate.trainings.list()
        results = []
        for t in trainings:
            if "ostris/flux-dev-lora-trainer" in t.model:
                raw = {}
                for attr in dir(t):
                    if attr.startswith('_'):
                        continue
                    try:
                        val = getattr(t, attr)
                        if callable(val):
                            continue
                        raw[attr] = str(val)
                    except Exception:
                        pass
                results.append(raw)
        return jsonify({"trainings": results})
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


GENERATION_PROMPT_SYSTEM = """You are an expert prompt engineer for Flux, a state-of-the-art AI image generation model fine-tuned with LoRA. Your goal is to produce ad-ready, commercial-grade marketing imagery.

Analyze the provided sample image of a product. Your job is to craft a detailed, optimized prompt that will produce a stunning, photorealistic, professional advertisement image — the kind you'd see in a Nike, Apple, or luxury brand campaign.

Critical requirements:
- The image MUST feature a real-looking human or avatar naturally interacting with, wearing, holding, or using the product — this is an advertisement, not a product-only shot
- Choose an appropriate lifestyle context: someone using the product in a real-world scenario (street, studio, gym, outdoors, workspace, etc.)
- The person should look natural, aspirational, and on-brand for the product category

Prompt guidelines:
- Write a single detailed prompt paragraph (no bullet points)
- Describe the product from the image accurately and how the person is interacting with it
- Specify the model/person: age range, style, pose, expression, wardrobe
- Include cinematic lighting details: golden hour, studio softbox, natural window light, etc.
- Specify camera: shot on Canon EOS R5, 85mm lens, shallow depth of field, etc.
- Include environment and mood: aspirational, energetic, luxurious, minimal, urban, etc.
- If a trigger word is provided, include it naturally in the prompt to activate the LoRA style
- Include quality boosters: "8k uhd", "award-winning advertising photography", "editorial", "sharp focus", "professional color grading"
- Keep it under 250 words
- Do NOT include negative prompts — just the positive prompt

Respond with ONLY the prompt text, nothing else. No quotes, no labels, no explanation."""


@app.route('/api/generate-prompt', methods=['POST'])
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

        img = Image.open(filepath)

        user_input = GENERATION_PROMPT_SYSTEM
        if trigger_word:
            user_input += f"\n\nIMPORTANT: Include this trigger word in the prompt: {trigger_word}"

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content([user_input, img])
        generated_prompt = response.text.strip()

        print(f"[PromptGen] Trigger: {trigger_word}")
        print(f"[PromptGen] Output: {generated_prompt}")

        return jsonify({"prompt": generated_prompt})

    except Exception as e:
        print(f"[PromptGen] Error: {e}")
        return jsonify({"error": str(e)}), 500


UPSCALER_PROMPT_SYSTEM = """You are an image enhancement specialist. Analyze the provided image and generate a prompt and negative_prompt for an AI upscaler to enhance this image with maximum realism.

Your goals for the prompt:
- Increase photorealism and natural appearance
- Reduce excessive contrast and saturation
- Remove any plastic, artificial, or CGI-looking skin
- Add realistic skin texture, pores, and natural imperfections
- Preserve the original composition and subject matter
- Enhance lighting to look natural and photographed

Respond ONLY with valid JSON in this exact format, no other text:
{"prompt": "your enhancement prompt here", "negative_prompt": "your negative prompt here"}"""


def generate_upscale_prompts(image_path):
    """Use Gemini to analyze the image and generate upscaler prompts."""
    model = genai.GenerativeModel("gemini-2.0-flash")
    img = Image.open(image_path)

    response = model.generate_content([UPSCALER_PROMPT_SYSTEM, img])
    text = response.text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    parsed = json.loads(text)
    return parsed["prompt"], parsed["negative_prompt"]


@app.route('/api/upscale', methods=['POST'])
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


@app.route('/api/images/<filename>', methods=['GET'])
def serve_image(filename):
    """Serve a generated image."""
    filepath = os.path.join(GENERATED_FOLDER, secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "Image not found"}), 404
    return send_file(filepath, mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
