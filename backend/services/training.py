import replicate
from models.product import update_training, update_training_status, get_product

FLUX_DEV_LORA_MODEL = "ostris/flux-dev-lora-trainer"
FLUX_DEV_LORA_VERSION = "e440909d3512c31646ee2e0c7d6f6f4923224863a6a10c494606e79fb5844497"  # Update this with the latest version if needed


def start_training(product_name, zip_url, destination_model):
    """
    Kick off LoRA fine-tuning on ostris/flux-dev-lora-trainer.
    Returns training_id for polling.
    """
    trigger_word = f"TOK_{product_name.upper().replace(' ', '').replace('-', '')}"

    print(f"[Training] Starting LoRA training for '{product_name}'")
    print(f"[Training] Trigger word: {trigger_word}")
    print(f"[Training] Training data: {zip_url}")
    print(f"[Training] Destination: {destination_model}")

    training = replicate.trainings.create(
        model=FLUX_DEV_LORA_MODEL,
        version=FLUX_DEV_LORA_VERSION,
        input={
            "input_images": zip_url,
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
        destination=destination_model
    )

    training_id = training.id
    print(f"[Training] Training started with ID: {training_id}")

    # Save training info to database
    update_training(product_name, training_id, trigger_word)

    return training_id, trigger_word


def poll_training_status(training_id):
    """
    Check training status. Returns dict with status, logs, version_id (when done).
    """
    training = replicate.trainings.get(training_id)

    result = {
        "status": training.status,  # "starting" | "processing" | "succeeded" | "failed" | "canceled"
        "logs": "",
        "version_id": None
    }

    # Get last portion of logs
    if training.logs:
        log_lines = training.logs.strip().split('\n')
        result["logs"] = '\n'.join(log_lines[-20:])  # Last 20 lines

    if training.status == "succeeded":
        # Extract version ID from training output
        version_id = None
        if hasattr(training, 'output') and training.output:
            version_id = training.output.get("version")

        if not version_id and hasattr(training, 'version'):
            version_id = str(training.version)

        result["version_id"] = version_id
        update_training_status(training_id, "succeeded", version_id)
        print(f"[Training] Training {training_id} succeeded! Version: {version_id}")

    elif training.status == "failed":
        update_training_status(training_id, "failed", None)
        print(f"[Training] Training {training_id} failed.")
        if training.error:
            result["error"] = str(training.error)

    elif training.status == "canceled":
        update_training_status(training_id, "canceled", None)

    return result
