import os
import requests

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_ZTURBO_ENDPOINT_ID = os.environ.get("RUNPOD_ZTURBO_ENDPOINT_ID", "")

BASE_URL = f"https://api.runpod.ai/v2/{RUNPOD_ZTURBO_ENDPOINT_ID}"


def _headers():
    return {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }


def submit_job(prompt: str, width: int, height: int, steps: int,
               cfg: float, denoise: float, seed: int | None = None) -> str:
    """Submit a z-turbo image generation job to RunPod. Returns job_id."""
    job_input = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "cfg": cfg,
        "denoise": denoise,
    }
    if seed is not None:
        job_input["seed"] = seed

    r = requests.post(f"{BASE_URL}/run", headers=_headers(), json={"input": job_input})
    r.raise_for_status()
    return r.json()["id"]


def get_job_status(job_id: str) -> dict:
    """Poll RunPod for job status. Returns full status dict."""
    r = requests.get(f"{BASE_URL}/status/{job_id}", headers=_headers())
    r.raise_for_status()
    return r.json()
