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

WORKFLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Flux2Klein9bInpaintingAPI.json")

COMFYUI_URL = "http://127.0.0.1:8188"
COMFYUI_INPUT_DIR = "/comfyui/input"

R2_BUCKET = os.environ.get("R2_BUCKET", "")
R2_INPUT_BUCKET = os.environ.get("R2_INPUT_BUCKET", R2_BUCKET)
R2_OUTPUT_BUCKET = os.environ.get("R2_OUTPUT_BUCKET", R2_BUCKET)

# Nodes that are display-only (no downstream consumers).
# Strip these before queuing so missing custom nodes don't break the job.
DISPLAY_NODE_CLASSES = {
    "Image Comparer (rgthree)",
    "MaskPreview",
    "MaskPreview+",
    "ImageAndMaskPreview",
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
        # https://<account>.r2.cloudflarestorage.com/<bucket>/<key>
        path = url.split("r2.cloudflarestorage.com/", 1)[1]
        bucket, key = path.split("/", 1)
        return bucket, key
    # Bare key — use the default input bucket
    return R2_INPUT_BUCKET, url


def download_to_input(image_ref: str, dest_filename: str) -> str:
    """Download an image from R2 (or any https:// URL) into ComfyUI's input directory."""
    os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
    dest = os.path.join(COMFYUI_INPUT_DIR, dest_filename)
    tmp_path = f"/tmp/dl_{dest_filename}"

    if image_ref.startswith("https://") and "r2.cloudflarestorage.com" not in image_ref:
        # Generic HTTPS URL — download directly
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


def build_workflow(scene_filename: str, reference_filename: str, prompt: str, seed: int,
                   steps: int = 4, denoise: float = 1.0, guidance: float = 4.0) -> dict:
    with open(WORKFLOW_PATH) as f:
        workflow = copy.deepcopy(json.load(f))

    # Scene image (PNG with mask encoded in red channel) — LoadImage node 151
    workflow["151"]["inputs"]["image"] = scene_filename

    # Product / reference image — LoadImage node 121
    workflow["121"]["inputs"]["image"] = reference_filename

    # Positive prompt — CLIPTextEncode node 107
    workflow["107"]["inputs"]["text"] = prompt

    # LanPaint_KSampler node 156
    workflow["156"]["inputs"]["seed"] = seed
    workflow["156"]["inputs"]["steps"] = steps
    workflow["156"]["inputs"]["denoise"] = denoise

    # FluxGuidance node 100
    workflow["100"]["inputs"]["guidance"] = guidance

    return _strip_display_nodes(workflow)


def queue_workflow(workflow: dict) -> str:
    r = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
    r.raise_for_status()
    return r.json()["prompt_id"]


def wait_for_job(prompt_id: str, timeout: int = 600) -> dict:
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

    save_node_output = history["outputs"].get("9", {})
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

        key = f"generated/{uuid.uuid4()}_{img['filename']}"
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

    scene_url = job_input.get("scene_url")         # masked scene image (mask in red channel)
    reference_url = job_input.get("reference_url") # product / reference image
    prompt = job_input.get("prompt", "product on a surface")
    seed = job_input.get("seed")
    steps = job_input.get("steps", 4)
    denoise = job_input.get("denoise", 1.0)
    guidance = job_input.get("guidance", 4.0)

    if not scene_url:
        return {"error": "scene_url is required (masked scene PNG with mask in red channel)"}
    if not reference_url:
        return {"error": "reference_url is required (product/reference image)"}

    seed = random.randint(0, 2**32 - 1) if seed is None else int(seed)
    steps = int(steps)
    denoise = float(denoise)
    guidance = float(guidance)

    start_time = time.time()

    scene_filename = download_to_input(scene_url, "masked_scene.png")
    reference_filename = download_to_input(reference_url, "reference_image.jpg")

    workflow = build_workflow(scene_filename, reference_filename, prompt, seed, steps, denoise, guidance)

    prompt_id = queue_workflow(workflow)
    print(f"Queued workflow prompt_id={prompt_id}")

    history = wait_for_job(prompt_id)
    images = upload_images_to_r2(history)

    duration = round(time.time() - start_time, 2)
    return {
        "images": images,
        "params": {"prompt": prompt, "seed": seed, "steps": steps, "denoise": denoise, "guidance": guidance},
        "duration_seconds": duration,
    }


# ComfyUI is started by /start.sh in the base image — wait for it to be ready
print("Waiting for ComfyUI to be ready...")
wait_for_comfyui()
print("ComfyUI is ready. Starting RunPod serverless handler.")

runpod.serverless.start({"handler": handler})
