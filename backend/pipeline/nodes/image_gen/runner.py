import os
import time

import boto3
import requests
from botocore.config import Config

RUNPOD_API_KEY      = os.environ.get("RUNPOD_API_KEY", "")
LORA_ENDPOINT_ID    = "4zt599q013q0cz"
Z_TURBO_ENDPOINT_ID = "1dv4vwaqf3quge"
TERMINAL_FAILED     = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}
POLL_INTERVAL       = 5

R2_ENDPOINT_URL      = os.environ.get("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID     = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET            = os.environ.get("R2_OUTPUT_BUCKET", "")


class NodeFailed(Exception):
    pass


def _rp_headers():
    return {"Authorization": f"Bearer {RUNPOD_API_KEY}", "Content-Type": "application/json"}


def _r2_client():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def _download_r2(r2_path: str) -> bytes:
    parts = r2_path[5:].split("/", 1)
    bucket, key = parts[0], parts[1]
    resp = _r2_client().get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()


def _poll_runpod(endpoint_id: str, job_id: str) -> dict:
    while True:
        r = requests.get(
            f"https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}",
            headers=_rp_headers(),
        )
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if status == "COMPLETED":
            return data
        if status in TERMINAL_FAILED:
            raise NodeFailed(f"RunPod {status}: {data.get('error') or status}")
        time.sleep(POLL_INTERVAL)


def submit_and_fetch(
    mode: str,
    prompt: str,
    width: int,
    height: int,
    lora_name: str | None = None,
    lora_strength: float = 1.0,
    upscale_lora_strength: float = 0.6,
    seed: int | None = None,
) -> tuple[str, bytes]:
    if mode == "template":
        body = {
            "prompt": prompt,
            "lora_name": lora_name,
            "width": width,
            "height": height,
            "lora_strength": lora_strength,
            "upscale_lora_strength": upscale_lora_strength,
            "seed": seed,
        }
        endpoint = LORA_ENDPOINT_ID
    else:
        body = {"prompt": prompt, "width": width, "height": height, "seed": seed}
        endpoint = Z_TURBO_ENDPOINT_ID

    r = requests.post(
        f"https://api.runpod.ai/v2/{endpoint}/run",
        headers=_rp_headers(),
        json={"input": body},
    )
    r.raise_for_status()
    runpod_job_id = r.json()["id"]
    print(f"[ImageGen runner] job={runpod_job_id} mode={mode}")

    data = _poll_runpod(endpoint, runpod_job_id)
    images = data.get("output", {}).get("images", [])
    if not images:
        raise NodeFailed("No images returned from RunPod")

    r2_path = images[0]["r2_path"]
    return r2_path, _download_r2(r2_path)
