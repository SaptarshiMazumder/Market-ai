import runpod
import requests
import os
import json
import copy
import time
import subprocess
import random
import socket
import uuid
import boto3
from botocore.config import Config

WORKFLOW_PATH = os.path.join(os.path.dirname(__file__), "LoraWorkflow.json")

COMFYUI_URL = "http://127.0.0.1:8188"
LORAS_DIR = "/comfyui/models/loras"

R2_LORA_BUCKET = os.environ.get("R2_LORA_BUCKET", "test-ftp")
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

# Track which LoRAs were present when ComfyUI last started
known_loras = set()
comfyui_process = None  # Only tracked when we restart ComfyUI ourselves


def start_comfyui():
    global comfyui_process, known_loras

    print("Killing existing ComfyUI processes...")
    subprocess.run(["pkill", "-9", "-f", "main.py"], capture_output=True)

    # Wait until port 8188 is actually free (up to 15s)
    for i in range(15):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex(("127.0.0.1", 8188)) != 0:
                print(f"Port 8188 free after {i}s")
                break
        time.sleep(1)
    else:
        print("WARNING: port 8188 may still be in use — proceeding anyway")

    comfyui_process = subprocess.Popen(
        [
            "python", "/comfyui/main.py",
            "--disable-auto-launch",
            "--disable-metadata",
            "--listen", "127.0.0.1",
            "--port", "8188",
        ],
        cwd="/comfyui",
    )

    wait_for_comfyui()

    # Record which LoRAs ComfyUI now knows about
    known_loras = set(os.listdir(LORAS_DIR)) if os.path.exists(LORAS_DIR) else set()
    print(f"ComfyUI ready. Known LoRAs: {known_loras}")


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


def _build_workflow(prompt: str, width: int, height: int,
                    steps: int, lora_scale: float) -> dict:
    """Load LoraWorkflow.json and inject runtime params."""
    with open(WORKFLOW_PATH) as f:
        workflow = copy.deepcopy(json.load(f))

    # Find which node ID is the positive prompt by inspecting the KSampler
    positive_node_id = None
    for node in workflow.values():
        if node.get("class_type") == "KSampler":
            node["inputs"]["steps"] = steps
            node["inputs"]["seed"] = random.randint(0, 2**32 - 1)
            positive_node_id = str(node["inputs"]["positive"][0])

    for node_id, node in workflow.items():
        class_type = node.get("class_type")
        if class_type == "CLIPTextEncode" and node_id == positive_node_id:
            node["inputs"]["text"] = prompt
        elif class_type == "EmptyLatentImage":
            node["inputs"]["width"] = width
            node["inputs"]["height"] = height
        elif class_type == "LoraLoader":
            node["inputs"]["strength_model"] = lora_scale
            node["inputs"]["strength_clip"] = lora_scale

    return workflow


def download_lora(lora_key: str) -> str:
    """Download LoRA from Cloudflare R2 into the ComfyUI loras dir. Returns filename."""
    if lora_key.startswith("r2://"):
        parts = lora_key[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1]
    else:
        bucket = R2_LORA_BUCKET
        key = lora_key

    filename = os.path.basename(key)
    dest = os.path.join(LORAS_DIR, filename)

    if not os.path.exists(dest):
        print(f"Downloading LoRA from R2: bucket={bucket} key={key}")
        os.makedirs(LORAS_DIR, exist_ok=True)
        _r2_client().download_file(bucket, key, dest)
        print(f"Downloaded: {filename}")

    return filename


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
        time.sleep(1)
    raise TimeoutError(f"Job {prompt_id} timed out")


def upload_images_to_r2(history) -> list:
    """Fetch generated images from ComfyUI, upload to R2, return list of r2_paths."""
    client = _r2_client()
    results = []
    for node_output in history["outputs"].values():
        for img in node_output.get("images", []):
            r = requests.get(
                f"{COMFYUI_URL}/view",
                params={
                    "filename": img["filename"],
                    "subfolder": img["subfolder"],
                    "type": img["type"],
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
            print(f"Uploaded image to R2: {key}")
            results.append({"r2_path": f"r2://{R2_OUTPUT_BUCKET}/{key}", "filename": img["filename"]})
    return results


def handler(job):
    job_input = job["input"]
    lora_key = job_input.get("lora_key")
    prompt = job_input.get("prompt", "")
    width = int(job_input.get("width", 1024))
    height = int(job_input.get("height", 1024))
    steps = int(job_input.get("steps", 25))
    lora_scale = float(job_input.get("lora_scale", 1.0))

    if not lora_key:
        return {"error": "lora_key is required"}

    lora_filename = download_lora(lora_key)

    # If this LoRA wasn't present when ComfyUI started, restart so it sees it
    if lora_filename not in known_loras:
        print(f"New LoRA detected ({lora_filename}), restarting ComfyUI...")
        start_comfyui()

    workflow = _build_workflow(prompt, width, height, steps, lora_scale)

    # Inject the downloaded LoRA filename
    for node in workflow.values():
        if node.get("class_type") == "LoraLoader":
            node["inputs"]["lora_name"] = lora_filename

    prompt_id = queue_workflow(workflow)
    history = wait_for_job(prompt_id)
    images = upload_images_to_r2(history)

    return {"images": images}


# ComfyUI is already started by start.sh — just wait for it to be ready
print("Waiting for ComfyUI to be ready...")
wait_for_comfyui()

# Record which LoRAs ComfyUI knows about at startup
known_loras = set(os.listdir(LORAS_DIR)) if os.path.exists(LORAS_DIR) else set()
print(f"ComfyUI ready. Known LoRAs at startup: {known_loras}")

runpod.serverless.start({"handler": handler})
