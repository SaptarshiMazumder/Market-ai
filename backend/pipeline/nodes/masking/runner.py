import os
import time

import boto3
import requests
from botocore.config import Config

RUNPOD_API_KEY   = os.environ.get("RUNPOD_API_KEY", "")
MASKING_ENDPOINT = "05tbqu0ikzqfiy"
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
            f"https://api.runpod.ai/v2/{MASKING_ENDPOINT}/status/{job_id}",
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
    generated_r2: str,
    subject: str,
    mask_blur: int,
    mask_dilation: int,
    seed: int,
) -> tuple[str, bytes]:
    job_input = {
        "image_url": generated_r2,
        "object_name": subject,
        "seed": seed,
        "mask_blur": mask_blur,
        "mask_dilation": mask_dilation,
    }
    r = requests.post(
        f"https://api.runpod.ai/v2/{MASKING_ENDPOINT}/run",
        headers=_rp_headers(),
        json={"input": job_input},
    )
    r.raise_for_status()
    runpod_job_id = r.json()["id"]
    print(f"[Masking runner] job={runpod_job_id}")

    data = _poll_runpod(runpod_job_id)
    images = data.get("output", {}).get("images", [])
    if not images:
        raise NodeFailed("No images returned from RunPod masking")

    r2_path = images[0]["r2_path"]
    return r2_path, _download_r2(r2_path)
