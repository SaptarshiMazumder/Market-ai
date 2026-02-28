import os
import requests

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_VIDEO_ENDPOINT_ID = os.environ.get("RUNPOD_VIDEO_ENDPOINT_ID", "")

BASE_URL = f"https://api.runpod.ai/v2/{RUNPOD_VIDEO_ENDPOINT_ID}"


def _headers():
    return {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }


def submit_job(image_url: str,
               prompt: str | None = None,
               width: int | None = None,
               height: int | None = None,
               length: int | None = None,
               steps: int | None = None,
               seed: int | None = None) -> str:
    job_input = {
        "image_url": image_url,
    }
    if prompt is not None:
        job_input["prompt"] = prompt
    if width is not None:
        job_input["width"] = width
    if height is not None:
        job_input["height"] = height
    if length is not None:
        job_input["length"] = length
    if steps is not None:
        job_input["steps"] = steps
    if seed is not None:
        job_input["seed"] = seed

    r = requests.post(f"{BASE_URL}/run", headers=_headers(), json={"input": job_input})
    r.raise_for_status()
    return r.json()["id"]


def get_job_status(job_id: str) -> dict:
    r = requests.get(f"{BASE_URL}/status/{job_id}", headers=_headers())
    r.raise_for_status()
    return r.json()
