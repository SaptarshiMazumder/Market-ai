# WWAA Flux Kontext LoRA Dataset Creation Workflow v1.5

Generates identity-consistent dataset images from a single reference photo using Flux1 Kontext Dev.
Each run produces one image per prompt, keeping the subject's face/identity consistent while varying pose, angle, and lighting.

---

## Required Models

| Node | File | Folder |
|---|---|---|
| UNETLoader | `flux1-dev-kontext_fp8_scaled.safetensors` | `models/unet/` |
| DualCLIPLoader | `t5xxl_fp8_e4m3fn.safetensors` | `models/clip/` |
| DualCLIPLoader | `clip_l.safetensors` | `models/clip/` |
| VAELoader | `ae.safetensors` | `models/vae/` |

## Required Custom Nodes

- **wwaa-customnodes** — provides `WWAA_BuildString`, `WWAA_DisplayAny`, `WWAA_AdvancedTextFileReader`

Install via ComfyUI Manager.

---

## Setup on RunPod Pod

### 1. Create folders

```bash
mkdir -p /workspace/runpod-slim/ComfyUI/models/unet
mkdir -p /workspace/runpod-slim/ComfyUI/models/clip
mkdir -p /workspace/runpod-slim/ComfyUI/models/vae
```

### 2. Download models

```bash
wget -O /workspace/runpod-slim/ComfyUI/models/unet/flux1-dev-kontext_fp8_scaled.safetensors \
  "https://huggingface.co/Comfy-Org/flux1-kontext-dev_ComfyUI/resolve/main/split_files/diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors"

wget -O /workspace/runpod-slim/ComfyUI/models/clip/t5xxl_fp8_e4m3fn.safetensors \
  "https://huggingface.co/Comfy-Org/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors"

wget -O /workspace/runpod-slim/ComfyUI/models/clip/clip_l.safetensors \
  "https://huggingface.co/Comfy-Org/flux_text_encoders/resolve/main/clip_l.safetensors"

wget --header="Authorization: Bearer YOUR_HF_TOKEN" \
  -O /workspace/runpod-slim/ComfyUI/models/vae/ae.safetensors \
  "https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors"
```

> `ae.safetensors` is on a gated repo — you need a HuggingFace account and must accept the Black Forest Labs license. Replace `YOUR_HF_TOKEN` with your token from https://huggingface.co/settings/tokens

### 3. Create the prompts file

```bash
cat > /workspace/prompts.txt << 'EOF'
Photorealistic profile view of the subject's face from the left, against a plain white wall background.
Hyperrealistic profile view of the subject's face from the right, against a clean white wall.
DSLR photograph, three-quarter view of the subject's face, looking towards the camera, against a plain white wall.
Ultra-realistic three-quarter view of the subject, looking slightly away from the camera, against a seamless white wall.
Low-angle shot, looking up at the subject's face with a neutral expression, against a plain white wall.
High-angle shot, looking down at the subject's face, against a stark white wall.
Photorealistic headshot with the subject's head tilted slightly to the side, looking directly at the camera, against a white wall.
Hyperrealistic shot of the subject looking over their shoulder at the camera, against a white wall background.
Dramatic Rembrandt lighting portrait, with one side of the subject's face illuminated, from a three-quarter angle against a white wall.
Extreme close-up shot from a slight angle, focusing on the subject's facial features, against a white wall.
Photorealistic headshot with a slight Dutch angle, where the camera is tilted, against a plain white wall background.
DSLR photo of the subject looking up and away, past the camera, in a three-quarter turn against a white wall.
Ultra-realistic shot of the subject looking down and to the side, with their face angled away from the camera, against a white wall.
Hyperrealistic shot from behind the subject, as they turn their head to the side to look towards the camera, against a white wall.
Photorealistic portrait from a 45-degree angle, showing the face and shoulders, against a seamless white wall.
Macro shot from a three-quarter perspective, with a shallow depth of field focusing sharply on the subject's eyes, against a white wall.
Worm's-eye view looking directly up at the subject's chin and face, against a plain white wall.
Bird's-eye view looking directly down on the top of the subject's head as they look up towards the camera, against a white wall.
Photorealistic shot of the subject with their head tilted back, exposing the neck and looking upwards, against a white wall.
Realistic headshot with the subject's chin tucked down, looking up at the camera from under their brow, against a white wall.
EOF
```

Verify:
```bash
wc -l /workspace/prompts.txt
head -2 /workspace/prompts.txt
```

---

## Running the Workflow

1. Load the workflow JSON into ComfyUI
2. Load your reference photo into the `LoadImage` node
3. In `WWAA_AdvancedTextFileReader`:
   - Set `file_path` to `/workspace/prompts.txt`
   - Set `traversal_mode` to `sequential`
   - Toggle `reload_file` to `true` once, then back to `false`
4. Set the queue count (top right in ComfyUI) to `20` (or however many lines are in your prompts file)
5. Hit **Run** — it generates one image per prompt automatically

---

## Troubleshooting

| Error | Fix |
|---|---|
| Same image every run | Change `traversal_mode` from `random` to `sequential` |
| Prompts not loading / blank output | Toggle `reload_file` to `true` once to force re-read |
| File path error | Path must start with `/` — use `/workspace/prompts.txt` not `workspace/...` |
| `ae.safetensors` 401 error | Requires HuggingFace login and license acceptance on Black Forest Labs repo |
| Red nodes on load | Models missing or in wrong folder — check paths above |
