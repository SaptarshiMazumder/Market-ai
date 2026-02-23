#!/bin/bash
# Create symbolic links to the base model on the persistent volume
# This allows the empty ComfyUI container to use the models we downloaded manually.

echo "Setting up ComfyUI model symlinks..."

# Ensure target directories exist
mkdir -p /comfyui/models/unet
mkdir -p /comfyui/models/vae
mkdir -p /comfyui/models/text_encoders

# Check if the volume is mounted
if [ -d "/runpod-volume/FLUX.1-dev" ]; then
    echo "Found FLUX.1-dev on runpod-volume. Creating symlinks..."
    
    # 1. The main UNet model
    if [ ! -L "/comfyui/models/unet/flux1-dev.safetensors" ]; then
        ln -s /runpod-volume/FLUX.1-dev/flux1-dev.safetensors /comfyui/models/unet/flux1-dev.safetensors
    fi
    
    # 2. The VAE
    if [ ! -L "/comfyui/models/vae/ae.safetensors" ]; then
        ln -s /runpod-volume/FLUX.1-dev/ae.safetensors /comfyui/models/vae/ae.safetensors
    fi
    
    # 3. The CLIP models
    if [ ! -L "/comfyui/models/text_encoders/clip_l.safetensors" ]; then
        ln -s /runpod-volume/FLUX.1-dev/text_encoder/model.safetensors /comfyui/models/text_encoders/clip_l.safetensors
    fi
    
    # ComfyUI requires a single t5xxl_fp16.safetensors file, but the Diffusers repo shards it.
    # If the single file isn't on the volume yet, download it directly from Comfy-Org's huggingface repo.
    if [ ! -f "/runpod-volume/t5xxl_fp16.safetensors" ]; then
        echo "Downloading standalone t5xxl_fp16.safetensors for ComfyUI..."
        wget -O /runpod-volume/t5xxl_fp16.safetensors https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp16.safetensors
    fi
    
    if [ ! -L "/comfyui/models/text_encoders/t5xxl_fp16.safetensors" ]; then
        ln -s /runpod-volume/t5xxl_fp16.safetensors /comfyui/models/text_encoders/t5xxl_fp16.safetensors
    fi
    
    echo "Symlinks created successfully."
else
    echo "WARNING: /runpod-volume/FLUX.1-dev not found!"
    echo "Did you forget to attach the Network Volume to this Serverless Endpoint?"
fi

# Execute the start script built into the runpod/worker-comfyui image
echo "Starting ComfyUI Worker..."
exec python -u /handler.py
