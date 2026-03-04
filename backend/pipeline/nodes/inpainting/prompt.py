import os

from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_gemini = genai.Client(api_key=GEMINI_API_KEY)


def generate(subject: str) -> str:
    response = _gemini.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(temperature=0.7),
        contents=(
            f"Write a short, specific inpainting prompt for placing a '{subject}' into a scene. "
            f"One sentence, describe how the item sits in the environment naturally. "
            f"No introductions, output only the prompt."
        ),
    )
    return response.text.strip()
