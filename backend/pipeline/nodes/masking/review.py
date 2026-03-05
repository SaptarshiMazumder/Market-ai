import json
import os

from google import genai
from google.genai import types

GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
REVIEW_THRESHOLD = 5.0

_gemini = genai.Client(api_key=GEMINI_API_KEY)


def review(mask_bytes: bytes, subject: str, product_bytes: bytes | None = None) -> dict:
    """
    Review mask quality.
    Only fails on genuinely broken masks — wrong object masked, subject not covered,
    or mask completely fragmented into noise.
    """
    contents_parts = [types.Part.from_bytes(data=mask_bytes, mime_type="image/png")]
    if product_bytes:
        contents_parts.append(types.Part.from_bytes(data=product_bytes, mime_type="image/png"))

    prompt = (
        f"You are reviewing an AI-generated segmentation mask for product inpainting. Subject: '{subject}'.\n\n"
        f"The mask image shows white areas where the subject will be replaced. "
        f"{'Image 2 is the actual product for reference.' if product_bytes else ''}\n\n"
        f"Score 0–10. Be LENIENT — the inpainting model handles blending and edge quality. "
        f"Your job is only to catch genuinely broken masks. Use this strict rubric:\n\n"
        f"- 8–10: Mask covers the '{subject}' region, roughly the right shape, usable\n"
        f"- 5–7: Mask is imperfect (slightly loose edges, minor bleed) but the subject area is covered\n"
        f"- 2–4: Wrong object masked, OR major portions of the subject are uncovered\n"
        f"- 0–1: Mask is completely absent, inverted, or pure noise\n\n"
        f"Do NOT penalise for:\n"
        f"- Edge softness or blur (that is intentional)\n"
        f"- Slight over-dilation into background (better too big than too small)\n"
        f"- Minor imperfections in boundary tracing\n"
        f"- Edge sharpness mismatch with product type\n\n"
        f"Only give a score below 5 if the mask fundamentally fails to cover the '{subject}'.\n\n"
        f"Reply ONLY with valid JSON: {{\"score\": <float>, \"reason\": \"<one sentence>\"}}"
    )
    contents_parts.append(prompt)

    response = _gemini.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents_parts,
    )
    raw = response.text.strip().strip("```json").strip("```").strip()
    data = json.loads(raw)
    score = float(data["score"])
    return {"score": score, "reason": data.get("reason", ""), "passed": score >= REVIEW_THRESHOLD}
