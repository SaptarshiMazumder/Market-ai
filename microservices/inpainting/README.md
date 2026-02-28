# Inpainting Serverless Worker

ComfyUI-based inpainting worker running on RunPod Serverless with Flux 2 Klein 9B.

## Models on Network Volume

| Model | Path on Volume | Size | Source |
|-------|---------------|------|--------|
| UNET (fp8) | `models/unet/flux-2-klein-9b.safetensors` | 8.8 GB | `black-forest-labs/FLUX.2-klein-9b-fp8` |
| VAE | `models/vae/flux2-vae.safetensors` | 321 MB | `Comfy-Org/flux2-klein-9B` |
| CLIP (full precision) | `models/clip/qwen_3_8b.safetensors` | 16 GB | `Comfy-Org/flux2-klein-9B` |

## Setting Up the Network Volume

1. Create a RunPod **Pod** (not Serverless) with your network volume attached.
2. SSH in or open the web terminal.
3. Run the commands below.
4. Terminate the pod when done — files persist on the volume.

### Create directories

```bash
mkdir -p /workspace/models/unet
mkdir -p /workspace/models/vae
mkdir -p /workspace/models/clip
```

### Download models

UNET (~8.8 GB) — gated repo, requires HuggingFace token:

```bash
wget --header="Authorization: Bearer hf_XXXXXXXXXXXX" \
  "https://huggingface.co/black-forest-labs/FLUX.2-klein-9b-fp8/resolve/main/flux-2-klein-9b-fp8.safetensors" \
  -O /workspace/models/unet/flux-2-klein-9b.safetensors
```

VAE (~321 MB):

```bash
wget "https://huggingface.co/Comfy-Org/flux2-klein-9B/resolve/main/split_files/vae/flux2-vae.safetensors" \
  -O /workspace/models/vae/flux2-vae.safetensors
```

CLIP (~16 GB, full precision):

```bash
wget "https://huggingface.co/Comfy-Org/flux2-klein-9B/resolve/main/split_files/text_encoders/qwen_3_8b.safetensors" \
  -O /workspace/models/clip/qwen_3_8b.safetensors
```

### Verify

```bash
find /workspace/models -type f -name "*.safetensors" -exec ls -lh {} \;
```

Expected output:

```
-rw-r--r-- 1 root root 8.8G /workspace/models/unet/flux-2-klein-9b.safetensors
-rw-r--r-- 1 root root 321M /workspace/models/vae/flux2-vae.safetensors
-rw-r--r-- 1 root root  16G /workspace/models/clip/qwen_3_8b.safetensors
```

> On a Serverless worker, the volume mounts at `/runpod-volume` instead of `/workspace`. The `extra_model_paths.yaml` handles this mapping automatically.

## Environment Variables

Set these on the RunPod Serverless endpoint:

| Variable | Required | Description |
|----------|----------|-------------|
| `R2_ACCOUNT_ID` | Yes | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | Yes | R2 API token access key |
| `R2_SECRET_ACCESS_KEY` | Yes | R2 API token secret key |
| `R2_BUCKET` | Yes | Default R2 bucket name (no trailing slash) |
| `R2_INPUT_BUCKET` | No | Override bucket for input images (defaults to `R2_BUCKET`) |
| `R2_OUTPUT_BUCKET` | No | Override bucket for output images (defaults to `R2_BUCKET`) |

## Building and Deploying

```bash
docker build -t your-username/inpainting-worker:latest .
docker push your-username/inpainting-worker:latest
```

Then create a Serverless endpoint on RunPod with:
- **Container Image**: `your-username/inpainting-worker:latest`
- **GPU**: RTX 4090 or better (24 GB+ VRAM, CUDA 12.6+ driver)
- **Network Volume**: the volume with the models above

## API Usage

```bash
curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "scene_url": "r2://bucket/path/to/scene_with_mask.png",
      "reference_url": "r2://bucket/path/to/product.jpg",
      "prompt": "product on a surface",
      "seed": 42
    }
  }'
```

| Field | Required | Description |
|-------|----------|-------------|
| `scene_url` | Yes | Masked scene image (mask encoded in red channel). HTTPS URL or `r2://` reference. |
| `reference_url` | Yes | Product/reference image. HTTPS URL or `r2://` reference. |
| `prompt` | No | Text prompt (default: `"product on a surface"`) |
| `seed` | No | Random seed (default: random) |
