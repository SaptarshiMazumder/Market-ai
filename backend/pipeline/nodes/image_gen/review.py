import json
import os

import requests as http_requests
from google import genai
from google.genai import types

GEMINI_API_KEY      = os.environ.get("GEMINI_API_KEY", "")
REVIEW_THRESHOLD    = 7.0
TEMPLATES_BASE_URL  = os.environ.get("TEMPLATES_SERVICE_URL", "http://localhost:5003")

_gemini = genai.Client(api_key=GEMINI_API_KEY)

# Human-readable description of exposed workflow params (derived from lora_z_turbo_upscale_api.json)
_WORKFLOW_PARAM_GUIDE = (
    "Workflow parameter reference (ComfyUI lora-z-turbo-upscale):\n"
    "- lora_strength: strength_model in node 30 'Load LoRA (Generate)' — controls how strongly the "
    "LoRA character is baked into the initial generation. Typical range 0.8–1.4. "
    "Higher = stronger character features.\n"
    "- upscale_lora_strength: strength_model in node 33 'Load LoRA (Upscale Refine)' — controls "
    "how strongly the LoRA character is reinforced during the latent upscale refinement pass. "
    "Typical range 0.4–0.9. Higher = more character detail preserved after upscaling.\n"
    "Both params are independent. You can raise one without the other."
)


def review(image_bytes: bytes, subject: str) -> dict:
    prompt = (
        f"You are a strict quality reviewer for AI-generated product photography. "
        f"The subject that must appear in the image is: '{subject}'.\n\n"
        f"Score 0–10. Be critical — do NOT give high scores unless the subject is prominently "
        f"and clearly featured. Most AI images have flaws; find them.\n\n"
        f"Check ALL of the following:\n\n"
        f"1. SUBJECT VISIBILITY (most important) — Is '{subject}' clearly visible, "
        f"unambiguously identifiable, and the clear focal point of the image? "
        f"If the subject is obscured, too small, blends into the background, is partially "
        f"cut off, or could be mistaken for something else — that is a major defect. "
        f"A viewer should immediately recognise the '{subject}' without searching for it.\n\n"
        f"2. CORRECT USAGE — Is the '{subject}' being worn, held, or used in a natural and "
        f"correct way? Wrong orientation, impossible usage, or the subject floating detached "
        f"from the character are defects.\n\n"
        f"3. PHOTOREALISM — Does this look like a real photograph? "
        f"Check for AI artefacts: over-smoothed skin, floating objects, unnatural bokeh, "
        f"impossible lighting, flat textures, or watercolour-like areas.\n\n"
        f"4. BODY INTEGRITY — Are there body deformities? "
        f"Extra/missing limbs, fused fingers, distorted face, waxy or plastic-looking skin, "
        f"mismatched proportions — all are defects.\n\n"
        f"5. COMPOSITION — Is the framing appropriate for product photography? "
        f"The subject should be the hero of the shot, not buried in a busy scene.\n\n"
        f"Score strictly:\n"
        f"- 9–10: Subject is unmistakably prominent, image is photorealistic, ready for publication\n"
        f"- 7–8: Subject clearly visible, minor photorealism or composition issues\n"
        f"- 5–6: Subject present but not prominent, OR noticeable AI artefacts\n"
        f"- 3–4: Subject hard to find, wrong usage, or clear body deformities\n"
        f"- 0–2: Subject missing or image fundamentally broken\n\n"
        f"If the score is below 7.0, return `suggested_prompt_adjustments` — specific, concrete "
        f"changes the prompt writer should make to fix the issues found. Examples:\n"
        f"- If subject is too small: suggest closer framing, tighter shot, subject filling the frame\n"
        f"- If subject is obscured: suggest the character actively displaying/wearing it prominently\n"
        f"- If wrong usage: describe the correct natural usage\n"
        f"- If AI artefacts: suggest simpler scene, fewer elements, cleaner background\n"
        f"- If body deformity: suggest avoiding certain poses or actions that caused it\n\n"
        f"Reply ONLY with valid JSON:\n"
        f"{{\"score\": <float>, \"reason\": \"<one specific sentence>\", "
        f"\"suggested_prompt_adjustments\": \"<concrete prompt guidance>\"}}  "
        f"— omit suggested_prompt_adjustments if score >= 7.0"
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
    if not passed and data.get("suggested_prompt_adjustments"):
        result["suggested_prompt_adjustments"] = data["suggested_prompt_adjustments"]
    return result


def review_character(image_bytes: bytes, preview_url: str, current_params: dict) -> dict:
    """
    Compare the generated image against the template preview character.
    Returns: {passed, reason, suggested_params (only if not passed)}
    """
    # Support three formats: filesystem path, relative URL, or absolute URL
    import mimetypes
    if os.path.exists(preview_url):
        # Absolute filesystem path (local dev)
        with open(preview_url, "rb") as f:
            preview_bytes = f.read()
        content_type = mimetypes.guess_type(preview_url)[0] or "image/jpeg"
    else:
        # Relative URLs (e.g. /api/template-images/...) need the templates service base
        full_url = (TEMPLATES_BASE_URL + preview_url) if preview_url.startswith("/") else preview_url
        resp = http_requests.get(full_url, timeout=15)
        resp.raise_for_status()
        preview_bytes = resp.content
        content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
    if content_type not in ("image/jpeg", "image/png", "image/webp"):
        content_type = "image/jpeg"

    lora_s = current_params.get("lora_strength", 1.0)
    upscale_s = current_params.get("upscale_lora_strength", 0.6)

    prompt = (
        "You are reviewing AI-generated product photography for character consistency.\n\n"
        "Image 1 (reference): the template character — this is who should appear in the generated image.\n"
        "Image 2 (generated): the newly generated image to evaluate.\n\n"
        "Does the character in Image 2 look at least ~70% like the person/character in Image 1? "
        "You are checking overall identity resemblance — face shape, look, general style. "
        "Minor differences in lighting, pose, expression, or styling are acceptable. "
        "Do NOT require a strict pixel-perfect match; if the character is recognisably the same person, that is sufficient.\n\n"
        f"Params used for generation: lora_strength={lora_s}, upscale_lora_strength={upscale_s}\n\n"
        f"{_WORKFLOW_PARAM_GUIDE}\n\n"
        "If the character does NOT match, suggest adjusted param values that would improve resemblance.\n\n"
        "Reply ONLY with valid JSON:\n"
        "{\"passed\": <bool>, \"reason\": \"<one sentence>\", "
        "\"suggested_params\": {\"lora_strength\": <float>, \"upscale_lora_strength\": <float>}}\n"
        "Include suggested_params only when passed is false."
    )

    response = _gemini.models.generate_content(
        model="gemini-2.0-flash",
        contents=[
            types.Part.from_bytes(data=preview_bytes, mime_type=content_type),
            types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            prompt,
        ],
    )
    raw = response.text.strip().strip("```json").strip("```").strip()
    data = json.loads(raw)
    return {
        "passed": bool(data["passed"]),
        "reason": data.get("reason", ""),
        "suggested_params": data.get("suggested_params"),
    }
