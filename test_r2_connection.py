import os
import boto3
from botocore.config import Config

# This script helps verify your Cloudflare R2 connection
# Ensure these environment variables are set before running:
# R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY

def test_connection():
    endpoint_url = os.environ.get("R2_ENDPOINT_URL")
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")

    if not all([endpoint_url, access_key, secret_key]):
        print("Error: Missing environment variables.")
        print("Please set R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY.")
        return

    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
        
        print(f"Connecting to: {endpoint_url}")
        buckets = s3.list_buckets()
        print("\nSuccessfully connected to R2!")
        print("Your buckets:")
        for bucket in buckets['Buckets']:
            print(f" - {bucket['Name']}")
            
    except Exception as e:
        print(f"\nConnection failed!")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_connection()
