import runpod
import requests
import os
import json
import copy
import time
import random
import uuid
import shutil
import boto3
from botocore.config import Config

WORKFLOW_PATH = os.path.join(os.path.dirname(__file__), "workflow-api-C6gm9qJqfnksxkb0xKgFK.json")

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_INPUT_DIR = "/comfyui/input"

R2_INPUT_BUCKET = os.environ.get("R2_INPUT_BUCKET", "objects-to-train")
R2_OUTPUT_BUCKET = os.environ.get("R2_OUTPUT_BUCKET", "test-ftp")


def _r2_client():
    account_id = os.environ["R2_ACCOUNT_ID"].strip()
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"].strip(),
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"].strip(),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def wait_for_comfyui(timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(f"{COMFYUI_URL}/system_stats", timeout=2)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError("ComfyUI failed to start in time")


def download_image(image_url: str) -> str:
    """Download image from R2 into ComfyUI input dir as input.jpg."""
    if image_url.startswith("r2://"):
        parts = image_url[5:].split("/", 1)
        bucket, key = parts[0], parts[1]
    else:
        bucket = R2_INPUT_BUCKET
        key = image_url

    ext = os.path.splitext(key)[1] or ".jpg"
    tmp_path = f"/tmp/input_image{ext}"
    dest = os.path.join(COMFYUI_INPUT_DIR, "input.jpg")

    print(f"Downloading image from R2: bucket={bucket} key={key}")
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    _r2_client().download_file(bucket, key, tmp_path)
    shutil.copy(tmp_path, dest)
    print(f"Image ready at {dest}")
    return "input.jpg"


def build_workflow(prompt: str, seed: int, width: int, height: int, length: int, steps: int) -> dict:
    with open(WORKFLOW_PATH) as f:
        workflow = copy.deepcopy(json.load(f))

    # Inject positive prompt
    workflow["6"]["inputs"]["text"] = prompt

    # Inject resolution and frame count
    workflow["63"]["inputs"]["width"] = width
    workflow["63"]["inputs"]["height"] = height
    workflow["63"]["inputs"]["length"] = length

    # Inject steps into both samplers
    workflow["57"]["inputs"]["steps"] = steps
    workflow["57"]["inputs"]["end_at_step"] = steps // 2
    workflow["58"]["inputs"]["steps"] = steps
    workflow["58"]["inputs"]["start_at_step"] = steps // 2

    # Inject seed into the high-noise sampler (node 57)
    workflow["57"]["inputs"]["noise_seed"] = seed

    return workflow


def queue_workflow(workflow):
    r = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
    r.raise_for_status()
    return r.json()["prompt_id"]


def wait_for_job(prompt_id, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        history = r.json()
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Job {prompt_id} timed out")


def upload_video_to_r2(history) -> list:
    """Fetch generated video from ComfyUI, upload to R2, return list of r2_paths."""
    client = _r2_client()
    results = []
    for node_output in history["outputs"].values():
        for vid in node_output.get("gifs", []):
            r = requests.get(
                f"{COMFYUI_URL}/view",
                params={
                    "filename": vid["filename"],
                    "subfolder": vid.get("subfolder", ""),
                    "type": vid.get("type", "output"),
                },
            )
            r.raise_for_status()
            key = f"generated/{uuid.uuid4()}_{vid['filename']}"
            client.put_object(
                Bucket=R2_OUTPUT_BUCKET,
                Key=key,
                Body=r.content,
                ContentType="video/mp4",
            )
            print(f"Uploaded video to R2: {key}")
            results.append({
                "r2_path": f"r2://{R2_OUTPUT_BUCKET}/{key}",
                "filename": vid["filename"],
            })
    return results


def handler(job):
    job_input = job["input"]
    image_url = job_input.get("image_url")
    prompt = job_input.get("prompt", "A person stands confidently, the camera slowly circles around them.")
    width = int(job_input.get("width", 832))
    height = int(job_input.get("height", 480))
    length = int(job_input.get("length", 33))
    steps = int(job_input.get("steps", 20))
    seed = job_input.get("seed")
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    else:
        seed = int(seed)

    if not image_url:
        return {"error": "image_url is required"}

    start_time = time.time()

    download_image(image_url)
    workflow = build_workflow(prompt, seed, width, height, length, steps)

    prompt_id = queue_workflow(workflow)
    print(f"Queued workflow: {prompt_id}")

    history = wait_for_job(prompt_id)
    videos = upload_video_to_r2(history)

    duration = round(time.time() - start_time, 2)

    return {
        "videos": videos,
        "params": {
            "prompt": prompt,
            "seed": seed,
        },
        "duration_seconds": duration,
    }


# ComfyUI is started by the base image — wait for it to be ready
print("Waiting for ComfyUI to be ready...")
wait_for_comfyui()
print("ComfyUI ready.")

runpod.serverless.start({"handler": handler})
