# WWAA Flux Kontext LoRA Dataset Creation Workflow v1.5

## Required Models

| Node | File | Folder |
|---|---|---|
| UNETLoader | `flux1-dev-kontext_fp8_scaled.safetensors` | `models/unet/` |
| DualCLIPLoader | `t5xxl_fp8_e4m3fn.safetensors` | `models/clip/` |
| DualCLIPLoader | `clip_l.safetensors` | `models/clip/` |
| VAELoader | `ae.safetensors` | `models/vae/` |

---

## Setup Steps

### 1. Create model folders

```bash
mkdir -p /workspace/runpod-slim/ComfyUI/models/unet
mkdir -p /workspace/runpod-slim/ComfyUI/models/clip
mkdir -p /workspace/runpod-slim/ComfyUI/models/vae
```

### 2. Download models

```bash
wget -O /workspace/runpod-slim/ComfyUI/models/unet/flux1-dev-kontext_fp8_scaled.safetensors "https://huggingface.co/Comfy-Org/flux1-kontext-dev_ComfyUI/resolve/main/split_files/diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors"

wget -O /workspace/runpod-slim/ComfyUI/models/clip/t5xxl_fp8_e4m3fn.safetensors "https://huggingface.co/Comfy-Org/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors"

wget -O /workspace/runpod-slim/ComfyUI/models/clip/clip_l.safetensors "https://huggingface.co/Comfy-Org/flux_text_encoders/resolve/main/clip_l.safetensors"

wget -O /workspace/runpod-slim/ComfyUI/models/vae/ae.safetensors "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors"
```

> **Note:** `ae.safetensors` is on a gated Black Forest Labs repo. You need a HuggingFace account and must accept their license. If you get a 401 error, add your token:
> ```bash
> wget --header="Authorization: Bearer YOUR_HF_TOKEN" -O /workspace/runpod-slim/ComfyUI/models/vae/ae.safetensors "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors"
> ```

### 3. Install required custom nodes

Install via ComfyUI Manager:

- **wwaa-customnodes** — provides `WWAA_BuildString`, `WWAA_DisplayAny`, and `WWAA_AdvancedTextFileReader` nodes

### 4. Set up the prompts file

The `WWAA_AdvancedTextFileReader` node reads prompts one line at a time from a `.txt` file. Download a ready-made prompts file:

```bash
wget -O /workspace/woman-lora-prompts.txt "https://storage.googleapis.com/train-1234435345/trainingPrompts.txt"
```

Or create your own — one prompt per line, each describing the subject in a different pose, angle, lighting or outfit.

Verify it downloaded correctly:
```bash
wc -l /workspace/woman-lora-prompts.txt
```

Then in the `WWAA_AdvancedTextFileReader` node, set the file path to:
```
/workspace/woman-lora-prompts.txt
```

> **Important:** The path must start with `/`. Using a relative path like `workspace/...` will cause a "File not found" error.

### 5. Configure the node for sequential mode

In the `WWAA_AdvancedTextFileReader` node, change the mode from `random` to `sequential`. This ensures each prompt is used once in order rather than repeating randomly.

---

## Running the workflow

1. Load your reference photo into the `LoadImage` node
2. Set the queue count (top right in ComfyUI) to match the number of lines in your prompts file (e.g. `30`)
3. Hit **Run** — it will generate one image per prompt automatically

Each image will keep the subject's identity from your reference photo while varying the pose, angle, lighting, and outfit based on the prompt. This is the intended behavior for LoRA dataset creation.

---

## How it works

- **Flux Kontext** takes your reference image and uses it to keep the subject's identity consistent across all generated images
- The prompts file drives the variation — pose, angle, lighting, clothing
- The `WWAA_BuildString` node appends a suffix to every prompt (e.g. to strip jewelry)
- The `WWAA_DisplayAny` nodes let you preview the current prompt and total line count while running

---

## Troubleshooting

| Error | Fix |
|---|---|
| `File not found: workspace/...` | Path is missing leading `/` — use `/workspace/woman-lora-prompts.txt` |
| Same image every run | Change node mode from `random` to `sequential`, queue multiple runs |
| Red nodes on load | Models are missing or in wrong folder — check paths above |
| `ae.safetensors` 401 error | Requires HuggingFace login and license acceptance on Black Forest Labs repo |

---

## Notes

- The Flux Kontext model is ~12 GB — download will take time
- `t5xxl`, `clip_l`, and `ae.safetensors` are shared with standard Flux workflows — skip if already downloaded
