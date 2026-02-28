import os
import requests

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_INPAINTING_ENDPOINT_ID = os.environ.get("RUNPOD_INPAINTING_ENDPOINT_ID", "")

BASE_URL = f"https://api.runpod.ai/v2/{RUNPOD_INPAINTING_ENDPOINT_ID}"


def _headers():
    return {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }


def submit_job(scene_url: str, reference_url: str,
               prompt: str | None = None,
               seed: int | None = None,
               steps: int | None = None,
               denoise: float | None = None,
               guidance: float | None = None) -> str:
    job_input = {
        "scene_url": scene_url,
        "reference_url": reference_url,
    }
    if prompt is not None:
        job_input["prompt"] = prompt
    if seed is not None:
        job_input["seed"] = seed
    if steps is not None:
        job_input["steps"] = steps
    if denoise is not None:
        job_input["denoise"] = denoise
    if guidance is not None:
        job_input["guidance"] = guidance

    r = requests.post(f"{BASE_URL}/run", headers=_headers(), json={"input": job_input})
    r.raise_for_status()
    return r.json()["id"]


def get_job_status(job_id: str) -> dict:
    r = requests.get(f"{BASE_URL}/status/{job_id}", headers=_headers())
    r.raise_for_status()
    return r.json()
