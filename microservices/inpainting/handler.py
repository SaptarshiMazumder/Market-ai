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

WORKFLOW_PATH = os.path.join(os.path.dirname(__file__), "Flux2Klein9bInpaintingAPI.json")

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


def download_to_input(image_url: str, dest_filename: str) -> str:
    """Download an image from R2 into ComfyUI's input directory."""
    if image_url.startswith("r2://"):
        parts = image_url[5:].split("/", 1)
        bucket, key = parts[0], parts[1]
    else:
        bucket = R2_INPUT_BUCKET
        key = image_url

    tmp_path = f"/tmp/dl_{dest_filename}"
    dest = os.path.join(COMFYUI_INPUT_DIR, dest_filename)

    print(f"Downloading {key} from R2 bucket {bucket}")
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    _r2_client().download_file(bucket, key, tmp_path)
    shutil.copy(tmp_path, dest)
    print(f"Ready at {dest}")
    return dest_filename


def build_workflow(scene_filename: str, reference_filename: str, prompt: str, seed: int) -> dict:
    with open(WORKFLOW_PATH) as f:
        workflow = copy.deepcopy(json.load(f))

    # Scene image (with alpha mask) — LoadImage node 151
    workflow["151"]["inputs"]["image"] = scene_filename

    # Reference image — LoadImage node 121
    workflow["121"]["inputs"]["image"] = reference_filename

    # Positive prompt — CLIPTextEncode node 107
    workflow["107"]["inputs"]["text"] = prompt

    # Seed — LanPaint_KSampler node 156
    workflow["156"]["inputs"]["seed"] = seed

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


def upload_images_to_r2(history) -> list:
    """Fetch generated images from ComfyUI, upload to R2, return list of r2_paths."""
    client = _r2_client()
    results = []
    # Only collect from node 9 (SaveImage) — other nodes output temp/preview images
    save_node_output = history["outputs"].get("9", {})
    for img in save_node_output.get("images", []):
        r = requests.get(
            f"{COMFYUI_URL}/view",
            params={
                "filename": img["filename"],
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output"),
            },
        )
        r.raise_for_status()
        key = f"generated/{uuid.uuid4()}_{img['filename']}"
        client.put_object(
            Bucket=R2_OUTPUT_BUCKET,
            Key=key,
            Body=r.content,
            ContentType="image/png",
        )
        print(f"Uploaded to R2: {key}")
        results.append({
            "r2_path": f"r2://{R2_OUTPUT_BUCKET}/{key}",
            "filename": img["filename"],
        })
    return results


def handler(job):
    job_input = job["input"]

    scene_url = job_input.get("scene_url")
    reference_url = job_input.get("reference_url")
    prompt = job_input.get("prompt", "a spray can in her hand")
    seed = job_input.get("seed")

    if not scene_url:
        return {"error": "scene_url is required"}
    if not reference_url:
        return {"error": "reference_url is required"}

    if seed is None:
        seed = random.randint(0, 2**32 - 1)
    else:
        seed = int(seed)

    start_time = time.time()

    scene_filename = download_to_input(scene_url, "masked_scene.png")
    reference_filename = download_to_input(reference_url, "reference_image.jpg")

    workflow = build_workflow(scene_filename, reference_filename, prompt, seed)

    prompt_id = queue_workflow(workflow)
    print(f"Queued workflow: {prompt_id}")

    history = wait_for_job(prompt_id)
    images = upload_images_to_r2(history)

    duration = round(time.time() - start_time, 2)

    return {
        "images": images,
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
