#!/usr/bin/env bash
# Run this ONCE on a RunPod pod that has the network volume mounted at /workspace.
# Downloads all model files needed by the generate-and-upscale workflow.
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
mkdir -p "$VOLUME/models/SEEDVR2"

# ── Z-Image-Turbo models ──────────────────────────────────────────────────────

BASE="https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files"

echo "=== Downloading diffusion model: z_image_turbo_bf16.safetensors (~4.7 GB) ==="
wget -c "$BASE/diffusion_models/z_image_turbo_bf16.safetensors" \
    -O "$VOLUME/models/diffusion_models/z_image_turbo_bf16.safetensors"

echo "=== Downloading text encoder: qwen_3_4b.safetensors (~7 GB) ==="
wget -c "$BASE/text_encoders/qwen_3_4b.safetensors" \
    -O "$VOLUME/models/text_encoders/qwen_3_4b.safetensors"

echo "=== Downloading VAE: ae.safetensors (~330 MB) ==="
wget -c "$BASE/vae/ae.safetensors" \
    -O "$VOLUME/models/vae/ae.safetensors"

# ── SeedVR2 models (go in models/SEEDVR2/) ───────────────────────────────────

echo "=== Downloading SeedVR2 VAE: ema_vae_fp16.safetensors (requires HF token) ==="
if [ -z "${HF_TOKEN:-}" ]; then
    echo "ERROR: HF_TOKEN is not set. Export your HuggingFace token first:"
    echo "  export HF_TOKEN=your_token_here"
    exit 1
fi
wget -c --header="Authorization: Bearer $HF_TOKEN" \
    "https://huggingface.co/numz/SeedVR2_comfyUI/resolve/main/ema_vae_fp16.safetensors" \
    -O "$VOLUME/models/SEEDVR2/ema_vae_fp16.safetensors"

echo "=== Downloading SeedVR2 DiT: seedvr2_ema_3b-Q4_K_M.gguf ==="
wget -c "https://huggingface.co/cmeka/SeedVR2-GGUF/resolve/main/seedvr2_ema_3b-Q4_K_M.gguf" \
    -O "$VOLUME/models/SEEDVR2/seedvr2_ema_3b-Q4_K_M.gguf"

echo ""
echo "=== Done. Network volume model listing ==="
find "$VOLUME/models" -type f \( -name "*.safetensors" -o -name "*.gguf" \) -exec ls -lh {} \;
echo ""
echo "You can now terminate this pod."
