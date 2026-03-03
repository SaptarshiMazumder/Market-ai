import os
import requests

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")


def _headers():
    return {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }


def submit_job(
    endpoint_id: str,
    image_url: str,
    object_name: str,
    seed: int | None = None,
    mask_dilation: int | None = None,
    mask_blur: int | None = None,
) -> str:
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

    r = requests.post(
        f"https://api.runpod.ai/v2/{endpoint_id}/run",
        headers=_headers(),
        json={"input": job_input},
    )
    r.raise_for_status()
    return r.json()["id"]


def get_job_status(endpoint_id: str, job_id: str) -> dict:
    r = requests.get(
        f"https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}",
        headers=_headers(),
    )
    r.raise_for_status()
    return r.json()
