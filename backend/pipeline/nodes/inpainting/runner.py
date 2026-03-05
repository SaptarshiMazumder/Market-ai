import os
import time

import boto3
import requests
from botocore.config import Config

RUNPOD_API_KEY   = os.environ.get("RUNPOD_API_KEY", "")
INPAINT_ENDPOINT = "e70xck7rf5xnq4"
TERMINAL_FAILED  = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}
POLL_INTERVAL    = 5

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


def download_r2(r2_path: str) -> bytes:
    parts = r2_path[5:].split("/", 1)
    bucket, key = parts[0], parts[1]
    resp = _r2_client().get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()


_download_r2 = download_r2  # internal alias


def _poll_runpod(job_id: str) -> dict:
    while True:
        r = requests.get(
            f"https://api.runpod.ai/v2/{INPAINT_ENDPOINT}/status/{job_id}",
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
    masked_r2: str,
    product_r2: str,
    prompt: str,
    seed: int,
    steps: int,
    denoise: float = 1.0,
    guidance: float = 4.0,
    lan_paint_num_steps: int = 2,
    lan_paint_prompt_mode: str = "Image First",
) -> tuple[str, bytes]:
    job_input = {
        "scene_url": masked_r2,
        "reference_url": product_r2,
        "prompt": prompt,
        "seed": seed,
        "steps": steps,
        "denoise": denoise,
        "guidance": guidance,
        "lan_paint_num_steps": lan_paint_num_steps,
        "lan_paint_prompt_mode": lan_paint_prompt_mode,
    }
    r = requests.post(
        f"https://api.runpod.ai/v2/{INPAINT_ENDPOINT}/run",
        headers=_rp_headers(),
        json={"input": job_input},
    )
    r.raise_for_status()
    runpod_job_id = r.json()["id"]
    print(f"[Inpainting runner] job={runpod_job_id} steps={steps}")

    data = _poll_runpod(runpod_job_id)
    images = data.get("output", {}).get("images", [])
    if not images:
        raise NodeFailed("No images returned from RunPod inpainting")

    r2_path = images[0]["r2_path"]
    return r2_path, _download_r2(r2_path)
