import os
import time
from pathlib import Path
from google import genai
from google.genai import types
from PIL import Image


# Folder containing your .jpg, .png, or .webp images
IMAGE_FOLDER = "./training_data_2" 

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_caption(image_path, trigger_word):
    """Sends image to Gemini to generate a LoRA-specific caption."""
    
    prompt = f"""
    Analyze this image and provide a highly detailed, one-sentence caption for LoRA training.
    
    RULES:
    1. Start or feature the subject as '{trigger_word}'.
    2. Describe the shot angle (e.g., medium shot, close-up, profile view).
    3. Describe the subject's clothes and expression, but never mention their hair color or hairstyle."
    4. Describe the background and lighting (e.g., studio background, golden hour, indoor hallway).
    5. Use natural language, not just tags.
    
    EXAMPLE STYLE:
    "A side profile portrait of {trigger_word} looking over her shoulder, long wavy red hair, wearing a black bikini top against a neutral studio background."
    """

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            ]
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

def main():
    trigger_word = input("Enter your Trigger Word (e.g., TOKREDGIRL): ").strip()
    if not trigger_word:
        print("Trigger word is required!")
        return

    image_extensions = (".png", ".jpg", ".jpeg", ".webp")
    image_files = [f for f in os.listdir(IMAGE_FOLDER) if f.lower().endswith(image_extensions)]

    print(f"Found {len(image_files)} images. Starting captioning...")

    for filename in image_files:
        image_path = os.path.join(IMAGE_FOLDER, filename)
        txt_path = Path(image_path).with_suffix(".txt")

        # Skip if .txt already exists to save API credits
        if txt_path.exists():
            print(f"Skipping {filename} (caption already exists).")
            continue

        print(f"Captioning {filename}...")
        caption = generate_caption(image_path, trigger_word)

        if caption:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(caption)
            print(f"Successfully saved: {txt_path.name}")
        
        # Short sleep to avoid hitting rate limits on free tier
        time.sleep(1)

    print("\nProcessing complete! Your dataset is ready for fal.ai.")

if __name__ == "__main__":
    main()