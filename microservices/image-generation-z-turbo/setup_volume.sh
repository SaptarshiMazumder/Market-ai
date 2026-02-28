#!/usr/bin/env bash
# Run this ONCE on a RunPod pod that has the network volume mounted at /workspace.
# Downloads the three model files needed by the Z-Image-Turbo workflow.
#
# Usage:
#   1. Create a RunPod pod (any GPU) with your network volume attached
#   2. SSH in and run:  bash setup_volume.sh
#   3. Terminate the pod when done — the files stay on the volume forever.

set -euo pipefail

VOLUME=/workspace

mkdir -p "$VOLUME/models/diffusion_models"
mkdir -p "$VOLUME/models/text_encoders"
mkdir -p "$VOLUME/models/vae"

BASE="https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files"

echo "=== Downloading diffusion model: z_image_turbo_bf16.safetensors (~4.7 GB) ==="
wget "$BASE/diffusion_models/z_image_turbo_bf16.safetensors" \
    -O "$VOLUME/models/diffusion_models/z_image_turbo_bf16.safetensors"

echo "=== Downloading text encoder: qwen_3_4b.safetensors (~7 GB) ==="
wget "$BASE/text_encoders/qwen_3_4b.safetensors" \
    -O "$VOLUME/models/text_encoders/qwen_3_4b.safetensors"

echo "=== Downloading VAE: ae.safetensors (~330 MB) ==="
wget "$BASE/vae/ae.safetensors" \
    -O "$VOLUME/models/vae/ae.safetensors"

echo ""
echo "=== Done. Network volume contents ==="
find "$VOLUME/models" -type f -name "*.safetensors" -exec ls -lh {} \;
echo ""
echo "You can now terminate this pod."
