import os
import boto3
from botocore.config import Config

# This script generates a secure, 24-hour temporary download link
# for your dataset.zip file sitting in Cloudflare R2.
# It then prints out the exact JSON you need for the RunPod Dashboard.

def get_url_and_payload():
    # Load your R2 keys from your environment variables
    endpoint_url = os.environ.get("R2_ENDPOINT_URL")
    access_key = os.environ.get("R2_ACCESS_KEY_ID")
    secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")
    
    bucket_name = "exp-train-dataset"
    file_key = "dataset.zip"

    if not all([endpoint_url, access_key, secret_key]):
        print("Error: R2 environment variables are missing.")
        print("Make sure R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY are set.")
        return

    try:
        # Connect to R2
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
        
        # Generate the temporary link (valid for 24 hours)
        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": file_key},
            ExpiresIn=86400,
        )
        
        print("\n--- ✅ SUCCESS! ---")
        print("Your dataset URL was generated successfully.")
        print("\n--- 📋 COPY THIS INTO THE RUNPOD JSON BOX ---")
        
        json_payload = f"""{{
    "input": {{
        "dataset_url": "{presigned_url}",
        "lora_name": "my_first_flux_model",
        "trigger_word": "TOK",
        "r2_bucket": "exp-models"
    }}
}}"""
        print(json_payload)
        print("\n-------------------------------------------")
        print("Instructions:")
        print("1. Copy the JSON block starting from the first '{' to the last '}'.")
        print("2. Go to your RunPod Serverless dashboard -> click your endpoint name.")
        print("3. Click the 'Run' tab.")
        print("4. Paste the JSON into the 'Request' box and click 'Run'!")
        
    except Exception as e:
        print(f"Error generating URL: {e}")

if __name__ == "__main__":
    get_url_and_payload()
