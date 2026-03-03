import os
import uuid
import boto3
from botocore.config import Config

R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_OUTPUT_BUCKET = os.environ.get("R2_OUTPUT_BUCKET", "")


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


def upload_image(file_bytes: bytes, original_filename: str) -> str:
    """Upload an image to R2 and return its r2:// path."""
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "png"
    key = f"mask-inputs/{uuid.uuid4()}.{ext}"
    _client().put_object(
        Bucket=R2_OUTPUT_BUCKET,
        Key=key,
        Body=file_bytes,
        ContentType=f"image/{ext}",
    )
    return f"r2://{R2_OUTPUT_BUCKET}/{key}"


def _list_images(prefix: str, limit: int = 50) -> list:
    """List images in R2 under a prefix, sorted newest first. Returns [{r2_path, preview_url}]."""
    client = _client()
    resp = client.list_objects_v2(Bucket=R2_OUTPUT_BUCKET, Prefix=prefix)
    objects = resp.get("Contents", [])
    objects.sort(key=lambda o: o["LastModified"], reverse=True)
    result = []
    for obj in objects[:limit]:
        key = obj["Key"]
        preview_url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": R2_OUTPUT_BUCKET, "Key": key},
            ExpiresIn=3600,
        )
        result.append({
            "r2_path": f"r2://{R2_OUTPUT_BUCKET}/{key}",
            "preview_url": preview_url,
        })
    return result


def list_masked_images() -> list:
    return _list_images("masks/")


def list_product_images() -> list:
    return _list_images("products/")
