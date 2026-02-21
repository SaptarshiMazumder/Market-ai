import uuid
import json

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from services.r2 import upload_dataset
from services.runpod import submit_job, get_job_status
from models.trained_model import list_models, create_model, set_model_url, set_model_failed, get_model_by_job_id

training_bp = Blueprint('training', __name__)

TRAINING_DEFAULTS = {
    "steps": 2000,
    "lr": 1e-4,
    "lora_rank": 16,
    "batch_size": 2,
    "resolution": [512, 768, 1024],
}


@training_bp.route('/api/training-config', methods=['GET'])
def get_training_config():
    """Return default training config values for the UI."""
    return jsonify(TRAINING_DEFAULTS)


@training_bp.route('/api/models', methods=['GET'])
def get_models():
    """Return all trained models from SQLite."""
    try:
        return jsonify({"models": list_models()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@training_bp.route('/api/train', methods=['POST'])
def start_training():
    """Upload dataset to R2, submit RunPod training job, record in DB."""
    try:
        model_name = request.form.get('model_name')
        trigger_word = request.form.get('trigger_word', 'TOK')
        zip_file = request.files.get('images')

        if not model_name or not zip_file:
            return jsonify({"error": "model_name and images (zip) are required"}), 400

        # Optional training overrides (all have defaults in the RunPod worker)
        overrides = {}
        if request.form.get('steps'):
            overrides['steps'] = int(request.form.get('steps'))
        if request.form.get('lr'):
            overrides['lr'] = float(request.form.get('lr'))
        if request.form.get('lora_rank'):
            overrides['lora_rank'] = int(request.form.get('lora_rank'))
        if request.form.get('batch_size'):
            overrides['batch_size'] = int(request.form.get('batch_size'))
        if request.form.get('resolution'):
            overrides['resolution'] = json.loads(request.form.get('resolution'))

        key = f"{uuid.uuid4()}_{secure_filename(zip_file.filename)}"
        dataset_url = upload_dataset(key, zip_file.stream)
        print(f"[Train] Uploaded dataset to R2: {key}")

        job_id = submit_job(dataset_url, lora_name=model_name, trigger_word=trigger_word, overrides=overrides)
        print(f"[Train] RunPod job submitted: {job_id}")

        create_model(name=model_name, trigger_word=trigger_word, job_id=job_id)

        return jsonify({"job_id": job_id})

    except Exception as e:
        print(f"[Train] Error: {e}")
        return jsonify({"error": str(e)}), 500


@training_bp.route('/api/training-status/<job_id>', methods=['GET'])
def training_status(job_id):
    """Poll RunPod for job status. On completion, persist the output r2_path."""
    try:
        data = get_job_status(job_id)
        runpod_status = data.get("status")

        TERMINAL_FAILED = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}

        # Map RunPod statuses to our internal statuses
        if runpod_status == "COMPLETED":
            status = "succeeded"
        elif runpod_status in TERMINAL_FAILED:
            status = "failed"
        else:
            status = "training"  # IN_QUEUE, IN_PROGRESS, etc.

        result = {"status": status, "model_string": None}

        # Always attach DB metadata so the frontend has name + trigger_word
        db_record = get_model_by_job_id(job_id)
        if db_record:
            result["model_name"] = db_record.get("name") or db_record.get("destination")
            result["trigger_word"] = db_record.get("trigger_word")

        if runpod_status == "COMPLETED":
            output = data.get("output", {})
            r2_path = output.get("r2_path")
            result["model_string"] = r2_path

            # Persist to DB only once (when model_string not yet set)
            if db_record and db_record.get("model_string") is None and r2_path:
                set_model_url(job_id, r2_path)

        elif runpod_status in TERMINAL_FAILED:
            result["error"] = data.get("error") or f"Job {runpod_status.lower()}"
            if db_record and db_record.get("status") != "failed":
                set_model_failed(job_id)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
