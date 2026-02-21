import os
import requests
from google.cloud import storage

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
MODELS_PREFIX = "models"


def _bucket():
    client = storage.Client(project=GCP_PROJECT_ID)
    return client.bucket(GCS_BUCKET_NAME)


def upload_weights(model_name, version_hash, weights_url):
    """
    Download LoRA weights from Replicate and upload to GCS.
    Returns the public GCS URL.
    """
    print(f"[GCS] Downloading weights for {model_name}...")
    resp = requests.get(weights_url, stream=True, timeout=300)
    resp.raise_for_status()

    blob_path = f"{MODELS_PREFIX}/{model_name}/{version_hash}/weights.tar"
    blob = _bucket().blob(blob_path)
    blob.upload_from_string(resp.content, content_type="application/x-tar")

    gcs_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{blob_path}"
    print(f"[GCS] Uploaded weights → {gcs_url}")
    return gcs_url
