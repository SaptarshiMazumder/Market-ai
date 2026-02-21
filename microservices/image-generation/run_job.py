import os
import sys
import json
import time
import requests
from pathlib import Path

# --- Load .env if present ---
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# --- Config ---
API_KEY = os.environ.get("RUNPOD_API_KEY")
ENDPOINT_ID = "zotmmnshs1nxix"
WORKFLOW_PATH = os.path.join(os.path.dirname(__file__), "LoraWorkflow.json")

if not API_KEY:
    print("Error: RUNPOD_API_KEY environment variable not set.")
    sys.exit(1)

BASE_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def submit_job(lora_key: str, workflow: dict) -> str:
    payload = {
        "input": {
            "lora_key": lora_key,
            "workflow": workflow,
        }
    }
    r = requests.post(f"{BASE_URL}/run", headers=HEADERS, json=payload)
    r.raise_for_status()
    job_id = r.json()["id"]
    print(f"Job submitted: {job_id}")
    return job_id


def poll_job(job_id: str, interval: int = 10) -> dict:
    print("Polling for result", end="", flush=True)
    while True:
        r = requests.get(f"{BASE_URL}/status/{job_id}", headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        status = data["status"]

        if status == "COMPLETED":
            print(" done.")
            return data
        elif status == "FAILED":
            print(" failed.")
            print("Error:", data.get("error"))
            sys.exit(1)
        else:
            print(".", end="", flush=True)
            time.sleep(interval)


def print_results(output: dict):
    images = output.get("images", [])
    if not images:
        print("No images in output.")
        return
    for img in images:
        print(f"  r2_path : {img.get('r2_path')}")
        print(f"  filename: {img.get('filename')}")


if __name__ == "__main__":
    # Pass the R2 key of the trained LoRA, e.g.:
    #   python run_job.py myModel.safetensors
    # or the full r2:// path returned by the training job:
    #   python run_job.py r2://test-ftp/myModel.safetensors
    lora_key = sys.argv[1] if len(sys.argv) > 1 else "myModel.safetensors"

    with open(WORKFLOW_PATH) as f:
        workflow = json.load(f)

    job_id = submit_job(lora_key, workflow)
    result = poll_job(job_id)
    print_results(result.get("output", {}))
