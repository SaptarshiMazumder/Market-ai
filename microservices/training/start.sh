#!/bin/bash
set -e

MODEL_DIR="/runpod-volume/FLUX.1-dev"

SHARD1="$MODEL_DIR/transformer/diffusion_pytorch_model-00001-of-00003.safetensors"
SHARD2="$MODEL_DIR/transformer/diffusion_pytorch_model-00002-of-00003.safetensors"
SHARD3="$MODEL_DIR/transformer/diffusion_pytorch_model-00003-of-00003.safetensors"
TOKENIZER_FILE="$MODEL_DIR/tokenizer/merges.txt"

if [ -f "$SHARD1" ] && [ -f "$SHARD2" ] && [ -f "$SHARD3" ] && [ -f "$TOKENIZER_FILE" ]; then
    echo "FLUX.1-dev already cached at $MODEL_DIR"
else
    echo "Incomplete or missing model files. Cleaning up volume and re-downloading..."
    rm -rf /runpod-volume/*
    echo "Downloading FLUX.1-dev from HuggingFace (one-time)..."
    python -c "
import os
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='black-forest-labs/FLUX.1-dev',
    local_dir='$MODEL_DIR',
    token=os.environ.get('HF_TOKEN', ''),
    ignore_patterns=['*.md', '.gitattributes'],
)
print('Download complete.')
"
fi

echo "Starting RunPod handler..."
exec python /app/handler.py
