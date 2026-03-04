import json
import os

from google import genai
from google.genai import types

GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
REVIEW_THRESHOLD = 6.5

_gemini = genai.Client(api_key=GEMINI_API_KEY)


def review(image_bytes: bytes, subject: str) -> dict:
    prompt = (
        f"You are a quality reviewer for AI-generated product placement. Subject: '{subject}'.\n\n"
        f"Score this inpainted image 0–10 based on:\n"
        f"1. Is the {subject} naturally integrated into the scene?\n"
        f"2. Is the lighting and shadow consistent with the environment?\n"
        f"3. Are there no visible seams, artifacts, or blending issues?\n\n"
        f"Reply ONLY with valid JSON: {{\"score\": <float>, \"reason\": \"<one sentence>\"}}"
    )
    response = _gemini.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            prompt,
        ],
    )
    raw = response.text.strip().strip("```json").strip("```").strip()
    data = json.loads(raw)
    score = float(data["score"])
    return {"score": score, "reason": data.get("reason", ""), "passed": score >= REVIEW_THRESHOLD}
