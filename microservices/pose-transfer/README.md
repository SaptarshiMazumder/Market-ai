# Pose Transfer Worker — Model Downloads

Models are not baked into the Docker image. Run these commands on your RunPod
network volume (or inside the pod terminal) before the first job.

All paths are under `/comfyui/`.

---

## 1. Create directories

```bash
mkdir -p /comfyui/models/diffusion_models
mkdir -p /comfyui/models/vae
mkdir -p /comfyui/models/text_encoders
mkdir -p /comfyui/models/loras
mkdir -p /comfyui/models/controlnet
mkdir -p /comfyui/custom_nodes/comfyui_controlnet_aux/ckpts
```

---

## 2. Download models

### Qwen Image Edit diffusion model
Node: UNETLoader (ID 156)
Path: `models/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors`

```bash
wget -O /comfyui/models/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors \
  https://huggingface.co/Comfy-Org/Qwen2.5-VL-ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors
```

> Verify the exact URL on https://huggingface.co/Comfy-Org — search for "qwen_image_edit".

---

### Qwen Image VAE
Node: VAELoader (ID 148)
Path: `models/vae/qwen_image_vae.safetensors`

```bash
wget -O /comfyui/models/vae/qwen_image_vae.safetensors \
  https://huggingface.co/Comfy-Org/Qwen2.5-VL-ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors
```

---

### Qwen 2.5 VL text encoder
Node: CLIPLoader (ID 147)
Path: `models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors`

```bash
wget -O /comfyui/models/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors \
  https://huggingface.co/Comfy-Org/Qwen2.5-VL-ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors
```

---

### Qwen Image Lightning LoRA (4-step fast inference)
Node: LoraLoaderModelOnly (ID 159)
Path: `models/loras/Qwen-Image-Lightning-4steps-V1.0.safetensors`

```bash
wget -O /comfyui/models/loras/Qwen-Image-Lightning-4steps-V1.0.safetensors \
  https://huggingface.co/InstantX/Qwen-Image-Lightning/resolve/main/Qwen-Image-Lightning-4steps-V1.0.safetensors
```

> If this URL is wrong, search https://huggingface.co/InstantX for "Qwen Image Lightning".

---

### Qwen InstantX ControlNet Union
Node: ControlNetLoader (ID 167)
Path: `models/controlnet/Qwen-Image-InstantX-ControlNet-Union.safetensors`

```bash
wget -O /comfyui/models/controlnet/Qwen-Image-InstantX-ControlNet-Union.safetensors \
  https://huggingface.co/InstantX/Qwen-Image-ControlNet-Union/resolve/main/Qwen-Image-InstantX-ControlNet-Union.safetensors
```

> If this URL is wrong, search https://huggingface.co/InstantX for "Qwen Image ControlNet".

---

### DWPose model (for DWPreprocessor)
Node: DWPreprocessor (ID 165)
Path: `custom_nodes/comfyui_controlnet_aux/ckpts/dw-ll_ucoco_384_bs5.torchscript.pt`

```bash
wget -O /comfyui/custom_nodes/comfyui_controlnet_aux/ckpts/dw-ll_ucoco_384_bs5.torchscript.pt \
  https://huggingface.co/yzd-v/DWPose/resolve/main/dw-ll_ucoco_384_bs5.torchscript.pt
```

---

### YOLOX-L (for DWPreprocessor — may auto-download on first run)
Node: DWPreprocessor (ID 165)
Path: `custom_nodes/comfyui_controlnet_aux/ckpts/yolox_l.onnx`

```bash
wget -O /comfyui/custom_nodes/comfyui_controlnet_aux/ckpts/yolox_l.onnx \
  https://huggingface.co/yzd-v/DWPose/resolve/main/yolox_l.onnx
```

> `comfyui_controlnet_aux` may download these automatically on first inference.
> Check the ckpts folder after a test run before downloading manually.

---

## Handler API

### Inputs

| Field | Type | Description |
|-------|------|-------------|
| `input_image` | string (required) | R2 path or URL — the subject image to be edited |
| `pose_image` | string (required) | R2 path or URL — the reference image to extract the pose from |

Accepted formats for both fields:
- `r2://bucket-name/path/to/image.png`
- `https://<account>.r2.cloudflarestorage.com/bucket/key`
- Bare R2 key (uses `R2_INPUT_BUCKET` env var)

### Output

```json
{
  "images": [
    {
      "r2_path": "r2://<bucket>/generated/<uuid>_ComfyUI_xxxxx_.png",
      "key": "generated/<uuid>_ComfyUI_xxxxx_.png",
      "filename": "ComfyUI_xxxxx_.png"
    }
  ],
  "duration_seconds": 18.4
}
```

### Required environment variables

| Variable | Description |
|----------|-------------|
| `R2_ACCOUNT_ID` | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | R2 access key |
| `R2_SECRET_ACCESS_KEY` | R2 secret key |
| `R2_INPUT_BUCKET` | Bucket to read input images from |
| `R2_OUTPUT_BUCKET` | Bucket to write generated images to |
