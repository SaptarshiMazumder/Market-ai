import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("RUNPOD_API_KEY")
ENDPOINT_ID = os.environ.get("ENDPOINT_ID")

if not API_KEY or not ENDPOINT_ID:
    print("Error: RUNPOD_API_KEY and ENDPOINT_ID must be set in .env")
    sys.exit(1)

BASE_URL = f"https://api.runpod.ai/v2/{ENDPOINT_ID}"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def submit_job(config: dict) -> str:
    payload = {"input": config}
    r = requests.post(f"{BASE_URL}/run", headers=HEADERS, json=payload)
    r.raise_for_status()
    job_id = r.json()["id"]
    print(f"Job submitted: {job_id}")
    return job_id


def poll_job(job_id: str, interval: int = 30) -> dict:
    print("Polling for result", end="", flush=True)
    while True:
        r = requests.get(f"{BASE_URL}/status/{job_id}", headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        status = data["status"]

        if status == "COMPLETED":
            print(" done!")
            return data
        elif status == "FAILED":
            print(" failed.")
            print("Error:", data.get("error"))
            sys.exit(1)
        else:
            print(f" [{status}]", end="", flush=True)
            time.sleep(interval)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"
    print(f"Mode: {mode}")

    config = {
        "dataset_url": "https://storage.googleapis.com/train-loras/dataset.zip",
        "lora_name": "myProd_v2",
        "trigger_word": "MY_PROD",
    }

    if mode == "test":
        config.update({"lora_name": "test_run", "steps": 1, "save_every": 1, "sample_every": 9999})

    job_id = submit_job(config)
    result = poll_job(job_id)
    output = result.get("output", {})
    print(f"\nUploaded to: {output.get('r2_path')}")
