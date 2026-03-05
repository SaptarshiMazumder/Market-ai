import os

from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_gemini = genai.Client(api_key=GEMINI_API_KEY)


def generate_scenario(subject: str, template_name: str) -> str:
    """
    Generate a short scenario sentence combining the product and template context.
    E.g. subject='cap', template_name='young boy' -> 'a young boy casually wearing a cap outdoors'
    Used to seed the ADK agent with concrete context before it writes the full prompt.
    """
    response = _gemini.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(temperature=0.8),
        contents=(
            f"You are a creative director for product photography.\n"
            f"Product: {subject}\n"
            f"Model/Context: {template_name}\n\n"
            f"Write ONE concise scenario sentence (10-20 words) describing a natural, believable moment "
            f"where the model/context is using or wearing the product. "
            f"Be specific about activity, setting, or mood. Output only the sentence, no quotes."
        ),
    )
    scenario = response.text.strip()
    print(f"[ImageGen prompt] scenario: {scenario}")
    return scenario
