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
    lora_name: str,
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    lora_strength: float = 1.0,
    upscale_lora_strength: float = 0.6,
    seed: int | None = None,
) -> str:
    job_input = {
        "prompt": prompt,
        "lora_name": lora_name,
        "width": width,
        "height": height,
        "lora_strength": lora_strength,
        "upscale_lora_strength": upscale_lora_strength,
        "seed": seed if seed is not None else 42,
    }

    base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
    r = requests.post(f"{base_url}/run", headers=_headers(), json={"input": job_input})
    r.raise_for_status()
    return r.json()["id"]


def get_job_status(endpoint_id: str, job_id: str) -> dict:
    base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
    r = requests.get(f"{base_url}/status/{job_id}", headers=_headers())
    r.raise_for_status()
    return r.json()
