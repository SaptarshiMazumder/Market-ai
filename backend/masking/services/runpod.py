import os
import requests

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_MASKING_ENDPOINT_ID = os.environ.get("RUNPOD_MASKING_ENDPOINT_ID", "")

BASE_URL = f"https://api.runpod.ai/v2/{RUNPOD_MASKING_ENDPOINT_ID}"


def _headers():
    return {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }


def submit_job(image_url: str, object_name: str,
               seed: int | None = None,
               mask_dilation: int | None = None,
               mask_blur: int | None = None) -> str:
    job_input = {
        "image_url": image_url,
        "object_name": object_name,
    }
    if seed is not None:
        job_input["seed"] = seed
    if mask_dilation is not None:
        job_input["mask_dilation"] = mask_dilation
    if mask_blur is not None:
        job_input["mask_blur"] = mask_blur

    r = requests.post(f"{BASE_URL}/run", headers=_headers(), json={"input": job_input})
    r.raise_for_status()
    return r.json()["id"]


def get_job_status(job_id: str) -> dict:
    r = requests.get(f"{BASE_URL}/status/{job_id}", headers=_headers())
    r.raise_for_status()
    return r.json()
