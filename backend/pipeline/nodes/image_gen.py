"""
Node 1: Image Generation
Self-contained. No imports from other nodes.

Input:  subject, mode, lora_name, keyword, scenario, width, height
Output: {"r2_path", "prompt", "score", "reason", "attempts_used"}
Raises: NodeFailed after 3 attempts
"""

import json
import os
import random
import time

import boto3
import requests
from botocore.config import Config
from google import genai
from google.genai import types

# ── RunPod ────────────────────────────────────────────────────────────────────
RUNPOD_API_KEY        = os.environ.get("RUNPOD_API_KEY", "")
LORA_ENDPOINT_ID      = "4zt599q013q0cz"
Z_TURBO_ENDPOINT_ID   = "vycazppjzv96nv"
TERMINAL_FAILED       = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}
POLL_INTERVAL         = 5

# ── R2 ────────────────────────────────────────────────────────────────────────
R2_ENDPOINT_URL    = os.environ.get("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID   = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET          = os.environ.get("R2_OUTPUT_BUCKET", "")

# ── Gemini ─────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_gemini = genai.Client(api_key=GEMINI_API_KEY)

# ── Review config ──────────────────────────────────────────────────────────────
REVIEW_THRESHOLD = 7.0
MAX_ATTEMPTS     = 3

# Param escalation per attempt index
_LORA_PARAMS = [
    {"lora_strength": 1.0, "upscale_lora_strength": 0.6},
    {"lora_strength": 1.1, "upscale_lora_strength": 0.7},
    {"lora_strength": 1.2, "upscale_lora_strength": 0.8},
]


class NodeFailed(Exception):
    pass


# ── Helpers ────────────────────────────────────────────────────────────────────

def _rp_headers():
    return {"Authorization": f"Bearer {RUNPOD_API_KEY}", "Content-Type": "application/json"}


def _r2_client():
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def _download_r2(r2_path: str) -> bytes:
    parts = r2_path[5:].split("/", 1)   # strip "r2://"
    bucket, key = parts[0], parts[1]
    resp = _r2_client().get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()


def _poll_runpod(endpoint_id: str, job_id: str) -> dict:
    while True:
        r = requests.get(
            f"https://api.runpod.ai/v2/{endpoint_id}/status/{job_id}",
            headers=_rp_headers(),
        )
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if status == "COMPLETED":
            return data
        if status in TERMINAL_FAILED:
            raise NodeFailed(f"RunPod {status}: {data.get('error') or status}")
        time.sleep(POLL_INTERVAL)


def _generate_prompt(subject: str, keyword: str, scenario: str | None) -> str:
    import random as _r

    FORMAT_INSTRUCTIONS = {
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
    fmt = _r.choice(["A", "B", "C"])
    response = _gemini.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=(
                "You are a cinematic prompt writer. Produce one photorealistic image prompt matching "
                "the format rules exactly. Output ONLY the prompt, no labels, no quotes.\n\n"
                "CONTENT: Include subject, wardrobe showing the item, pose, environment, camera/shot "
                "language, lighting specifics, concrete textures. 120–220 words.\n\n"
                + FORMAT_INSTRUCTIONS[fmt]
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


def _review(image_bytes: bytes, subject: str) -> dict:
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


# ── Public entry point ─────────────────────────────────────────────────────────

def run(
    subject: str,
    mode: str,
    lora_name: str | None = None,
    keyword: str | None = None,
    scenario: str | None = None,
    width: int = 1024,
    height: int = 1024,
) -> dict:
    last_reason = ""
    for attempt in range(MAX_ATTEMPTS):
        seed = random.randint(1, 999999)
        prompt = _generate_prompt(subject, keyword or "", scenario)

        if mode == "template":
            params = _LORA_PARAMS[attempt]
            body = {
                "prompt": prompt, "lora_name": lora_name,
                "width": width, "height": height,
                "lora_strength": params["lora_strength"],
                "upscale_lora_strength": params["upscale_lora_strength"],
                "seed": seed,
            }
            endpoint = LORA_ENDPOINT_ID
        else:
            body = {"prompt": prompt, "width": width, "height": height, "seed": seed}
            endpoint = Z_TURBO_ENDPOINT_ID

        r = requests.post(
            f"https://api.runpod.ai/v2/{endpoint}/run",
            headers=_rp_headers(),
            json={"input": body},
        )
        r.raise_for_status()
        runpod_job_id = r.json()["id"]
        print(f"[ImageGen node] attempt={attempt+1} job={runpod_job_id}")

        data = _poll_runpod(endpoint, runpod_job_id)
        images = data.get("output", {}).get("images", [])
        if not images:
            raise NodeFailed("No images returned from RunPod")

        r2_path = images[0]["r2_path"]
        image_bytes = _download_r2(r2_path)
        review = _review(image_bytes, subject)
        print(f"[ImageGen node] attempt={attempt+1} score={review['score']} passed={review['passed']}")

        if review["passed"]:
            return {
                "r2_path": r2_path,
                "prompt": prompt,
                "score": review["score"],
                "reason": review["reason"],
                "attempts_used": attempt + 1,
            }
        last_reason = review["reason"]

    raise NodeFailed(f"Image gen failed after {MAX_ATTEMPTS} attempts. Last: {last_reason}")
