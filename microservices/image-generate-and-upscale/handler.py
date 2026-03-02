import runpod
import requests
import os
import json
import copy
import time
import random
import uuid
import boto3
from botocore.config import Config

WORKFLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image_generate_and_upscale_api.json")

COMFYUI_URL = "http://127.0.0.1:8188"

R2_BUCKET = os.environ.get("R2_BUCKET", "")
R2_OUTPUT_BUCKET = os.environ.get("R2_OUTPUT_BUCKET", R2_BUCKET)


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


def build_workflow(
    prompt: str,
    seed: int,
    width: int = 832,
    height: int = 1536,
    steps: int = 8,
    cfg: float = 1.0,
    denoise: float = 1.0,
    negative_prompt: str = "",
    upscale_denoise: float = 0.8,
    scale_by: float = 1.25,
    upscale_resolution: int = 2560,
) -> dict:
    with open(WORKFLOW_PATH) as f:
        workflow = copy.deepcopy(json.load(f))

    # Prompts — CLIPTextEncode nodes 5 (positive) and 6 (negative)
    workflow["5"]["inputs"]["text"] = prompt
    workflow["6"]["inputs"]["text"] = negative_prompt

    # Image dimensions — EmptySD3LatentImage node 7
    workflow["7"]["inputs"]["width"] = width
    workflow["7"]["inputs"]["height"] = height

    # Generation KSampler — node 4
    workflow["4"]["inputs"]["seed"] = seed
    workflow["4"]["inputs"]["steps"] = steps
    workflow["4"]["inputs"]["cfg"] = cfg
    workflow["4"]["inputs"]["denoise"] = denoise

    # Latent upscale pass KSampler — node 11
    workflow["11"]["inputs"]["seed"] = seed
    workflow["11"]["inputs"]["steps"] = steps
    workflow["11"]["inputs"]["cfg"] = cfg
    workflow["11"]["inputs"]["denoise"] = upscale_denoise

    # LatentUpscaleBy — node 12
    workflow["12"]["inputs"]["scale_by"] = scale_by

    # SeedVR2 upscaler — node 18
    workflow["18"]["inputs"]["seed"] = seed
    workflow["18"]["inputs"]["resolution"] = upscale_resolution

    return workflow


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
    """Fetch final upscaled image from SaveImage node 19 and upload to R2."""
    client = _r2_client()
    results = []

    save_node_output = history["outputs"].get("19", {})
    for img in save_node_output.get("images", []):
        r = requests.get(
            f"{COMFYUI_URL}/view",
            params={
                "filename": img["filename"],
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output"),
            },
            timeout=120,
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

    prompt = job_input.get("prompt")
    seed = job_input.get("seed")
    width = job_input.get("width", 832)
    height = job_input.get("height", 1536)
    steps = job_input.get("steps", 8)
    cfg = job_input.get("cfg", 1.0)
    denoise = job_input.get("denoise", 1.0)
    negative_prompt = job_input.get("negative_prompt", "")
    upscale_denoise = job_input.get("upscale_denoise", 0.8)
    scale_by = job_input.get("scale_by", 1.25)
    upscale_resolution = job_input.get("upscale_resolution", 2560)

    if not prompt:
        return {"error": "prompt is required"}

    seed = random.randint(0, 2**32 - 1) if seed is None else int(seed)
    width = int(width)
    height = int(height)
    steps = int(steps)
    cfg = float(cfg)
    denoise = float(denoise)
    upscale_denoise = float(upscale_denoise)
    scale_by = float(scale_by)
    upscale_resolution = int(upscale_resolution)

    start_time = time.time()

    workflow = build_workflow(
        prompt, seed, width, height, steps, cfg, denoise,
        negative_prompt, upscale_denoise, scale_by, upscale_resolution,
    )

    prompt_id = queue_workflow(workflow)
    print(f"Queued workflow prompt_id={prompt_id}")

    history = wait_for_job(prompt_id)
    images = upload_images_to_r2(history)

    duration = round(time.time() - start_time, 2)
    return {
        "images": images,
        "params": {
            "prompt": prompt,
            "seed": seed,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg": cfg,
            "denoise": denoise,
            "negative_prompt": negative_prompt,
            "upscale_denoise": upscale_denoise,
            "scale_by": scale_by,
            "upscale_resolution": upscale_resolution,
        },
        "duration_seconds": duration,
    }


print("Waiting for ComfyUI to be ready...")
wait_for_comfyui()
print("ComfyUI is ready. Starting RunPod serverless handler.")

runpod.serverless.start({"handler": handler})
