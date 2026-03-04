import os
import random

from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_gemini = genai.Client(api_key=GEMINI_API_KEY)

_FORMAT_INSTRUCTIONS = {
    "A": (
        "FORMAT A:\n"
        "- Two sentences separated by a newline.\n"
        "- Sentence 1 must start with 'Cinematic'.\n"
        "- Sentence 2 must start with a lighting phrase and end with 'photorealistic quality, professional cinematography.'\n"
    ),
    "B": (
        "FORMAT B:\n"
        "- One long sentence only (no line breaks).\n"
        "- Must start with 'lunevacyber realistic photograph of'.\n"
        "- Include camera move or lens details early.\n"
    ),
    "C": (
        "FORMAT C:\n"
        "- Two lines.\n"
        "- Line 1 must start with 'lunevacyber realistic photograph of' and include 'Behind her:' or 'Behind him:' once.\n"
        "- Line 2 must be exactly:\n"
        "  Steps: 9, CFG scale: 1, Sampler: res2s_FlowMatchEulerDiscreteScheduler, Seed: 0, Size: 0x0, Model: Z Image, Version: ComfyUI\n"
    ),
}


def generate(subject: str, keyword: str, scenario: str | None) -> str:
    fmt = random.choice(["A", "B", "C"])
    response = _gemini.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are a cinematic prompt writer. Produce one photorealistic image prompt matching "
                "the format rules exactly. Output ONLY the prompt, no labels, no quotes.\n\n"
                "CONTENT: Include subject, wardrobe showing the item, pose, environment, camera/shot "
                "language, lighting specifics, concrete textures. 120–220 words.\n\n"
                + _FORMAT_INSTRUCTIONS[fmt]
            ),
            temperature=0.7,
        ),
        contents=(
            f"Subject: {subject}\n"
            f"Scenario: {scenario or 'None'}\n"
            f"Trigger word: {keyword or 'None'}\n"
            "Write the prompt now."
        ),
    )
    return response.text.strip()
