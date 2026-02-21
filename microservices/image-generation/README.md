# RunPod Flux Serverless Worker

Serverless ComfyUI endpoint on RunPod that generates images using Flux Dev + custom LoRAs.

---

## One-time Setup

### 1. Set your API key
```bash
export RUNPOD_API_KEY=your_runpod_api_key_here
```

### 2. Install Python dependencies
```bash
pip install requests
```

---

## Build & Deploy

### Build the Docker image
```bash
docker build -t raj1145/flux-tok-worker:v8 .
```

### Push to Docker Hub
```bash
docker push raj1145/flux-tok-worker:v8
```

### Update the RunPod endpoint
Go to RunPod → Serverless → `xenogeneic_black_dormouse` → Manage → update image tag → save.

---

## Run a Job

### With default LoRA
```bash
python run_job.py
```

### With a specific LoRA key
```bash
python run_job.py "r2://test-ftp/my_model.safetensors"
```

Output is saved as `output_0.png` in the current directory.

---

## Project Structure

```
runpod-flux-deploy/
├── Dockerfile          # Builds the worker image
├── handler.py          # Runs inside the container — downloads LoRA, runs workflow
├── LoraWorkflow.json   # ComfyUI workflow sent with each job
├── run_job.py          # Client script — submits job, polls, saves image
└── trained_loras/      # Local copies of your LoRA files
```

---

## RunPod Resources

| Resource | Value |
|---|---|
| Endpoint ID | `zotmmnshs1nxix` |
| Endpoint name | `xenogeneic_black_dormouse` |
| Docker image | `raj1145/flux-tok-worker:v7` |
| GPU | 80GB Pro (AP-JP-1) |
| Network volume | `flux_network_volume` — mounted at `/runpod-volume` |

### Network volume contents
```
/runpod-volume/models/
├── unet/flux1-dev.safetensors
├── vae/ae.safetensors
└── clip/
    ├── clip_l.safetensors
    └── t5xxl_fp16.safetensors
```

---

## Workflow Parameters (LoraWorkflow.json)

| Node | Setting | Current Value |
|---|---|---|
| KSampler | steps | 25 |
| KSampler | cfg | 1.0 |
| KSampler | scheduler | beta |
| EmptyLatentImage | resolution | 1024x1024 |
| LoraLoader | strength_model | 1.0 |
| LoraLoader | strength_clip | 1.0 |

---

## Notes

- **First request** with a new LoRA: handler downloads it + restarts ComfyUI (~2-3 min total)
- **Subsequent requests** with same LoRA on same worker: no download, no restart — fast
- To change the prompt, edit node `6` (positive) and node `7` (negative) in `LoraWorkflow.json`
- To migrate to a cheaper region (US-TX-3, 24GB GPU at $0.00019/s): delete and recreate the network volume in that region, re-download Flux models
