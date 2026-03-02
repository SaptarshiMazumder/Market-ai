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

# ── Z-Image-Turbo models (same as image-generation-z-turbo worker) ────────────

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

# ── SeedVR2 models ─────────────────────────────────────────────────────────────
# These are used by the SeedVR2VideoUpscaler node.
#
# NOTE: Verify the exact HuggingFace repo URLs before running — update below
# if the model has moved or your custom node expects a different folder layout.
#
# SeedVR2 VAE  → placed in models/vae/ (resolved via extra_model_paths.yaml)
# SeedVR2 DiT  → placed in models/diffusion_models/ (resolved via extra_model_paths.yaml)
#
# If the SeedVR2 custom node looks in a different folder (e.g. models/SeedVR2/),
# create a symlink:
#   ln -s $VOLUME/models/diffusion_models/seedvr2_ema_3b-Q4_K_M.gguf \
#         $VOLUME/models/SeedVR2/seedvr2_ema_3b-Q4_K_M.gguf

echo "=== Downloading SeedVR2 VAE: ema_vae_fp16.safetensors ==="
# TODO: Replace with the correct HuggingFace URL for ema_vae_fp16.safetensors
wget -c "https://huggingface.co/SeedVR/SeedVR2/resolve/main/ema_vae_fp16.safetensors" \
    -O "$VOLUME/models/vae/ema_vae_fp16.safetensors"

echo "=== Downloading SeedVR2 DiT: seedvr2_ema_3b-Q4_K_M.gguf ==="
# TODO: Replace with the correct HuggingFace URL for the GGUF quantised DiT
wget -c "https://huggingface.co/city96/SeedVR2-ema-3B-GGUF/resolve/main/seedvr2_ema_3b-Q4_K_M.gguf" \
    -O "$VOLUME/models/diffusion_models/seedvr2_ema_3b-Q4_K_M.gguf"

echo ""
echo "=== Done. Network volume model listing ==="
find "$VOLUME/models" -type f \( -name "*.safetensors" -o -name "*.gguf" \) -exec ls -lh {} \;
echo ""
echo "You can now terminate this pod."
