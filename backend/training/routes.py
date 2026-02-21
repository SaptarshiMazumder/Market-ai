import os
import uuid
import threading

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
import replicate

from services.replicate_models import ensure_model_exists
from services.gcs import upload_weights
from models.trained_model import list_models, create_model, set_model_url, get_model_by_training_id

UPLOAD_FOLDER = 'uploads'
FLUX_TRAINER_MODEL = "ostris/flux-dev-lora-trainer"
FLUX_TRAINER_VERSION = "e440909d3512c31646ee2e0c7d6f6f4923224863a6a10c494606e79fb5844497"

training_bp = Blueprint('training', __name__)


def _upload_and_save(replicate_training_id, model_name, version_hash, weights_url):
    """Background thread: upload weights to GCS, then update SQLite."""
    def _run():
        try:
            gcs_url = upload_weights(model_name, version_hash, weights_url)
            set_model_url(replicate_training_id, gcs_url)
            print(f"[Train] Model URL saved to DB: {gcs_url}")
        except Exception as e:
            print(f"[Train] Background upload failed: {e}")
    threading.Thread(target=_run, daemon=True).start()


@training_bp.route('/api/models', methods=['GET'])
def get_models():
    """Return all trained models from SQLite."""
    try:
        return jsonify({"models": list_models()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@training_bp.route('/api/train', methods=['POST'])
def start_training():
    """Start a Flux LoRA training job and create a DB record."""
    try:
        model_name = request.form.get('model_name')
        trigger_word = request.form.get('trigger_word', 'TOK')
        zip_file = request.files.get('images')

        if not model_name or not zip_file:
            return jsonify({"error": "model_name and images (zip) are required"}), 400

        filename = f"{uuid.uuid4()}_{secure_filename(zip_file.filename)}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        zip_file.save(filepath)

        destination, _ = ensure_model_exists(model_name)

        print(f"[Train] Starting training: {destination}, trigger: {trigger_word}")

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

        # Persist the pending training to SQLite immediately
        create_model(
            name=model_name,
            trigger_word=trigger_word,
            replicate_training_id=training.id,
        )

        print(f"[Train] Training started: {training.id}")
        return jsonify({"training_id": training.id, "destination": destination})

    except Exception as e:
        print(f"[Train] Error: {e}")
        return jsonify({"error": str(e)}), 500


@training_bp.route('/api/training-status/<training_id>', methods=['GET'])
def training_status(training_id):
    """
    Poll Replicate for training status.
    On first success: uploads weights to GCS and updates SQLite.
    """
    try:
        training = replicate.trainings.get(training_id)

        result = {
            "status": training.status,
            "logs": "",
            "model_string": None,
        }

        if training.logs:
            result["logs"] = '\n'.join(training.logs.strip().split('\n')[-20:])

        if training.status == "succeeded":
            output = getattr(training, "output", None) or {}
            version_str = output.get("version") if isinstance(output, dict) else None
            weights_url = output.get("weights") if isinstance(output, dict) else None

            result["model_string"] = version_str

            # Kick off GCS upload + DB update only if not already done
            db_record = get_model_by_training_id(training_id)
            if db_record and db_record.get("model_string") is None and version_str and weights_url:
                destination, version_hash = version_str.split(":") if ":" in version_str else (version_str, "unknown")
                model_name = destination.split("/")[-1] if "/" in destination else destination
                _upload_and_save(training_id, model_name, version_hash, weights_url)

        if training.status == "failed":
            result["error"] = str(getattr(training, "error", "Unknown error"))

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@training_bp.route('/api/debug/trainings', methods=['GET'])
def debug_trainings():
    """Dump raw Replicate training data."""
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
