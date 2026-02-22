import os
import sys
from services.r2 import upload_dataset
from services.runpod import submit_job, get_job_status
import time

# To use this script, ensure the following are in your environment:
# RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL

def start_training(local_zip_path, lora_name, trigger_word):
    print(f"--- Starting Training Process for: {lora_name} ---")
    
    # 1. Upload dataset to R2
    print(f"Step 1: Uploading {local_zip_path} to Cloudflare R2...")
    with open(local_zip_path, "rb") as f:
        dataset_url = upload_dataset(os.path.basename(local_zip_path), f)
    print(f"Upload complete. Dataset URL generated.")

    # 2. Submit job to RunPod
    print(f"Step 2: Submitting job to RunPod (Endpoint: {os.environ.get('RUNPOD_ENDPOINT_ID')})...")
    job_id = submit_job(dataset_url, lora_name, trigger_word)
    print(f"Job submitted! Job ID: {job_id}")

    # 3. Monitor
    print(f"Step 3: Monitoring progress (this will take 15-30 minutes)...")
    print(f"You can also check status here: https://www.runpod.io/console/serverless/endpoint/{os.environ.get('RUNPOD_ENDPOINT_ID')}/jobs")
    
    while True:
        status = get_job_status(job_id)
        current_state = status.get("status")
        print(f"Current Status: {current_state}")
        
        if current_state == "COMPLETED":
            print("\nSUCCESS! Training finished.")
            print(f"Your model should now be in your R2 bucket: {status.get('output', {}).get('model_url', 'Check R2')}")
            break
        elif current_state == "FAILED":
            print("\nERROR: Training failed.")
            print(f"Details: {status.get('error')}")
            break
            
        time.sleep(30) # Check every 30 seconds

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python start_training.py <path_to_zip> <lora_name> <trigger_word>")
        sys.exit(1)
        
    start_training(sys.argv[1], sys.argv[2], sys.argv[3])
