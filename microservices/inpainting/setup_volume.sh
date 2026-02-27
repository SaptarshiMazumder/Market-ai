#!/usr/bin/env bash
# Run this ONCE on a RunPod pod that has the network volume mounted at /runpod-volume.
# It downloads the three model files needed by the workflow and places them
# in the exact paths/filenames the workflow JSON expects.
#
# Usage:
#   1. Create a RunPod pod (any GPU, e.g. RTX 3080) with your network volume attached at /runpod-volume
#   2. SSH in and run:  bash setup_volume.sh
#   3. Terminate the pod when done — the files stay on the volume forever.
#
# Requires: pip install huggingface_hub  (or: pip install -U huggingface_hub)
# For gated repos you need a HuggingFace token:  export HF_TOKEN=hf_...

set -euo pipefail

VOLUME=/runpod-volume

mkdir -p "$VOLUME/models/unet"
mkdir -p "$VOLUME/models/vae"
mkdir -p "$VOLUME/models/clip"

pip install -q -U huggingface_hub

echo "=== Downloading UNET: flux-2-klein-9b.safetensors (fp8, ~9 GB) ==="
# fp8 version — same quality, half the VRAM of full precision
huggingface-cli download \
    black-forest-labs/FLUX.2-klein-9b-fp8 \
    flux-2-klein-9b-fp8.safetensors \
    --local-dir /tmp/hf_dl \
    ${HF_TOKEN:+--token "$HF_TOKEN"}
mv /tmp/hf_dl/flux-2-klein-9b-fp8.safetensors "$VOLUME/models/unet/flux-2-klein-9b.safetensors"

echo "=== Downloading VAE: flux2-vae.safetensors (~330 MB) ==="
huggingface-cli download \
    Comfy-Org/flux2-klein-9B \
    split_files/vae/flux2-vae.safetensors \
    --local-dir /tmp/hf_dl \
    ${HF_TOKEN:+--token "$HF_TOKEN"}
mv /tmp/hf_dl/split_files/vae/flux2-vae.safetensors "$VOLUME/models/vae/flux2-vae.safetensors"

echo "=== Downloading CLIP: qwen_3_8b.safetensors (fp8 mixed, ~8.7 GB) ==="
huggingface-cli download \
    Comfy-Org/flux2-klein-9B \
    split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors \
    --local-dir /tmp/hf_dl \
    ${HF_TOKEN:+--token "$HF_TOKEN"}
mv /tmp/hf_dl/split_files/text_encoders/qwen_3_8b_fp8mixed.safetensors "$VOLUME/models/clip/qwen_3_8b.safetensors"

rm -rf /tmp/hf_dl

echo ""
echo "=== Done. Network volume contents ==="
find "$VOLUME/models" -type f -name "*.safetensors" | sort
echo ""
echo "You can now terminate this pod."
