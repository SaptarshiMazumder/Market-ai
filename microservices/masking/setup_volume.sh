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

echo "=== Downloading SAM2: sam2_hiera_base_plus.safetensors (~350 MB) ==="
wget "https://huggingface.co/Kijai/sam2-safetensors/resolve/main/sam2_hiera_base_plus.safetensors" \
    -O "$VOLUME/models/sam2/sam2_hiera_base_plus.safetensors"

echo "=== Downloading Florence 2 Large (~1.5 GB) ==="
mkdir -p "$VOLUME/models/LLM/Florence-2-large"
BASE="https://huggingface.co/microsoft/Florence-2-large/resolve/main"
DIR="$VOLUME/models/LLM/Florence-2-large"

wget "$BASE/model.safetensors"          -O "$DIR/model.safetensors"
wget "$BASE/config.json"                -O "$DIR/config.json"
wget "$BASE/configuration_florence2.py" -O "$DIR/configuration_florence2.py"
wget "$BASE/modeling_florence2.py"      -O "$DIR/modeling_florence2.py"
wget "$BASE/processing_florence2.py"    -O "$DIR/processing_florence2.py"
wget "$BASE/preprocessor_config.json"   -O "$DIR/preprocessor_config.json"
wget "$BASE/tokenizer.json"             -O "$DIR/tokenizer.json"
wget "$BASE/tokenizer_config.json"      -O "$DIR/tokenizer_config.json"
wget "$BASE/vocab.json"                 -O "$DIR/vocab.json"
wget "$BASE/generation_config.json"     -O "$DIR/generation_config.json"

echo ""
echo "=== Done. Network volume contents ==="
echo "--- SAM2 ---"
ls -lh "$VOLUME/models/sam2/"
echo "--- Florence 2 ---"
ls -lh "$VOLUME/models/LLM/Florence-2-large/"
echo ""
echo "You can now terminate this pod."
