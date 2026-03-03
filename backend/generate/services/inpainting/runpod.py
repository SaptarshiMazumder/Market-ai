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
    scene_url: str,
    reference_url: str,
    prompt: str = "product on a surface",
    seed: int | None = None,
    steps: int | None = None,
    denoise: float | None = None,
    guidance: float | None = None,
) -> str:
    job_input = {
        "scene_url": scene_url,
        "reference_url": reference_url,
        "prompt": prompt,
    }
    if seed is not None:
        job_input["seed"] = seed
    if steps is not None:
        job_input["steps"] = steps
    if denoise is not None:
        job_input["denoise"] = denoise
    if guidance is not None:
        job_input["guidance"] = guidance

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
