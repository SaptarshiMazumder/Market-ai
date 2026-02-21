import uuid

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from services.r2 import upload_dataset
from services.runpod import submit_job, get_job_status
from models.trained_model import list_models, create_model, set_model_url, get_model_by_job_id

training_bp = Blueprint('training', __name__)


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

        key = f"{uuid.uuid4()}_{secure_filename(zip_file.filename)}"
        dataset_url = upload_dataset(key, zip_file.stream)
        print(f"[Train] Uploaded dataset to R2: {key}")

        job_id = submit_job(dataset_url, lora_name=model_name, trigger_word=trigger_word)
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

        # Map RunPod statuses to our internal statuses
        if runpod_status == "COMPLETED":
            status = "succeeded"
        elif runpod_status == "FAILED":
            status = "failed"
        else:
            status = "training"  # IN_QUEUE, IN_PROGRESS, etc.

        result = {"status": status, "model_string": None}

        if runpod_status == "COMPLETED":
            output = data.get("output", {})
            r2_path = output.get("r2_path")
            result["model_string"] = r2_path

            # Persist to DB only once (when model_string not yet set)
            db_record = get_model_by_job_id(job_id)
            if db_record and db_record.get("model_string") is None and r2_path:
                set_model_url(job_id, r2_path)

        if runpod_status == "FAILED":
            result["error"] = data.get("error", "Unknown error")

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
