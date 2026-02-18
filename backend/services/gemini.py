import os
import json
import google.generativeai as genai
from PIL import Image

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

GENERATION_PROMPT_SYSTEM = """You are an expert prompt engineer for Flux, a state-of-the-art AI image generation model fine-tuned with LoRA. Your goal is to produce ad-ready, commercial-grade marketing imagery.

Analyze the provided sample image of a product. Your job is to craft a detailed, optimized prompt that will produce a stunning, photorealistic, professional advertisement image — the kind you'd see in a Nike, Apple, or luxury brand campaign.

Critical requirements:
- The image MUST feature a real-looking human or avatar naturally interacting with, wearing, holding, or using the product — this is an advertisement, not a product-only shot
- Choose an appropriate lifestyle context: someone using the product in a real-world scenario (street, studio, gym, outdoors, workspace, etc.)
- The person should look natural, aspirational, and on-brand for the product category
- The scale and proportion of the product relative to the human MUST be realistic — e.g., a watch should fit on a wrist, a shoe should be foot-sized, a phone should be hand-sized. Never exaggerate or shrink the product unnaturally

Prompt guidelines:
- Write a single detailed prompt paragraph (no bullet points)
- Describe the product from the image accurately and how the person is interacting with it
- Specify the model/person: age range, style, pose, expression, wardrobe
- Include cinematic lighting details: golden hour, studio softbox, natural window light, etc.
- Specify camera: shot on Canon EOS R5, 85mm lens, shallow depth of field, etc.
- Include environment and mood: aspirational, energetic, luxurious, minimal, urban, etc.
- If a trigger word is provided, you MUST use ONLY that trigger word to refer to the product throughout the entire prompt — never describe the product by its actual name or type, always substitute the trigger word instead. This is critical for activating the LoRA fine-tune
- Include quality boosters: "8k uhd", "award-winning advertising photography", "editorial", "sharp focus", "professional color grading"
- Keep it under 250 words
- Do NOT include negative prompts — just the positive prompt

Respond with ONLY the prompt text, nothing else. No quotes, no labels, no explanation."""

UPSCALER_PROMPT_SYSTEM = """You are an image enhancement specialist. Analyze the provided image and generate a prompt and negative_prompt for an AI upscaler to enhance this image with maximum realism.

Your goals for the prompt:
- Increase photorealism and natural appearance
- Reduce excessive contrast and saturation
- Remove any plastic, artificial, or CGI-looking skin
- Add realistic skin texture, pores, and natural imperfections
- Preserve the original composition and subject matter
- Enhance lighting to look natural and photographed

Respond ONLY with valid JSON in this exact format, no other text:
{"prompt": "your enhancement prompt here", "negative_prompt": "your negative prompt here"}"""


def generate_prompt(image_path, trigger_word=""):
    """Use Gemini to analyze a sample image and generate an optimized prompt."""
    img = Image.open(image_path)

    user_input = GENERATION_PROMPT_SYSTEM
    if trigger_word:
        user_input += f"\n\nIMPORTANT: The trigger word is \"{trigger_word}\". Use ONLY this word to refer to the product — never use the product's actual name or category. For example, instead of 'a sleek wireless headphone', write 'a sleek {trigger_word}'."

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content([user_input, img])
    generated_prompt = response.text.strip()

    print(f"[PromptGen] Trigger: {trigger_word}")
    print(f"[PromptGen] Output: {generated_prompt}")

    return generated_prompt


def generate_upscale_prompts(image_path):
    """Use Gemini to analyze the image and generate upscaler prompts."""
    model = genai.GenerativeModel("gemini-2.0-flash")
    img = Image.open(image_path)

    response = model.generate_content([UPSCALER_PROMPT_SYSTEM, img])
    text = response.text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    parsed = json.loads(text)
    return parsed["prompt"], parsed["negative_prompt"]
