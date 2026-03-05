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
        f"You are a quality reviewer for AI-generated product photography. Subject: '{subject}'.\n\n"
        f"Score this image 0–10 based on:\n"
        f"1. Is the subject ({subject}) clearly visible and correctly worn/used?\n"
        f"2. Is the image photorealistic (no obvious AI artifacts)?\n"
        f"3. No body deformities (extra hands/legs, waxy skin, distorted face)?\n\n"
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
