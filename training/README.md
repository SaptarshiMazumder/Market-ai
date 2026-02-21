# RunPod Serverless Flux LoRA Trainer

Serverless RunPod endpoint that trains Flux LoRA models using [ai-toolkit](https://github.com/ostris/ai-toolkit).

## How It Works

1. Submit a job with a GCS dataset URL and training config
2. Worker downloads the dataset, trains a LoRA using ai-toolkit
3. Trained `.safetensors` is uploaded to your GCS bucket
4. Job response returns the GCS URL of the trained model

FLUX.1-dev (~33 GB) is cached on a RunPod network volume so it only downloads once.

## Build & Push

```bash
docker build -t raj1145/flux-tok-trainer:v1 .
docker push raj1145/flux-tok-trainer:v1
```

## RunPod Endpoint Setup

| Setting            | Value                             |
| ------------------ | --------------------------------- |
| Image              | `raj1145/flux-tok-trainer:v1`     |
| GPU                | 24 GB+ (RTX 4090 / A40 / L40)    |
| Network Volume     | Attach for FLUX.1-dev cache       |
| Env: `HF_TOKEN`   | HuggingFace read token            |
| Execution Timeout  | 3600 s                            |
| Flash Boot         | Disabled                          |

For GCS uploads, either:
- Set `GOOGLE_APPLICATION_CREDENTIALS` env var pointing to a service account JSON on the volume, or
- Mount a service account key and set the env var accordingly.

## Submit a Training Job

```bash
curl -X POST "https://api.runpod.ai/v2/<ENDPOINT_ID>/run" \
  -H "Authorization: Bearer <RUNPOD_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "dataset_gcs_url": "https://storage.googleapis.com/your-bucket/dataset.zip",
      "output_gcs_bucket": "your-bucket",
      "output_gcs_path": "trained_loras/myProd_v2.safetensors",
      "lora_name": "myProd_v2",
      "trigger_word": "MY_PROD",
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
| `dataset_gcs_url`  | Yes      | —         | Public/signed URL to a zip of image+caption pairs |
| `output_gcs_bucket`| Yes      | —         | GCS bucket name for the trained model             |
| `output_gcs_path`  | No       | auto      | Path within bucket for the output safetensors     |
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
├── photo1.txt      # "a photo of MY_PROD on a white background"
├── photo2.png
├── photo2.txt      # "MY_PROD product shot, studio lighting"
└── ...
```

Supported image formats: `.jpg`, `.jpeg`, `.png`, `.webp`
