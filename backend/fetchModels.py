import replicate
import os

# 1. Set your API Token
os.environ["REPLICATE_API_TOKEN"] = "r8_UkYGYR2XOBk9AtgqXoutZjQHHvrHva53Lz0fI"
def fetch_trained_models():
    print(f"{'Trainer Model':<30} | {'Status':<12} | {'Your Model String (Run this!)'}")
    print("-" * 100)
    
    # 1. List all trainings (paginated automatically)
    trainings = replicate.trainings.list()
    
    for t in trainings:
        # 2. Filter for only the Ostris Flux trainer
        # Use the specific trainer ID from your screenshot
        if "ostris/flux-dev-lora-trainer" in t.model:
            status = t.status # succeeded, failed, or processing
            
            # 3. Only grab 'succeeded' ones to get the final version ID
            if status == "succeeded":
                # The format needed for inference is 'owner/model:version_hash'
                model_string = f"{t.destination}:{t.version}"
                print(f"{t.model:<30} | {status:<12} | {model_string}")
            else:
                print(f"{t.model:<30} | {status:<12} | (No version yet)")

if __name__ == "__main__":
    fetch_trained_models()