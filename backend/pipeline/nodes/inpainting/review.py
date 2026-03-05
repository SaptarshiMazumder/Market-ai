import json
import os

from google import genai
from google.genai import types

GEMINI_API_KEY   = os.environ.get("GEMINI_API_KEY", "")
REVIEW_THRESHOLD = 7.0

_gemini = genai.Client(api_key=GEMINI_API_KEY)


def review(image_bytes: bytes, subject: str) -> dict:
    prompt = (
        f"You are a strict, detail-oriented quality reviewer for AI-generated product inpainting. "
        f"The product that was inpainted is: '{subject}'.\n\n"
        f"Examine the image carefully and score it 0–10. Be critical — do NOT give high scores "
        f"unless the result is genuinely clean and complete. A score of 7+ means it is ready for "
        f"commercial use. Most results will have flaws; find them.\n\n"
        f"Check ALL of the following, one by one:\n\n"
        f"1. COMPLETENESS — Is the entire '{subject}' visible and fully rendered? "
        f"Look for cut-off edges, missing portions, or regions where the product appears "
        f"cropped, truncated, or fades out unnaturally at the frame boundary or mask edge.\n\n"
        f"2. GRAPHIC / TEXT INTEGRITY — If the product has any text, logos, graphics, or prints, "
        f"are they fully intact and legible? Text that is partially cut off, distorted, smeared, "
        f"or missing letters is a serious defect.\n\n"
        f"3. STRUCTURAL COHERENCE — Does the product look physically correct? "
        f"Check for warping, stretching, unnatural folds, impossible geometry, or parts that "
        f"look melted or deformed.\n\n"
        f"4. BLENDING & SEAMS — Are there visible seam lines, halos, or hard edges where the "
        f"inpainted region meets the original image? Does the product look pasted-on rather than "
        f"naturally present in the scene?\n\n"
        f"5. LIGHTING CONSISTENCY — Does the lighting and shadow on the '{subject}' match the "
        f"environment? Mismatched light direction or colour temperature is a defect.\n\n"
        f"6. OVERALL REALISM — Does the result look like a real photograph, or does it look "
        f"AI-generated / fake? Judge as if this were a product advertisement.\n\n"
        f"Score strictly:\n"
        f"- 9–10: Flawless, commercial-ready\n"
        f"- 7–8: Minor issues that don't significantly affect the result\n"
        f"- 5–6: Noticeable issues (cut-off, distortion, blending) that are acceptable for "
        f"internal review but not publication\n"
        f"- 3–4: Clear defects — cut-off graphics, wrong geometry, obvious seams\n"
        f"- 0–2: Fundamentally broken\n\n"
        f"If the score is below 7.0, also return a `suggested_fixes` object with specific "
        f"parameter adjustments that would address the identified issues. Choose from:\n"
        f"- steps: int (4–20) — increase if quality is low or result is incomplete\n"
        f"- denoise: float (0.7–1.0) — lower slightly if product is cut off at mask edges\n"
        f"- guidance: float (1–10) — increase if product is not appearing correctly\n"
        f"- lan_paint_num_steps: int (1–5) — increase if blending or seams are poor\n"
        f"- lan_paint_prompt_mode: str ('Image First'|'Balanced'|'Text First') — "
        f"switch to 'Text First' if product appearance is wrong\n"
        f"- prompt_hint: str — a short note on how to adjust the prompt if relevant\n\n"
        f"Reply ONLY with valid JSON:\n"
        f"{{\"score\": <float>, \"reason\": \"<one specific sentence>\", "
        f"\"suggested_fixes\": {{...}}}}  — omit suggested_fixes if score >= 7.0"
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
    passed = score >= REVIEW_THRESHOLD
    result = {"score": score, "reason": data.get("reason", ""), "passed": passed}
    if not passed and data.get("suggested_fixes"):
        result["suggested_fixes"] = data["suggested_fixes"]
    return result
