# Z-Image-Turbo Serverless Worker

Text-to-image generation using Z-Image-Turbo on RunPod Serverless.

## Models on Network Volume

| Model | Path on Volume | Size | Source |
|-------|---------------|------|--------|
| Diffusion Model (bf16) | `models/diffusion_models/z_image_turbo_bf16.safetensors` | ~4.7 GB | `Comfy-Org/z_image_turbo` |
| Text Encoder (Qwen 3.4B) | `models/text_encoders/qwen_3_4b.safetensors` | ~7 GB | `Comfy-Org/z_image_turbo` |
| VAE | `models/vae/ae.safetensors` | ~330 MB | `Comfy-Org/z_image_turbo` |

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
```

### Download models

All models are from the public `Comfy-Org/z_image_turbo` repo -- no auth needed.

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

### Verify

```bash
find /workspace/models -type f -name "*.safetensors" -exec ls -lh {} \;
```

> On a Serverless worker, the volume mounts at `/runpod-volume`. The `extra_model_paths.yaml` maps the model directories automatically.

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
docker build -t your-username/z-image-turbo-worker:latest .
docker push your-username/z-image-turbo-worker:latest
```

Then create a Serverless endpoint on RunPod with:
- **Container Image**: `your-username/z-image-turbo-worker:latest`
- **GPU**: RTX 4090 or better (24 GB+ VRAM)
- **Network Volume**: the volume with the models above

## API Usage

```bash
curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "prompt": "a product photograph of a red sneaker on a marble surface",
      "width": 1024,
      "height": 1024,
      "steps": 8,
      "seed": 42
    }
  }'
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `prompt` | Yes | -- | Text description of the image to generate |
| `width` | No | `1024` | Image width in pixels |
| `height` | No | `1024` | Image height in pixels |
| `steps` | No | `8` | Sampling steps |
| `cfg` | No | `1.0` | Classifier-free guidance scale |
| `denoise` | No | `1.0` | Denoise strength |
| `seed` | No | random | Random seed for reproducibility |
