import os
import boto3
from botocore.config import Config

R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_INPUT_BUCKET = os.environ.get("R2_INPUT_BUCKET", "objects-to-train")
R2_OUTPUT_BUCKET = os.environ.get("R2_OUTPUT_BUCKET", "test-ftp")


def _client():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def lora_exists(model_name: str) -> str | None:
    """Check if a trained LoRA exists in the output bucket.
    Returns the R2 key if found, None otherwise."""
    key = f"{model_name}.safetensors"
    try:
        _client().head_object(Bucket=R2_OUTPUT_BUCKET, Key=key)
        return key
    except Exception:
        return None


def upload_dataset(key: str, file_obj) -> str:
    """Upload a zip file to the input bucket and return a 24-hour presigned URL."""
    client = _client()
    client.upload_fileobj(file_obj, R2_INPUT_BUCKET, key)
    presigned_url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": R2_INPUT_BUCKET, "Key": key},
        ExpiresIn=86400,  # 24 hours
    )
    return presigned_url
