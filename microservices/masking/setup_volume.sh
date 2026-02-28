#!/usr/bin/env bash
# Run this ONCE on a RunPod pod that has the network volume mounted at /workspace.
# It downloads the two model files/directories needed by the masking workflow.
#
# Usage:
#   1. Create a RunPod pod (any GPU) with your network volume attached
#   2. SSH in and run:  bash setup_volume.sh
#   3. Terminate the pod when done — the files stay on the volume forever.

set -euo pipefail

VOLUME=/workspace

mkdir -p "$VOLUME/models/sam2"
mkdir -p "$VOLUME/models/LLM"

pip install -q -U huggingface_hub

echo "=== Downloading SAM2: sam2_hiera_base_plus.safetensors (~350 MB) ==="
wget -q --show-progress \
    "https://huggingface.co/Kijai/sam2-safetensors/resolve/main/sam2_hiera_base_plus.safetensors" \
    -O "$VOLUME/models/sam2/sam2_hiera_base_plus.safetensors"

echo "=== Downloading Florence 2 Large (~1.5 GB) ==="
huggingface-cli download \
    microsoft/Florence-2-large \
    --local-dir "$VOLUME/models/LLM/Florence-2-large" \
    --local-dir-use-symlinks False

echo ""
echo "=== Done. Network volume contents ==="
echo "--- SAM2 ---"
ls -lh "$VOLUME/models/sam2/"
echo "--- Florence 2 ---"
ls -lh "$VOLUME/models/LLM/Florence-2-large/"
echo ""
echo "You can now terminate this pod."
