import json
import os
import random
import requests
from google import genai
from google.genai import types


def load_env(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_env(os.path.join(os.path.dirname(__file__), ".env"))

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

RUNPOD_URL = "https://api.runpod.ai/v2/4zt599q013q0cz/run"
RUNPOD_TOKEN = os.environ.get("RUNPOD_TOKEN", "")

FORMAT_A = "A"
FORMAT_B = "B"
FORMAT_C = "C"
FORMAT_CHOICES = [FORMAT_A, FORMAT_B, FORMAT_C]


def _format_instruction(format_choice):
    if format_choice == FORMAT_A:
        return (
            "FORMAT A:\n"
            "- Two sentences separated by a newline.\n"
            "- Sentence 1 must start with 'Cinematic' and be a single flowing line.\n"
            "- Sentence 2 must start with a lighting phrase like 'natural sunlight' or "
            "'soft diffused light' and end with a quality statement like "
            "'photorealistic quality, professional cinematography.'\n"
        )
    if format_choice == FORMAT_B:
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


def generate_prompt_v2(subject_item, scenario_hint=None, trigger_word=None, format_choice=None):
    if format_choice not in FORMAT_CHOICES:
        format_choice = random.choice(FORMAT_CHOICES)

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
        f"{_format_instruction(format_choice)}"
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        ),
        contents=(
            f"Subject: {subject_item}\n"
            f"Scenario: {scenario_hint if scenario_hint else 'None'}\n"
            f"Trigger word (character): {trigger_word if trigger_word else 'None'}\n"
            "Follow the scenario closely. Use it to build a detailed, physical pose and action.\n"
            "Use the trigger word as the character reference exactly as given.\n"
            "Invent a fitting wardrobe and environment around that character.\n"
            "Write the prompt now."
        ),
    )

    return response.text.strip()


def submit_to_runpod(prompt_text):
    response = requests.post(
        RUNPOD_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RUNPOD_TOKEN}",
        },
        json={"input": {"prompt": prompt_text,  "lora_name": "trainedLoraMidjourney.safetensors",
            "width": 1024,
            "height": 1024,
            "lora_strength": 0.8,
            "seed": 42}},
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--submit", action="store_true", help="Submit the prompt to RunPod")
    parser.add_argument("--format", choices=FORMAT_CHOICES, help="Prompt format: A, B, or C")
    args = parser.parse_args()

    subject = input("Enter the subject item: ")
    scenario_hint = input("Enter a scenario (optional): ").strip()
    trigger_word = input("Enter a trigger word (optional): ").strip()
    prompt = generate_prompt_v2(
        subject,
        scenario_hint if scenario_hint else None,
        trigger_word if trigger_word else None,
        args.format,
    )

    print("\n--- GENERATED PROMPT ---")
    print(prompt)

    if args.submit:
        print("\n--- SUBMITTING TO RUNPOD ---")
        result = submit_to_runpod(prompt)
        print(json.dumps(result, indent=2))
    else:
        print("\n(RunPod submission skipped - pass --submit to send)")
