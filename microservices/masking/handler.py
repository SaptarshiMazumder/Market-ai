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

WORKFLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FlorenceSegmentationMaskingAPI.json")

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_INPUT_DIR = "/comfyui/input"

R2_BUCKET = os.environ.get("R2_BUCKET", "")
R2_INPUT_BUCKET = os.environ.get("R2_INPUT_BUCKET", R2_BUCKET)
R2_OUTPUT_BUCKET = os.environ.get("R2_OUTPUT_BUCKET", R2_BUCKET)

DISPLAY_NODE_CLASSES = {
    "PreviewImage",
}


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
    raise TimeoutError("ComfyUI failed to start within the timeout period")


def _parse_r2_ref(url: str):
    """Return (bucket, key) from an r2:// URL, bare key, or https:// R2 endpoint URL."""
    if url.startswith("r2://"):
        parts = url[5:].split("/", 1)
        return parts[0], parts[1]
    if url.startswith("https://") and "r2.cloudflarestorage.com" in url:
        path = url.split("r2.cloudflarestorage.com/", 1)[1]
        bucket, key = path.split("/", 1)
        return bucket, key
    return R2_INPUT_BUCKET, url


def download_to_input(image_ref: str, dest_filename: str) -> str:
    """Download an image from R2 (or any https:// URL) into ComfyUI's input directory."""
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    dest = os.path.join(COMFYUI_INPUT_DIR, dest_filename)
    tmp_path = f"/tmp/dl_{dest_filename}"

    if image_ref.startswith("https://") and "r2.cloudflarestorage.com" not in image_ref:
        print(f"Downloading {image_ref} via HTTP")
        r = requests.get(image_ref, timeout=60)
        r.raise_for_status()
        with open(tmp_path, "wb") as f:
            f.write(r.content)
    else:
        bucket, key = _parse_r2_ref(image_ref)
        print(f"Downloading s3://{bucket}/{key} from R2")
        _r2_client().download_file(bucket, key, tmp_path)

    shutil.copy(tmp_path, dest)
    os.remove(tmp_path)
    print(f"Image ready at {dest}")
    return dest_filename


def _strip_display_nodes(workflow: dict) -> dict:
    """Remove display-only nodes so missing custom nodes don't abort the job."""
    to_remove = [
        node_id
        for node_id, node in workflow.items()
        if node.get("class_type") in DISPLAY_NODE_CLASSES
    ]
    for node_id in to_remove:
        print(f"Stripping display node {node_id} ({workflow[node_id]['class_type']})")
        del workflow[node_id]
    return workflow


def build_workflow(image_filename: str, object_name: str, seed: int) -> dict:
    with open(WORKFLOW_PATH) as f:
        workflow = copy.deepcopy(json.load(f))

    # Input image — LoadImage node 83
    workflow["83"]["inputs"]["image"] = image_filename

    # Object to detect — Florence2Run node 87
    workflow["87"]["inputs"]["text_input"] = object_name
    workflow["87"]["inputs"]["seed"] = seed

    return _strip_display_nodes(workflow)


def queue_workflow(workflow: dict) -> str:
    r = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
    r.raise_for_status()
    return r.json()["prompt_id"]


def wait_for_job(prompt_id: str, timeout: int = 300) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
        history = r.json()
        if prompt_id in history:
            job = history[prompt_id]
            status = job.get("status", {})
            if status.get("status_str") == "error":
                messages = status.get("messages", [])
                raise RuntimeError(f"ComfyUI job failed: {messages}")
            return job
        time.sleep(2)
    raise TimeoutError(f"Job {prompt_id} timed out after {timeout}s")


def upload_images_to_r2(history: dict) -> list:
    """Fetch generated images from ComfyUI's SaveImage node and upload to R2."""
    client = _r2_client()
    results = []

    save_node_output = history["outputs"].get("109", {})
    for img in save_node_output.get("images", []):
        r = requests.get(
            f"{COMFYUI_URL}/view",
            params={
                "filename": img["filename"],
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output"),
            },
            timeout=60,
        )
        r.raise_for_status()

        key = f"masks/{uuid.uuid4()}_{img['filename']}"
        client.put_object(
            Bucket=R2_OUTPUT_BUCKET,
            Key=key,
            Body=r.content,
            ContentType="image/png",
        )
        print(f"Uploaded result to R2: {R2_OUTPUT_BUCKET}/{key}")
        results.append({
            "r2_path": f"r2://{R2_OUTPUT_BUCKET}/{key}",
            "key": key,
            "filename": img["filename"],
        })
    return results


def handler(job):
    job_input = job["input"]

    image_url = job_input.get("image_url")
    object_name = job_input.get("object_name")
    seed = job_input.get("seed")

    if not image_url:
        return {"error": "image_url is required"}
    if not object_name:
        return {"error": "object_name is required (e.g. 'headphone', 'shoe', 'bottle')"}

    seed = random.randint(0, 2**32 - 1) if seed is None else int(seed)

    start_time = time.time()

    image_filename = download_to_input(image_url, "input_image.png")

    workflow = build_workflow(image_filename, object_name, seed)

    prompt_id = queue_workflow(workflow)
    print(f"Queued workflow prompt_id={prompt_id}")

    history = wait_for_job(prompt_id)
    images = upload_images_to_r2(history)

    duration = round(time.time() - start_time, 2)
    return {
        "images": images,
        "params": {"object_name": object_name, "seed": seed},
        "duration_seconds": duration,
    }


print("Waiting for ComfyUI to be ready...")
wait_for_comfyui()
print("ComfyUI is ready. Starting RunPod serverless handler.")

runpod.serverless.start({"handler": handler})
