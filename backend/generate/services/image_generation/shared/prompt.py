import os
import random
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

FORMAT_A = "A"
FORMAT_B = "B"
FORMAT_C = "C"
FORMAT_CHOICES = [FORMAT_A, FORMAT_B, FORMAT_C]


def _format_instruction(fmt):
    if fmt == FORMAT_A:
        return (
            "FORMAT A:\n"
            "- Two sentences separated by a newline.\n"
            "- Sentence 1 must start with 'Cinematic' and be a single flowing line.\n"
            "- Sentence 2 must start with a lighting phrase like 'natural sunlight' or "
            "'soft diffused light' and end with a quality statement like "
            "'photorealistic quality, professional cinematography.'\n"
        )
    if fmt == FORMAT_B:
        return (
            "FORMAT B:\n"
            "- One long sentence only (no line breaks).\n"
            "- Must start with 'lunevacyber realistic photograph of'.\n"
            "- Include camera move or lens details early (e.g., low-angle dolly, 24mm lens).\n"
        )
    return (
        "FORMAT C:\n"
        "- Two lines.\n"
        "- Line 1 must start with 'lunevacyber realistic photograph of' and include 'Behind her:' or "
        "'Behind him:' once.\n"
        "- Line 2 must be exactly:\n"
        "  Steps: 9, CFG scale: 1, Sampler: res2s_FlowMatchEulerDiscreteScheduler, "
        "Seed: 0, Size: 0x0, Model: Z Image, Version: ComfyUI\n"
    )


def generate_prompt(subject: str, keyword: str, scenario: str | None = None) -> str:
    fmt = random.choice(FORMAT_CHOICES)

    system_instruction = (
        "You are a cinematic prompt writer with a lyrical, hyper-specific, editorial style. "
        "Produce one photorealistic image prompt that matches the format rules exactly. "
        "Output ONLY the prompt, no labels, no quotes.\n\n"
        "STYLE TARGET:\n"
        "- Dense, flowing clauses stitched by commas, with tactile micro-details and brand-level specificity.\n"
        "- Blend fashion editorial, street photography, and cinematic realism.\n"
        "- Describe skin, fabric, metal, glass, pavement, signage, and weather effects with concrete nouns.\n"
        "- Include scene geography and ambient context (neon signage, interior props, street furniture, decals).\n"
        "- Write like a high-end photo brief: precise, sensual, and physical.\n\n"
        "CONTENT REQUIREMENTS:\n"
        "- Include subject, wardrobe, pose, environment, and a clear physical interaction with the subject item.\n"
        "- Add camera/shot language (angle, lens, movement) and lighting specifics.\n"
        "- Use concrete textures and materials. Avoid vague adjectives.\n"
        "- Include at least one motion verb (gliding, leaning, twisting, flicking, etc.).\n"
        "- Keep the total length between 120 and 220 words.\n\n"
        f"{_format_instruction(fmt)}"
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        ),
        contents=(
            f"Subject: {subject}\n"
            f"Scenario: {scenario if scenario else 'None'}\n"
            f"Trigger word (character): {keyword if keyword else 'None'}\n"
            "Follow the scenario closely. Use it to build a detailed, physical pose and action.\n"
            "Use the trigger word as the character reference exactly as given.\n"
            "Invent a fitting wardrobe and environment around that character.\n"
            "Write the prompt now."
        ),
    )

    return response.text.strip()
