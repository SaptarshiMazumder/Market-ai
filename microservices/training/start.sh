#!/bin/bash
set -e

MODEL_DIR="/runpod-volume/FLUX.2-klein-4B"
CACHE_DIR="/runpod-volume/hf-cache"

# Check for a specific file that proves the FLUX.2 download completed
CHECK_FILE="$MODEL_DIR/transformer/diffusion_pytorch_model.safetensors"

if [ -f "$CHECK_FILE" ]; then
    echo "FLUX.2-klein-4B is already cached at $MODEL_DIR"
else
    echo "FLUX.2-klein-4B not found or incomplete. Downloading to volume..."
    
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
from huggingface_hub import snapshot_download

print('Downloading FLUX.2 Klein 4B Trainer Format (~14GB)...')
snapshot_download(
    repo_id='black-forest-labs/FLUX.2-klein-4B',
    local_dir='$MODEL_DIR',
    cache_dir='$CACHE_DIR',
    token=os.environ.get('HF_TOKEN', ''),
    allow_patterns=[
        'model_index.json',
        'transformer/*',
        'vae/*',
        'text_encoder/*',
        'text_encoder_2/*',
        'tokenizer/*',
        'tokenizer_2/*',
        'scheduler/*'
    ]
)
print('FLUX.2 Klein 4B successfully downloaded to volume!')
"
fi

echo "Starting RunPod handler..."
exec python /app/handler.py
