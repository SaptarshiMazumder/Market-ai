import os
import requests

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
RUNPOD_IMAGE_ENDPOINT_ID = os.environ.get("RUNPOD_IMAGE_ENDPOINT_ID", "zotmmnshs1nxix")

BASE_URL = f"https://api.runpod.ai/v2/{RUNPOD_IMAGE_ENDPOINT_ID}"


def _headers():
    return {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }


def submit_job(lora_key: str, prompt: str, width: int, height: int,
               steps: int, lora_scale: float, seed: int | None = None,
               guidance_scale: float | None = None,
               negative_prompt: str | None = None) -> str:
    """Submit an image generation job to RunPod. Returns job_id."""
    job_input = {
        "lora_key": lora_key,
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": steps,
        "lora_scale": lora_scale,
    }
    if seed is not None:
        job_input["seed"] = seed
    if guidance_scale is not None:
        job_input["guidance_scale"] = guidance_scale
    if negative_prompt is not None:
        job_input["negative_prompt"] = negative_prompt

    r = requests.post(f"{BASE_URL}/run", headers=_headers(), json={"input": job_input})
    r.raise_for_status()
    return r.json()["id"]


def get_job_status(job_id: str) -> dict:
    """Poll RunPod for job status. Returns full status dict."""
    r = requests.get(f"{BASE_URL}/status/{job_id}", headers=_headers())
    r.raise_for_status()
    return r.json()
