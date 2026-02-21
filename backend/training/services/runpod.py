import os
import requests

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "llob5aq7bximyj")
R2_OUTPUT_BUCKET = os.environ.get("R2_OUTPUT_BUCKET", "test-ftp")

BASE_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"


def _headers():
    return {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }


def submit_job(dataset_url: str, lora_name: str, trigger_word: str) -> str:
    """Submit a training job to RunPod and return the job ID."""
    payload = {
        "input": {
            "dataset_url": dataset_url,
            "lora_name": lora_name,
            "trigger_word": trigger_word,
            "r2_bucket": R2_OUTPUT_BUCKET,
        }
    }
    r = requests.post(f"{BASE_URL}/run", headers=_headers(), json=payload)
    r.raise_for_status()
    return r.json()["id"]


def get_job_status(job_id: str) -> dict:
    """Fetch current status of a RunPod job."""
    r = requests.get(f"{BASE_URL}/status/{job_id}", headers=_headers())
    r.raise_for_status()
    return r.json()
