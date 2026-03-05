import json
import os

from google import genai
from google.genai import types

GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
REVIEW_THRESHOLD = 6.5

_gemini = genai.Client(api_key=GEMINI_API_KEY)


def review(mask_bytes: bytes, subject: str, product_bytes: bytes | None = None) -> dict:
    """
    Review mask quality.
    If product_bytes is provided, the review also considers whether the mask edges
    are appropriate for the type of product being inpainted.
    """
    if product_bytes:
        prompt = (
            f"You are reviewing an AI-generated mask for product inpainting. Subject: '{subject}'.\n\n"
            f"Image 1: the mask image (white = masked area to be replaced).\n"
            f"Image 2: the actual product that will be inpainted into the masked region.\n\n"
            f"Score 0–10 based on:\n"
            f"1. Is the subject '{subject}' fully covered by the mask (no gaps)?\n"
            f"2. Are the mask edges appropriate for the product type? "
            f"(Hard-edged products like bags/shoes need crisp edges; soft clothing can tolerate moderate blur)\n"
            f"3. Is the mask contiguous and not fragmented?\n"
            f"4. Is dilation reasonable — enough margin for clean inpainting, not bleeding into background?\n\n"
            f"Reply ONLY with valid JSON: {{\"score\": <float>, \"reason\": \"<one sentence>\"}}"
        )
        contents = [
            types.Part.from_bytes(data=mask_bytes, mime_type="image/png"),
            types.Part.from_bytes(data=product_bytes, mime_type="image/png"),
            prompt,
        ]
    else:
        prompt = (
            f"You are a quality reviewer for AI-generated image masks. Subject: '{subject}'.\n\n"
            f"Score this mask image 0–10 based on:\n"
            f"1. Is the subject ({subject}) properly isolated in the mask?\n"
            f"2. Are the mask edges clean (not too blurry or fragmented)?\n"
            f"3. Is the mask contiguous (not broken into many pieces)?\n\n"
            f"Reply ONLY with valid JSON: {{\"score\": <float>, \"reason\": \"<one sentence>\"}}"
        )
        contents = [
            types.Part.from_bytes(data=mask_bytes, mime_type="image/png"),
            prompt,
        ]

    response = _gemini.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
    )
    raw = response.text.strip().strip("```json").strip("```").strip()
    data = json.loads(raw)
    score = float(data["score"])
    return {"score": score, "reason": data.get("reason", ""), "passed": score >= REVIEW_THRESHOLD}
