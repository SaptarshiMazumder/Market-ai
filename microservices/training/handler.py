"""RunPod serverless handler for Flux LoRA training via ai-toolkit."""

import runpod
import os
import subprocess
import zipfile
import glob
import shutil
import requests
import boto3
from botocore.config import Config
from train_config import write_config

WORK_DIR = "/tmp/train_job"
TOOLKIT_DIR = "/app/ai-toolkit"
# /runpod-volume/FLUX.1-dev as default path for base model
VOLUME_MODEL_PATH = os.environ.get("VOLUME_MODEL_PATH", "/runpod-volume/FLUX.1-dev")


def download_base_model(dest_dir: str) -> None:
    """Download the Flux base model from Civitai if it doesn't exist."""
    if os.path.exists(dest_dir):
        print(f"Base model already exists at {dest_dir}. Skipping download.")
        return

    model_url = os.environ.get("BASE_MODEL_URL")
    api_key = os.environ.get("CIVITAI_API_KEY")

    if not model_url:
        print("BASE_MODEL_URL not set. Skipping automated base model download.")
        return

    print(f"Downloading base model from Civitai to {dest_dir}...")
    os.makedirs(dest_dir, exist_ok=True)
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    # Use a subprocess to run wget for efficiency and progress tracking
    # Civitai download URLs usually work well with wget
    try:
        # Example URL: https://civitai.com/api/download/models/618692
        # We assume the URL provided is a direct download link or Civitai API link
        download_path = os.path.join(dest_dir, "flux1-dev.safetensors") # Default name
        
        cmd = ["wget", "--header", f"Authorization: Bearer {api_key}" if api_key else "", "-O", download_path, model_url]
        subprocess.run([c for c in cmd if c], check=True)
        print("Base model download complete.")
    except Exception as e:
        print(f"Failed to download base model: {e}")
        # If it fails, we hope the training fails later with a clear error


def _build_r2_client():
    account_id = os.environ["R2_ACCOUNT_ID"].strip()
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"].strip(),
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"].strip(),
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def download_dataset(url: str, dest_dir: str) -> str:
    """Download and extract a dataset zip from a public URL or R2."""
    zip_path = os.path.join(dest_dir, "dataset.zip")
    extract_dir = os.path.join(dest_dir, "dataset")
    os.makedirs(extract_dir, exist_ok=True)

    if url.startswith("http://") or url.startswith("https://"):
        print(f"Downloading dataset from {url}")
        resp = requests.get(url, stream=True)
        resp.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
    else:
        input_bucket = os.environ.get("R2_INPUT_BUCKET", "exp-train-dataset")
        print(f"Downloading dataset from R2 bucket {input_bucket}, key {url}")
        client = _build_r2_client()
        client.download_file(input_bucket, url, zip_path)

    print("Extracting dataset...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    os.remove(zip_path)

    entries = os.listdir(extract_dir)
    if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
        extract_dir = os.path.join(extract_dir, entries[0])

    image_count = len(glob.glob(os.path.join(extract_dir, "*.jpg")) +
                      glob.glob(os.path.join(extract_dir, "*.png")) +
                      glob.glob(os.path.join(extract_dir, "*.jpeg")) +
                      glob.glob(os.path.join(extract_dir, "*.webp")))
    print(f"Dataset ready: {image_count} images in {extract_dir}")
    return extract_dir


def find_final_safetensors(output_dir: str) -> str:
    """Find the final .safetensors file from the training output."""
    candidates = glob.glob(os.path.join(output_dir, "**", "*.safetensors"), recursive=True)
    if not candidates:
        raise FileNotFoundError(f"No .safetensors files found in {output_dir}")

    final = [c for c in candidates if "step" not in os.path.basename(c)]
    if final:
        return sorted(final)[-1]
    return sorted(candidates)[-1]


def upload_to_r2(local_path: str, bucket: str, key: str) -> str:
    """Upload a file to Cloudflare R2 and return the key."""
    client = _build_r2_client()
    print(f"Uploading {local_path} -> r2://{bucket}/{key}")
    client.upload_file(local_path, bucket, key)
    print("Upload complete.")
    return f"r2://{bucket}/{key}"


def run_training(config_path: str) -> None:
    """Run ai-toolkit training as a subprocess."""
    cmd = [
        "python", os.path.join(TOOLKIT_DIR, "run.py"),
        config_path,
    ]
    print(f"Starting training: {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=TOOLKIT_DIR,
    )

    for line in proc.stdout:
        print(line, end="")

    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"Training failed with exit code {proc.returncode}")

    print("Training completed successfully.")


def handler(job):
    job_input = job["input"]

    dataset_url = job_input.get("dataset_url")
    if not dataset_url:
        return {"error": "dataset_url is required"}

    lora_name = job_input.get("lora_name", "lora_output")

    if os.path.exists(WORK_DIR):
        shutil.rmtree(WORK_DIR)
    os.makedirs(WORK_DIR, exist_ok=True)

    dataset_dir = download_dataset(dataset_url, WORK_DIR)

    # Ensure base model exists
    download_base_model(VOLUME_MODEL_PATH)

    output_dir = os.path.join(WORK_DIR, "output")
    config_path = os.path.join(WORK_DIR, "train_config.yaml")
    write_config(job_input, dataset_dir, output_dir, config_path)

    run_training(config_path)

    safetensors_path = find_final_safetensors(output_dir)

    r2_bucket = job_input.get("r2_bucket", os.environ.get("R2_BUCKET", ""))
    if not r2_bucket:
        return {"error": "r2_bucket must be provided in input or R2_BUCKET env var"}

    r2_prefix = job_input.get("r2_prefix", "").strip("/")
    filename = f"{lora_name}.safetensors"
    r2_key = f"{r2_prefix}/{filename}" if r2_prefix else filename

    r2_path = upload_to_r2(safetensors_path, r2_bucket, r2_key)

    return {
        "status": "success",
        "lora_name": lora_name,
        "r2_path": r2_path,
    }


runpod.serverless.start({"handler": handler})
