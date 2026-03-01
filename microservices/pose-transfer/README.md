# Pose Transfer Serverless Worker

ComfyUI-based pose transfer worker running on RunPod Serverless with Qwen Image Edit + InstantX ControlNet.

## Models on Network Volume

| Model | Path on Volume | Source |
|-------|---------------|--------|
| Diffusion model | `models/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors` | `Comfy-Org/Qwen2.5-VL-ComfyUI` |
| VAE | `models/vae/qwen_image_vae.safetensors` | `Comfy-Org/Qwen2.5-VL-ComfyUI` |
| Text encoder | `models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` | `Comfy-Org/Qwen2.5-VL-ComfyUI` |
| Lightning LoRA | `models/loras/Qwen-Image-Lightning-4steps-V1.0.safetensors` | `InstantX/Qwen-Image-Lightning` |
| ControlNet | `models/controlnet/Qwen-Image-InstantX-ControlNet-Union.safetensors` | `InstantX/Qwen-Image-ControlNet-Union` |
| DWPose | `models/controlnet/dw-ll_ucoco_384_bs5.torchscript.pt` | `yzd-v/DWPose` |
| YOLOX-L | `models/controlnet/yolox_l.onnx` | `yzd-v/DWPose` |

## Setting Up the Network Volume

1. Create a RunPod **Pod** (not Serverless) with your network volume attached.
2. SSH in or open the web terminal.
3. Run the commands below.
4. Terminate the pod when done — files persist on the volume.

### Create directories

```bash
mkdir -p /workspace/models/diffusion_models
mkdir -p /workspace/models/vae
mkdir -p /workspace/models/text_encoders
mkdir -p /workspace/models/loras
mkdir -p /workspace/models/controlnet
```

### Download models

Most repos are gated — set your HuggingFace token first:

```bash
export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxx"
```

Diffusion model:

```bash
wget --header="Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/Comfy-Org/Qwen2.5-VL-ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors" \
  -O /workspace/models/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors
```

VAE:

```bash
wget --header="Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/Comfy-Org/Qwen2.5-VL-ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors" \
  -O /workspace/models/vae/qwen_image_vae.safetensors
```

Text encoder:

```bash
wget --header="Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" \
  -O /workspace/models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors
```

Lightning LoRA: 

```bash
wget --header="Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/lightx2v/Qwen-Image-Lightning/resolve/main/Qwen-Image-Lightning-4steps-V1.0.safetensors" \
  -O /workspace/models/loras/Qwen-Image-Lightning-4steps-V1.0.safetensors
```

ControlNet:

```bash
wget --header="Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/Comfy-Org/Qwen-Image-InstantX-ControlNets/resolve/main/split_files/controlnet/Qwen-Image-InstantX-ControlNet-Union.safetensors" \
  -O /workspace/models/controlnet/Qwen-Image-InstantX-ControlNet-Union.safetensors
```

DWPose + YOLOX (for pose extraction):

```bash
wget --header="Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/yzd-v/DWPose/resolve/main/dw-ll_ucoco_384_bs5.torchscript.pt" \
  -O /workspace/models/controlnet/dw-ll_ucoco_384_bs5.torchscript.pt

wget --header="Authorization: Bearer $HF_TOKEN" \
  "https://huggingface.co/yzd-v/DWPose/resolve/main/yolox_l.onnx" \
  -O /workspace/models/controlnet/yolox_l.onnx
```

### Verify

```bash
find /workspace/models -type f | sort
```

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
docker build -t raj1145/qwen-pose-transfer-worker:latest .
docker push raj1145/qwen-pose-transfer-worker:latest
```

Then create a Serverless endpoint on RunPod with:
- **Container Image**: `raj1145/qwen-pose-transfer-worker:latest`
- **GPU**: RTX 4090 or better (24 GB+ VRAM)
- **Network Volume**: the volume with the models above

## API Usage

```bash
curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "input_image": "r2://bucket/path/to/subject.png",
      "pose_image": "r2://bucket/path/to/pose_reference.png"
    }
  }'
```

| Field | Required | Description |
|-------|----------|-------------|
| `input_image` | Yes | The subject image to be edited. HTTPS URL or `r2://` reference. |
| `pose_image` | Yes | The reference image to extract the pose from. HTTPS URL or `r2://` reference. |
