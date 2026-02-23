# LoRA Training & Generation Architecture

This document outlines the end-to-end technical architecture for the decoupled LoRA training and inference pipelines. It is currently hardcoded for **FLUX.1-dev**, but designed to be modular so future consultants can easily swap in different base models, such as SDXL or SD3.5.

## 1. High-Level Infrastructure Overview
The pipeline runs on **RunPod Serverless** with Cloudflare **R2 Storage** acting as the central data and artifact broker.

- **Storage Volume**: A persistent `100GB Network Volume` mounted to both Endpoints at `/runpod-volume`. It acts as the "warm cache" for massive base models (UNet, VAE, CLIP, T5) to prevent 40GB+ cold-start downloads.
- **Service 1: Trainer Endpoint (`flux-exp-trainer`)**: Handles async LoRA training using `ai-toolkit`. Reads the raw dataset from a URL, trains against the base model on the volume, and pushes the final `.safetensors` LoRA to R2.
- **Service 2: Inference Endpoint (`flux-exp-worker`)**: Runs a headless ComfyUI backend. Receives a prompt, dynamically downloads the specified LoRA from R2, symlinks the base models from the volume, executes the workflow, and pushes the `.png` to R2.

---

## 2. Component Details

### 2.1 Storage & Model Distribution (The Cache Layer)
The primary bottleneck for scaling AI image infrastructure is the base model size. The 100GB Network Volume (`/runpod-volume`) mitigates this.
- **Format**: Hugging Face snapshot format.
- **Initialization**: If the network volume is empty or corrupted, `microservices/training/start.sh` automatically downloads `black-forest-labs/FLUX.1-dev` directly via the Hugging Face CLI.
- **Consultant Note**: If you switch to SDXL, update `start.sh` to pull `stabilityai/stable-diffusion-xl-base-1.0` instead. Ensure the volume size is adequate for both models if you plan to keep them simultaneously.

### 2.2 The Trainer Microservice (`microservices/training`)
- **Docker Image Base**: Uses `runpod/pytorch:2.2.1-py3.10-cuda12.1.1-devel-ubuntu22.04`
- **Core Engine**: A cloned fork of `ostris/ai-toolkit`.
- **Flow**:
  1. `start.sh` ensures base models are cached on `/runpod-volume`.
  2. `handler.py` receives the serverless JSON input.
  3. `handler.py` downloads the raw dataset (images + captions ZIP) from `dataset_url`.
  4. `train_config.py` intercepts the parameters (steps, LR, resolution) and generates a temporary `ai-toolkit` YAML configuration.
  5. The YAML is executed via a subprocess calling `python /app/ai-toolkit/run.py`.
  6. Upon success, `boto3` uploads the final `/output/{lora_name}/{lora_name}.safetensors` to the R2 Bucket.
- **Consultant Note**: EMA is intentionally disabled in `train_config.py` (`"use_ema": False`) to prevent CUDA OOM on 24GB L4/A5000 GPUs. If scaling to 40GB+ GPUs, re-enable EMA for better LoRA quality. To swap to a different architecture, change `"type": "sd_trainer"` inside the `model` block in `train_config.py` to match the expected `ai-toolkit` network.

### 2.3 The Inference Microservice (`microservices/image-generation`)
- **Docker Image Base**: Uses `runpod/worker-comfyui:5.7.1-base`
- **Core Engine**: Headless ComfyUI
- **Flow**:
  1. `start.sh` creates symlinks from the ComfyUI expectation paths (`/comfyui/models/unet`, `/comfyui/models/vae`, etc.) directly to the raw HuggingFace format stored on `/runpod-volume`. It dynamically downloads specific standalone files (like the unitary `t5xxl_fp16.safetensors`) if ComfyUI requires them monolithically but Hugging Face shards them.
  2. `handler.py` boots ComfyUI via subprocess natively before spinning up the RunPod Serverless listener.
  3. The handler receives a JSON prompt request.
  4. `boto3` downloads the requested `lora_key` from the R2 bucket into `/comfyui/models/loras`.
  5. `handler.py` dynamically injects the prompt, resolution, and `lora_name` into a massive `LoraWorkflow.json` dictionary.
  6. Sends the JSON to `htt​p://127.0.0.1:8188/prompt`.
  7. Polls `htt​p://127.0.0.1:8188/history` until the prompt ID returns 'Completed'.
  8. Pushes the output ComfyUI `.png` directly to R2 and returns the URI to the caller.
- **Consultant Note**: To change inference steps, samplers, or switch to SDXL, you do not need to write Python code. Run ComfyUI locally, drag the nodes, configure them, hit "Save (API Format)", and overwrite `LoraWorkflow.json`. Note that `start.sh` will need updated symlink targets if changing to SDXL, as ComfyUI expects `.safetensors` in `/models/checkpoints/` instead of `/models/unet/`.

---

## 3. Deployment Configuration

### Environment Variables Required
Both RunPod serverless endpoints heavily rely on these environment injections:
- `HF_TOKEN`: Hugging Face Read token (needed for gated models like FLUX.1-dev).
- `R2_ACCOUNT_ID`: Cloudflare R2 Account ID.
- `R2_ACCESS_KEY_ID`: Cloudflare R2 Access Key.
- `R2_SECRET_ACCESS_KEY`: Cloudflare R2 Secret Key.
- `R2_LORA_BUCKET`: e.g. `exp-models`. The bucket where newly trained `.safetensors` are pushed (Trainer) and pulled (Inference).
- `R2_OUTPUT_BUCKET`: e.g. `exp-generations`. The bucket where generated `.png` renders are pushed.

### GitHub Actions (CI/CD)
The Docker images are auto-built and pushed to Docker Hub via GitHub Actions upon any commit to the `main` or `experimental` branch modifying either the `/training/` or `/image-generation/` directories.
- RunPod endpoints must be configured with "Public Image" pointing to `[docker-username]/flux-exp-trainer:latest` and `[docker-username]/flux-exp-worker:latest`. RunPod handles pulling the latest hash naturally when warm workers wake up or when scaling from zero.

---

## 4. RunPod Endpoint Architectures

- **Training Endpoint:**
  - Image: `marcusrashford/flux-exp-trainer:latest`
  - GPU: 24GB VRAM minimum (L4 / RTX A5000 / RTX 3090/4090).
  - Storage: 100GB Network Volume attached.
  - Scale: Max 1 worker (training is linear and you don't want volume lock collisions if multiple trainers try to write to the cache simultaneously).

- **Inference Endpoint:**
  - Image: `marcusrashford/flux-exp-worker:latest`
  - GPU: 24GB VRAM minimum (inference uses ~18GB for FLUX FP8).
  - Storage: 100GB Network Volume attached.
  - Scale: 0 to N. ComfyUI workers only *read* the base models entirely from the volume. They write generated images statelessly to `/tmp` before pushing to R2, so safe parallel execution is guaranteed.
