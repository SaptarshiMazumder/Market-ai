import runpod
import requests
import os
import time
import subprocess
import random
import socket
import uuid
import boto3
from botocore.config import Config

COMFYUI_URL = "http://127.0.0.1:8188"
LORAS_DIR = "/comfyui/models/loras"

R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_LORA_BUCKET = os.environ.get("R2_LORA_BUCKET", "test-ftp")
R2_OUTPUT_BUCKET = os.environ.get("R2_OUTPUT_BUCKET", "test-ftp")


def _r2_client():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
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


def download_lora(lora_key: str) -> str:
    """Download LoRA from Cloudflare R2 into the ComfyUI loras dir. Returns filename."""
    # Strip r2://bucket/ prefix if present
    if lora_key.startswith("r2://"):
        lora_key = lora_key.split("/", 3)[-1]

    filename = os.path.basename(lora_key)
    dest = os.path.join(LORAS_DIR, filename)

    if not os.path.exists(dest):
        print(f"Downloading LoRA from R2: {lora_key}")
        os.makedirs(LORAS_DIR, exist_ok=True)
        _r2_client().download_file(R2_LORA_BUCKET, lora_key, dest)
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
    workflow = job_input.get("workflow")

    if not workflow:
        return {"error": "No workflow provided"}

    if lora_key:
        lora_filename = download_lora(lora_key)

        # If this LoRA wasn't present when ComfyUI started, restart so it sees it
        if lora_filename not in known_loras:
            print(f"New LoRA detected ({lora_filename}), restarting ComfyUI...")
            start_comfyui()

        # Inject LoRA filename into workflow
        for node in workflow.values():
            if node.get("class_type") == "LoraLoader":
                node["inputs"]["lora_name"] = lora_filename

    # Randomize seed so every request is treated as a new job by ComfyUI
    for node in workflow.values():
        if node.get("class_type") == "KSampler":
            node["inputs"]["seed"] = random.randint(0, 2**32 - 1)

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
