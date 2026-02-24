#!/bin/bash
set -e

MODEL_DIR="/runpod-volume/FLUX.2-klein-4B"
CACHE_DIR="/runpod-volume/hf-cache"

# Check for the monolithic file ai-toolkit expects
CHECK_FILE="$MODEL_DIR/flux-2-klein-base-4b.safetensors"

if [ -f "$CHECK_FILE" ]; then
    echo "FLUX.2-klein-4B monolithic model found at $CHECK_FILE"
else
    echo "FLUX.2-klein-4B monolithic model not found. Attempting download..."
    
    # We must wipe the old FLUX.1 model because the 80GB volume is entirely full!
    # (FLUX.1 + T5 standalone + Old AI Toolkit checkpoints = 80GB maxed out)
    echo "Freeing up 45GB of space by removing older FLUX.1 models..."
    rm -rf /runpod-volume/FLUX.1-dev
    rm -rf /runpod-volume/hf-cache/*
    
    mkdir -p "$MODEL_DIR"
    mkdir -p "$CACHE_DIR"
    rm -rf "$MODEL_DIR/*"

    python -c "
import os
from huggingface_hub import hf_hub_download

print('Downloading the monolithic FLUX.2 Klein 4B transformer...')
download_path = hf_hub_download(
    repo_id='black-forest-labs/FLUX.2-klein-4B',
    filename='flux-2-klein-4b.safetensors',
    local_dir='$MODEL_DIR',
    token=os.environ.get('HF_TOKEN', '')
)

# Rename to the exact format ai-toolkit demands
final_path = '$MODEL_DIR/flux-2-klein-base-4b.safetensors'
if os.path.exists(download_path) and download_path != final_path:
    os.rename(download_path, final_path)

print('FLUX.2 Klein 4B successfully ready on volume!')
"
fi

echo "Starting RunPod handler..."
exec python /app/handler.py
