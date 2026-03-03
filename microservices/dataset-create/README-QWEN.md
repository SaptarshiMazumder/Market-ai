# Dataset Gen - QWEN Image Edit v4

Generates dataset images using QWEN's instruction-based image editing model.
Takes a reference image and applies pose/angle prompts from a list, editing the image directly using text instructions.
Uses a 4-step Lightning LoRA for fast inference.

---

## Required Models

| Node | File | Folder |
|---|---|---|
| UNETLoader | `qwen_image_edit_2509_fp8_e4m3fn.safetensors` | `models/unet/` |
| CLIPLoader | `qwen_2.5_vl_7b_fp8_scaled.safetensors` | `models/clip/` |
| VAELoader | `qwen_image_vae.safetensors` | `models/vae/` |
| LoraLoader | `Qwen-Image-Lightning-4steps-V1.0.safetensors` | `models/loras/` |
| LoraLoader | `lenovoqwen.safetensors` | `models/loras/` |

> **Note:** `lenovoqwen.safetensors` is a custom LoRA not publicly available — you need to supply this yourself.

---

## Setup on RunPod Pod

### 1. Create folders

```bash
mkdir -p /workspace/runpod-slim/ComfyUI/models/unet
mkdir -p /workspace/runpod-slim/ComfyUI/models/clip
mkdir -p /workspace/runpod-slim/ComfyUI/models/vae
mkdir -p /workspace/runpod-slim/ComfyUI/models/loras
```

### 2. Download models

```bash
# Diffusion model (~20 GB)
wget -O /workspace/runpod-slim/ComfyUI/models/unet/qwen_image_edit_2509_fp8_e4m3fn.safetensors \
  "https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/diffusion_models/qwen_image_edit_2509_fp8_e4m3fn.safetensors"

# Text encoder / vision language model (~9.4 GB)
wget -O /workspace/runpod-slim/ComfyUI/models/clip/qwen_2.5_vl_7b_fp8_scaled.safetensors \
  "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors"

# VAE
wget -O /workspace/runpod-slim/ComfyUI/models/vae/qwen_image_vae.safetensors \
  "https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors"

# Lightning LoRA (4-step fast inference)
wget -O /workspace/runpod-slim/ComfyUI/models/loras/Qwen-Image-Lightning-4steps-V1.0.safetensors \
  "https://huggingface.co/Comfy-Org/Qwen-Image-Edit_ComfyUI/resolve/main/split_files/loras/Qwen-Image-Edit-2509-Light-Migration.safetensors"
```

> Upload `lenovoqwen.safetensors` manually to `/workspace/runpod-slim/ComfyUI/models/loras/`

### 3. Verify downloads

```bash
ls -lh /workspace/runpod-slim/ComfyUI/models/unet/
ls -lh /workspace/runpod-slim/ComfyUI/models/clip/
ls -lh /workspace/runpod-slim/ComfyUI/models/vae/
ls -lh /workspace/runpod-slim/ComfyUI/models/loras/
```

---

## Running the Workflow

1. Load the workflow JSON into ComfyUI
2. Load your reference photo into the `LoadImage` node
3. The `CR Prompt List` node contains 20 built-in pose/angle prompts — no file needed
4. Set the `TextEncodeQwenImageEditPlus` node instruction to describe the edit you want applied to every image
5. Set queue count to `20` (one per prompt in the list)
6. Hit **Run**

### Key settings (KSampler)

| Setting | Value |
|---|---|
| Steps | 4 (Lightning LoRA — do not increase significantly) |
| Sampler | euler |
| Scheduler | beta |
| CFG | 1 |

---

## How it works

- `CR Prompt List` cycles through 20 pose/angle descriptions
- `StringConcatenate` combines the pose prompt with the character name
- `TextEncodeQwenImageEditPlus` sends the edit instruction to the QWEN model
- `ModelSamplingAuraFlow` handles QWEN's specific sampling requirements
- `SaveImageKJ` saves outputs with `.txt` caption sidecar files automatically

---

## Troubleshooting

| Error | Fix |
|---|---|
| Red nodes on load | Models missing or wrong folder — check paths above |
| Out of memory | Need at least 24 GB VRAM for the full model stack |
| Slow generation | Normal — QWEN edit model is large; Lightning LoRA keeps it to 4 steps |
| `lenovoqwen` not found | Upload the file manually to `models/loras/` |
