# RunPod Serverless Flux LoRA Trainer

Serverless RunPod endpoint that trains Flux LoRA models using [ai-toolkit](https://github.com/ostris/ai-toolkit).

## How It Works

1. Submit a job with a dataset URL and training config
2. Worker downloads the dataset, trains a LoRA using ai-toolkit
3. Trained `.safetensors` is uploaded to Cloudflare R2
4. Job response returns the R2 path of the trained model

FLUX.1-dev (~33 GB) is cached on a RunPod network volume so it only downloads once.

## Build & Push

```bash
# Handled automatically by GitHub Actions on push to experimental
# Or manual build:
docker build -t marcusrashford/flux-exp-trainer:latest .
docker push marcusrashford/flux-exp-trainer:latest
```

## RunPod Endpoint Setup

| Setting            | Value                             |
| ------------------ | --------------------------------- |
| Image              | `marcusrashford/flux-exp-trainer:latest`     |
| GPU                | 24 GB+ (RTX 4090 / A40 / L40)    |
| Network Volume     | Attach for FLUX.1-dev cache       |
| Env: `HF_TOKEN`   | HuggingFace read token            |
| Env: `R2_ACCOUNT_ID` | Cloudflare account ID          |
| Env: `R2_ACCESS_KEY_ID` | R2 access key               |
| Env: `R2_SECRET_ACCESS_KEY` | R2 secret key           |
| Env: `R2_BUCKET`  | Default R2 bucket for output      |
| Execution Timeout  | 3600 s                            |
| Flash Boot         | Disabled                          |

## Submit a Training Job

```bash
curl -X POST "https://api.runpod.ai/v2/<ENDPOINT_ID>/run" \
  -H "Authorization: Bearer <RUNPOD_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "dataset_url": "https://example.com/dataset.zip",
      "r2_bucket": "test-ftp",
      "lora_name": "my_model",
      "trigger_word": "TOK",
      "steps": 2000,
      "lr": 1e-4,
      "resolution": [512, 768, 1024],
      "lora_rank": 16,
      "batch_size": 1,
      "sample_every": 500,
      "save_every": 500
    }
  }'
```

## Check Job Status

```bash
curl "https://api.runpod.ai/v2/<ENDPOINT_ID>/status/<JOB_ID>" \
  -H "Authorization: Bearer <RUNPOD_API_KEY>"
```

## Input Parameters

| Parameter          | Required | Default   | Description                                      |
| ------------------ | -------- | --------- | ------------------------------------------------ |
| `dataset_url`      | Yes      | —         | Public/signed URL to a zip of image+caption pairs |
| `r2_bucket`        | Yes      | —         | R2 bucket name for the trained model              |
| `r2_prefix`        | No       | —         | Path prefix within bucket for the output          |
| `lora_name`        | No       | lora_output | Name for the LoRA                               |
| `trigger_word`     | No       | TOK       | Trigger word baked into the LoRA                  |
| `steps`            | No       | 2000      | Training steps                                    |
| `lr`               | No       | 1e-4      | Learning rate                                     |
| `resolution`       | No       | [512,768,1024] | Training resolutions                         |
| `lora_rank`        | No       | 16        | LoRA rank                                         |
| `batch_size`       | No       | 1         | Batch size                                        |
| `sample_every`     | No       | 500       | Generate samples every N steps                    |
| `save_every`       | No       | 500       | Save checkpoint every N steps                     |

## Dataset Format

Zip file containing image + caption pairs:

```
dataset.zip
├── photo1.jpg
├── photo1.txt      # "a photo of TOK on a white background"
├── photo2.png
├── photo2.txt      # "TOK product shot, studio lighting"
└── ...
```

Supported image formats: `.jpg`, `.jpeg`, `.png`, `.webp`
