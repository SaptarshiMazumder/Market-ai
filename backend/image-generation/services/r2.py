import os
import boto3
from botocore.config import Config

R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
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


def download_image(r2_path: str) -> bytes:
    """Download a generated image from R2.
    Accepts r2://bucket/key format or a bare key (uses R2_OUTPUT_BUCKET).
    """
    if r2_path.startswith("r2://"):
        parts = r2_path[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1]
    else:
        bucket = R2_OUTPUT_BUCKET
        key = r2_path

    response = _client().get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
