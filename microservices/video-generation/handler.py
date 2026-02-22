import runpod
import requests
import os
import json
import copy
import time
import uuid
import boto3
from botocore.config import Config

WORKFLOW_PATH = os.path.join(os.path.dirname(__file__), "workflow-api-C6gm9qJqfnksxkb0xKgFK.json")

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_INPUT_DIR = "/comfyui/input"

R2_INPUT_BUCKET = os.environ.get("R2_INPUT_BUCKET", "test-ftp")
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


def download_image_from_r2(image_url: str) -> str:
    """Download image from R2 into ComfyUI input dir. Returns filename."""
    if image_url.startswith("r2://"):
        parts = image_url[5:].split("/", 1)
        bucket, key = parts[0], parts[1]
    else:
        bucket = R2_INPUT_BUCKET
        key = image_url

    filename = os.path.basename(key)
    dest = os.path.join(COMFYUI_INPUT_DIR, filename)

    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    print(f"Downloading image from R2: bucket={bucket} key={key}")
    _r2_client().download_file(bucket, key, dest)
    print(f"Downloaded: {filename}")
    return filename


def build_workflow(image_filename: str, prompt: str) -> dict:
    with open(WORKFLOW_PATH) as f:
        workflow = copy.deepcopy(json.load(f))

    # Inject source image into LoadImage node
    workflow["62"]["inputs"]["image"] = image_filename

    # Inject positive prompt into CLIPTextEncode node
    workflow["6"]["inputs"]["text"] = prompt

    return workflow


def queue_workflow(workflow):
    r = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
    r.raise_for_status()
    return r.json()["prompt_id"]


def wait_for_job(prompt_id, timeout=900):
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}")
        history = r.json()
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Job {prompt_id} timed out")


def upload_video_to_r2(history) -> dict:
    """Find video in ComfyUI history outputs, upload to R2, return metadata."""
    client = _r2_client()

    for node_output in history["outputs"].values():
        # SaveVideo uses "videos" key; fall back to "gifs" or "images"
        for key in ("videos", "gifs", "images"):
            for item in node_output.get(key, []):
                r = requests.get(
                    f"{COMFYUI_URL}/view",
                    params={
                        "filename": item["filename"],
                        "subfolder": item.get("subfolder", ""),
                        "type": item.get("type", "output"),
                    },
                )
                r.raise_for_status()

                ext = os.path.splitext(item["filename"])[1] or ".mp4"
                r2_key = f"generated/videos/{uuid.uuid4()}{ext}"
                content_type = "video/mp4" if ext in (".mp4", ".mkv") else "video/webm"

                client.put_object(
                    Bucket=R2_OUTPUT_BUCKET,
                    Key=r2_key,
                    Body=r.content,
                    ContentType=content_type,
                )
                print(f"Uploaded video to R2: {r2_key}")
                return {
                    "r2_path": f"r2://{R2_OUTPUT_BUCKET}/{r2_key}",
                    "filename": item["filename"],
                }

    raise RuntimeError("No video output found in ComfyUI history")


DEFAULT_IMAGE_URL = "r2://objects-to-train/womanWCan.png"
DEFAULT_PROMPT = "A smooth cinematic product video of a woman holding a can, with subtle natural motion."


def handler(job):
    job_input = job["input"]
    image_url = job_input.get("image_url", DEFAULT_IMAGE_URL)
    prompt = job_input.get("prompt", DEFAULT_PROMPT)

    start_time = time.time()

    image_filename = download_image_from_r2(image_url)
    workflow = build_workflow(image_filename, prompt)

    prompt_id = queue_workflow(workflow)
    print(f"Queued workflow: {prompt_id}")

    history = wait_for_job(prompt_id)
    video = upload_video_to_r2(history)

    duration = round(time.time() - start_time, 2)
    return {
        "video": video,
        "params": {
            "image_url": image_url,
            "prompt": prompt,
        },
        "duration_seconds": duration,
    }


print("Waiting for ComfyUI to be ready...")
wait_for_comfyui()
print("ComfyUI ready.")

runpod.serverless.start({"handler": handler})
