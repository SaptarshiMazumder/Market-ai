#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# Model download URLs
# All models sourced from Kijai/WanVideo_comfy on HuggingFace (FP8, ComfyUI-ready)
# LightX2V LoRAs: verify the repo if these 404 (may be in a separate lightx2v repo)
# ---------------------------------------------------------------------------
HF_BASE="https://huggingface.co/Kijai/WanVideo_comfy/resolve/main"

declare -A MODELS=(
  ["diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"]="${HF_BASE}/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors"
  ["diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"]="${HF_BASE}/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
  ["loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors"]="${HF_BASE}/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors"
  ["loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors"]="${HF_BASE}/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors"
  ["vae/wan_2.1_vae.safetensors"]="${HF_BASE}/wan_2.1_vae.safetensors"
  ["clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors"]="${HF_BASE}/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
)

# ---------------------------------------------------------------------------
# Download models to network volume, then symlink into ComfyUI's model dirs
# Network volume: /runpod-volume/wan-models/<category>/
# ComfyUI dirs:   /comfyui/models/<category>/
# ---------------------------------------------------------------------------
VOLUME_MODELS="/runpod-volume/wan-models"

for rel_path in "${!MODELS[@]}"; do
  url="${MODELS[$rel_path]}"
  dest="${VOLUME_MODELS}/${rel_path}"
  dir=$(dirname "$dest")

  mkdir -p "$dir"

  if [ -f "$dest" ]; then
    echo "Already exists, skipping: $dest"
  else
    echo "Downloading: $rel_path"
    wget -q --show-progress \
      ${HF_TOKEN:+--header="Authorization: Bearer ${HF_TOKEN}"} \
      -O "$dest" "$url"
    echo "Done: $rel_path"
  fi

  # Symlink ComfyUI model dir entry → network volume file
  category=$(dirname "$rel_path")
  filename=$(basename "$rel_path")
  comfy_dir="/comfyui/models/${category}"
  mkdir -p "$comfy_dir"

  link="${comfy_dir}/${filename}"
  if [ ! -L "$link" ] && [ ! -f "$link" ]; then
    ln -s "$dest" "$link"
    echo "Linked: $link → $dest"
  fi
done

# ---------------------------------------------------------------------------
# Start ComfyUI in background, then handler
# ---------------------------------------------------------------------------
echo "Starting ComfyUI..."
python /comfyui/main.py \
    --disable-auto-launch \
    --disable-metadata \
    --listen 127.0.0.1 \
    --port 8188 &

echo "Starting RunPod handler..."
exec python /handler.py
