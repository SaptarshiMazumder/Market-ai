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

RUNPOD_URL = "https://api.runpod.ai/v2/1dv4vwaqf3quge/run"
RUNPOD_TOKEN = os.environ.get("RUNPOD_TOKEN", "")
ENVIRONMENTS_PATH = "environments.json"

OUTDOOR_OPEN_KEYWORDS = [
    "field", "wheat", "barley", "crop", "farmland",
    "coastal", "cliff", "ocean", "sea", "beach", "shore", "spindrift",
    "mountain", "valley", "alpine", "highland", "scree", "glacial",
    "desert", "scrubland", "arid", "mesa", "savanna", "plain",
    "meadow", "countryside", "panorama", "horizon", "open",
]

def is_outdoor_open(environment_name):
    name_lower = environment_name.lower()
    return any(kw in name_lower for kw in OUTDOOR_OPEN_KEYWORDS)

OUTDOOR_PHOTOGRAPHY_INSTRUCTIONS = (
    "\n\n6. OUTDOOR PHOTOGRAPHY TECHNICAL REQUIREMENTS (MANDATORY): "
    "The background must be rendered with maximum draw distance — every element from foreground to the "
    "horizon must be rendered with full sharpness and fine detail. There is ZERO depth-of-field blur, "
    "ZERO bokeh, ZERO lens blur anywhere in the background. The background is as sharp and resolved as "
    "the subject. Do NOT add atmospheric haze or softening to imply distance — render the far field with "
    "the same crispness as the near field. To make the image feel authentic and photographic rather than "
    "synthetic, add fine uniform film grain across the entire frame equivalent to ISO 400-800 on a full-frame "
    "sensor — fine-grained, not chunky. Natural photographic imperfections are encouraged: slight edge "
    "vignette, minor chromatic aberration at extreme corners, natural lighting falloff across the scene. "
    "The result must read as a genuine photograph taken on location, not a studio composite or AI render."
)

POSES_PATH = "poses.json"
CHARACTERS_PATH = "characters.json"

def choose_environment(subject_item, environment_names):
    system_instruction = (
        "Select the single best environment name from the provided list for the given subject. "
        "Return exactly one environment name from the list, with no extra words or punctuation."
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        ),
        contents=(
            f"Subject: {subject_item}\n"
            "Environment list:\n"
            + "\n".join(f"- {name}" for name in environment_names)
        ),
    )

    picked = response.text.strip()
    if picked in environment_names:
        return picked
    return random.choice(environment_names)


def choose_pose(subject_item, pose_names):
    system_instruction = (
        "Select the single best pose name from the provided list for the given subject. "
        "Return exactly one pose name from the list, with no extra words or punctuation."
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        ),
        contents=(
            f"Subject: {subject_item}\n"
            "Pose list:\n"
            + "\n".join(f"- {name}" for name in pose_names)
        ),
    )

    picked = response.text.strip()
    if picked in pose_names:
        return picked
    return random.choice(pose_names)


def choose_character(subject_item, character_names):
    system_instruction = (
        "Select the single best character description from the provided list for the given subject. "
        "Return exactly one character description from the list, with no extra words or punctuation."
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,
        ),
        contents=(
            f"Subject: {subject_item}\n"
            "Character list:\n"
            + "\n".join(f"- {name}" for name in character_names)
        ),
    )

    picked = response.text.strip()
    if picked in character_names:
        return picked
    return random.choice(character_names)


def generate_hyper_detailed_prompt(subject_item, environment_name, pose_name, character_name):
    outdoor_extra = OUTDOOR_PHOTOGRAPHY_INSTRUCTIONS if is_outdoor_open(environment_name) else ""

    system_instruction = (
        "You are an Elite Creative Director and Cinematographer. Your task is to write a "
        "250-300 word hyper-vivid, ultra-detailed prompt for the Soul2 image model.\n\n"
        "STRICT PROMPT ARCHITECTURE:\n"
        "1. BIOLOGICAL DETAIL: Describe the model listed below with extreme focus on 'skin micro-texture.' "
        "Mention sub-surface scattering, visible pores, natural freckles, fine peach fuzz under hard light, "
        "and the specific sheen of sweat or oils. Detail the fingernails (shape, gloss, cuticles) and "
        "hairstyle (individual flyaway strands, scalp visibility, hair texture). Choose an appropriate "
        "ethnicity, age range, and physical build that fits the subject and scene you invent.\n"
        "2. WARDROBE ANATOMY: Invent a complete outfit that fits the subject and scene. Describe each "
        "garment not just by name but by material science — weave density, thread count, surface finish, "
        "elasticity, seam construction, hardware details (zipper gauge, button material, stitching pattern), "
        "and exactly how light interacts with each texture and accessory.\n"
        "3. ENVIRONMENTAL DEPTH: Invent a scene that fits the subject and describe it to the most minute "
        "detail. Name every surface material, its age and wear state, micro-imperfections, and how ambient "
        "light falls across it. Specify the time of day through the angle and color temperature of "
        "incidental light, shadows, and any atmospheric particles (dust, humidity, haze) visible in the air.\n"
        "4. SUBJECT INTERACTION: How the model interacts with the subject item must be tactile and physical. "
        "Describe the contact points — grip pressure, deformation of materials, weight transfer, reflections "
        "of skin tone in glossy surfaces, or the way the item displaces fabric.\n"
        "5. LIGHTING: Specify the light source type, direction, quality (hard/soft), color temperature, and "
        "any supplemental fill or practical lights. Define the color grade and overall mood.\n\n"
        "NO VAGUE ADJECTIVES. Use technical, physical, and architectural nouns. "
        "Do NOT default to the same environment or outfit style — vary them freely based on what best "
        "serves the subject."
        + outdoor_extra
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.6,
        ),
        contents=(
            f"Subject: {subject_item}\n"
            f"Model: {character_name}\n"
            f"Environment: {environment_name}\n"
            f"Pose: {pose_name}\n"
            "Generate the ultimate editorial using the model, environment, and pose above."
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
        json={"input": {"prompt": prompt_text, "width": 2048,
      "height": 2048}},
    )
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--submit", action="store_true", help="Submit the prompt to RunPod")
    args = parser.parse_args()

    subject = input("Enter the subject item: ")
    with open(ENVIRONMENTS_PATH, "r", encoding="utf-8") as f:
        environment_names = json.load(f)

    with open(POSES_PATH, "r", encoding="utf-8") as f:
        pose_names = json.load(f)
    with open(CHARACTERS_PATH, "r", encoding="utf-8") as f:
        character_names = json.load(f)

    environment_name = choose_environment(subject, environment_names)
    pose_name = choose_pose(subject, pose_names)
    character_name = choose_character(subject, character_names)
    prompt = generate_hyper_detailed_prompt(subject, environment_name, pose_name, character_name)

    print("\n--- GENERATED PROMPT ---")
    print(f"Model: {character_name}")
    print(f"Environment: {environment_name}")
    print(f"Pose: {pose_name}")
    print(prompt)

    if args.submit:
        print("\n--- SUBMITTING TO RUNPOD ---")
        result = submit_to_runpod(prompt)
        print(json.dumps(result, indent=2))
    else:
        print("\n(RunPod submission skipped — pass --submit to send)")
