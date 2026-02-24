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
    
    # We purposefully DO NOT wipe the whole volume here because FLUX.1 might still be on it.
    # We only clean up the target directory for FLUX.2
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
