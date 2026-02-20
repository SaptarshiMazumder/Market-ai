import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
import replicate

from services.replicate_models import ensure_model_exists

UPLOAD_FOLDER = 'uploads'
FLUX_TRAINER_MODEL = "ostris/flux-dev-lora-trainer"
FLUX_TRAINER_VERSION = "e440909d3512c31646ee2e0c7d6f6f4923224863a6a10c494606e79fb5844497"

training_bp = Blueprint('training', __name__)


@training_bp.route('/api/models', methods=['GET'])
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
                # Extract trigger word from training input
                training_input = getattr(t, "input", {}) or {}
                if isinstance(training_input, dict):
                    entry["trigger_word"] = training_input.get("trigger_word", "")

                if t.status == "succeeded" and output_version:
                    entry["model_string"] = output_version
                    entry["version"] = output_version.split(":")[-1] if ":" in output_version else None
                models.append(entry)

        return jsonify({"models": models})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@training_bp.route('/api/train', methods=['POST'])
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


@training_bp.route('/api/training-status/<training_id>', methods=['GET'])
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


@training_bp.route('/api/debug/trainings', methods=['GET'])
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
