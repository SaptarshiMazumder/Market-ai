# Image Generate and Upscale Serverless Worker

Text-to-image generation using Z-Image-Turbo followed by a two-stage upscale:
latent upscale (KSampler) → SeedVR2 AI upscale.

## Models on Network Volume

| Model | Path on Volume | Size | Source |
|-------|---------------|------|--------|
| Diffusion Model (bf16) | `models/diffusion_models/z_image_turbo_bf16.safetensors` | ~4.7 GB | `Comfy-Org/z_image_turbo` |
| Text Encoder (Qwen 3.4B) | `models/text_encoders/qwen_3_4b.safetensors` | ~7 GB | `Comfy-Org/z_image_turbo` |
| VAE (Flux) | `models/vae/ae.safetensors` | ~330 MB | `Comfy-Org/z_image_turbo` |
| SeedVR2 VAE | `models/SEEDVR2/ema_vae_fp16.safetensors` | ~1 GB | `numz/SeedVR2_comfyUI` *(gated — needs HF token)* |
| SeedVR2 DiT (GGUF Q4_K_M) | `models/SEEDVR2/seedvr2_ema_3b-Q4_K_M.gguf` | ~2 GB | `cmeka/SeedVR2-GGUF` |

## Setting Up the Network Volume

1. Create a RunPod **Pod** (not Serverless) with your network volume attached.
2. SSH in or open the web terminal.
3. Run the commands below.
4. Terminate the pod when done -- files persist on the volume.

### Create directories

```bash
mkdir -p /workspace/models/diffusion_models
mkdir -p /workspace/models/text_encoders
mkdir -p /workspace/models/vae
mkdir -p /workspace/models/SEEDVR2
```

### Download Z-Image-Turbo models

All three are from the public `Comfy-Org/z_image_turbo` repo -- no auth needed.

Diffusion model (~4.7 GB):

```bash
wget "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors" \
  -O /workspace/models/diffusion_models/z_image_turbo_bf16.safetensors
```

Text encoder (~7 GB):

```bash
wget "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors" \
  -O /workspace/models/text_encoders/qwen_3_4b.safetensors
```

VAE (~330 MB):

```bash
wget "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors" \
  -O /workspace/models/vae/ae.safetensors
```

### Download SeedVR2 models

> The SeedVR2 VAE on `numz/SeedVR2_comfyUI` is a gated model — you need a HuggingFace token.
> Set `HF_TOKEN` before running: `export HF_TOKEN=your_token_here`

SeedVR2 VAE (~1 GB):

```bash
wget --header="Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/numz/SeedVR2_comfyUI/resolve/main/ema_vae_fp16.safetensors" \
  -O /workspace/models/SEEDVR2/ema_vae_fp16.safetensors
```

SeedVR2 DiT GGUF Q4_K_M (~2 GB):

```bash
wget "https://huggingface.co/cmeka/SeedVR2-GGUF/resolve/main/seedvr2_ema_3b-Q4_K_M.gguf" \
  -O /workspace/models/SEEDVR2/seedvr2_ema_3b-Q4_K_M.gguf
```

### Verify

```bash
find /workspace/models -type f \( -name "*.safetensors" -o -name "*.gguf" \) -exec ls -lh {} \;
```

> On a Serverless worker, the volume mounts at `/runpod-volume`. The `extra_model_paths.yaml` maps all model directories (including `models/SEEDVR2/`) automatically so ComfyUI can find all five files.

## Environment Variables

Set these on the RunPod Serverless endpoint:

| Variable | Required | Description |
|----------|----------|-------------|
| `R2_ACCOUNT_ID` | Yes | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | Yes | R2 API token access key |
| `R2_SECRET_ACCESS_KEY` | Yes | R2 API token secret key |
| `R2_BUCKET` | Yes | Default R2 bucket name (no trailing slash) |
| `R2_OUTPUT_BUCKET` | No | Override bucket for output images (defaults to `R2_BUCKET`) |

## Building and Deploying

```bash
docker build -t your-username/image-generate-and-upscale-worker:latest .
docker push your-username/image-generate-and-upscale-worker:latest
```

Then create a Serverless endpoint on RunPod with:
- **Container Image**: `your-username/image-generate-and-upscale-worker:latest`
- **GPU**: RTX 4090 or better (24 GB+ VRAM recommended for SeedVR2)
- **Network Volume**: the volume with the models above

## API Usage

```bash
curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "prompt": "a product photograph of a red sneaker on a marble surface",
      "width": 832,
      "height": 1536,
      "steps": 8,
      "seed": 42
    }
  }'
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `prompt` | Yes | -- | Text description of the image to generate |
| `negative_prompt` | No | `""` | Text to suppress in the output |
| `width` | No | `832` | Image width in pixels |
| `height` | No | `1536` | Image height in pixels |
| `steps` | No | `8` | Sampling steps (applied to both KSamplers) |
| `cfg` | No | `1.0` | Classifier-free guidance scale |
| `denoise` | No | `1.0` | Denoise strength for the generation pass |
| `upscale_denoise` | No | `0.8` | Denoise strength for the latent upscale pass |
| `scale_by` | No | `1.25` | Latent upscale factor before SeedVR2 |
| `upscale_resolution` | No | `2560` | Target resolution for SeedVR2 upscale |
| `seed` | No | random | Random seed (shared across all three sampling stages) |
