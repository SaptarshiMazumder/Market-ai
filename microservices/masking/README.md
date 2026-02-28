# Masking Serverless Worker

ComfyUI-based object masking worker running on RunPod Serverless. Uses Florence 2 for object detection and SAM2 for segmentation.

## Models on Network Volume

| Model | Path on Volume | Size | Source |
|-------|---------------|------|--------|
| SAM2 Hiera Base Plus | `models/sam2/sam2_hiera_base_plus.safetensors` | ~350 MB | `Kijai/sam2-safetensors` |
| Florence 2 Large | `models/LLM/Florence-2-large/` (directory) | ~1.5 GB | `microsoft/Florence-2-large` |

## Setting Up the Network Volume

1. Create a RunPod **Pod** (not Serverless) with your network volume attached.
2. SSH in or open the web terminal.
3. Run the commands below.
4. Terminate the pod when done -- files persist on the volume.

### Create directories

```bash
mkdir -p /workspace/models/sam2
mkdir -p /workspace/models/LLM
```

### Download models

SAM2 (~350 MB):

```bash
wget "https://huggingface.co/Kijai/sam2-safetensors/resolve/main/sam2_hiera_base_plus.safetensors" \
  -O /workspace/models/sam2/sam2_hiera_base_plus.safetensors
```

Florence 2 Large (~1.5 GB, multi-file model):

```bash
mkdir -p /workspace/models/LLM/Florence-2-large

BASE="https://huggingface.co/microsoft/Florence-2-large/resolve/main"
DIR="/workspace/models/LLM/Florence-2-large"

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
```

### Verify

```bash
ls -lh /workspace/models/sam2/
ls -lh /workspace/models/LLM/Florence-2-large/
```

Expected:

```
/workspace/models/sam2/sam2_hiera_base_plus.safetensors  (~350 MB)

/workspace/models/LLM/Florence-2-large/
  config.json
  model.safetensors
  tokenizer.json
  tokenizer_config.json
  preprocessor_config.json
  ...
```

> On a Serverless worker, the volume mounts at `/runpod-volume`. The Dockerfile creates symlinks from `/comfyui/models/sam2` and `/comfyui/models/LLM` to the network volume so the custom nodes find their models.

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
docker build -t your-username/masking-worker:latest .
docker push your-username/masking-worker:latest
```

Then create a Serverless endpoint on RunPod with:
- **Container Image**: `your-username/masking-worker:latest`
- **GPU**: Any GPU with 8 GB+ VRAM (models are lightweight)
- **Network Volume**: the volume with the models above

## API Usage

```bash
curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "image_url": "r2://bucket/path/to/scene.png",
      "object_name": "headphone",
      "seed": 42
    }
  }'
```

| Field | Required | Description |
|-------|----------|-------------|
| `image_url` | Yes | Image to segment. HTTPS URL or `r2://` reference. |
| `object_name` | Yes | Object to detect and mask (e.g. `"headphone"`, `"shoe"`, `"bottle"`). |
| `seed` | No | Random seed (default: random). |

The output is a composite image showing the detected mask overlaid on the original image in red.
