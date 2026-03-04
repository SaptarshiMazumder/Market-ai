"""
Node 3: Inpainting
Self-contained. No imports from other nodes.

Input:  masked_r2, product_r2, subject, (optional inpaint params)
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
RUNPOD_API_KEY      = os.environ.get("RUNPOD_API_KEY", "")
INPAINT_ENDPOINT    = "e70xck7rf5xnq4"
TERMINAL_FAILED     = {"FAILED", "CANCELLED", "TIMED_OUT", "CANCELLED_BY_SYSTEM"}
POLL_INTERVAL       = 5

# ── R2 ────────────────────────────────────────────────────────────────────────
R2_ENDPOINT_URL      = os.environ.get("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID     = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET            = os.environ.get("R2_OUTPUT_BUCKET", "")

# ── Gemini ─────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_gemini = genai.Client(api_key=GEMINI_API_KEY)

# ── Review config ──────────────────────────────────────────────────────────────
REVIEW_THRESHOLD = 6.5
MAX_ATTEMPTS     = 3
BASE_STEPS       = 4


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
    parts = r2_path[5:].split("/", 1)
    bucket, key = parts[0], parts[1]
    resp = _r2_client().get_object(Bucket=bucket, Key=key)
    return resp["Body"].read()


def _poll_runpod(job_id: str) -> dict:
    while True:
        r = requests.get(
            f"https://api.runpod.ai/v2/{INPAINT_ENDPOINT}/status/{job_id}",
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


def _generate_prompt(subject: str) -> str:
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


def _review(image_bytes: bytes, subject: str) -> dict:
    prompt = (
        f"You are a quality reviewer for AI-generated product placement. Subject: '{subject}'.\n\n"
        f"Score this inpainted image 0–10 based on:\n"
        f"1. Is the {subject} naturally integrated into the scene?\n"
        f"2. Is the lighting and shadow consistent with the environment?\n"
        f"3. Are there no visible seams, artifacts, or blending issues?\n\n"
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

def run(masked_r2: str, product_r2: str, subject: str) -> dict:
    last_reason = ""
    for attempt in range(MAX_ATTEMPTS):
        seed = random.randint(1, 999999)
        steps = BASE_STEPS + attempt * 2   # 4 → 6 → 8

        prompt = _generate_prompt(subject)

        job_input = {
            "scene_url": masked_r2,
            "reference_url": product_r2,
            "prompt": prompt,
            "seed": seed,
            "steps": steps,
            "denoise": 1.0,
            "guidance": 4.0,
        }
        r = requests.post(
            f"https://api.runpod.ai/v2/{INPAINT_ENDPOINT}/run",
            headers=_rp_headers(),
            json={"input": job_input},
        )
        r.raise_for_status()
        runpod_job_id = r.json()["id"]
        print(f"[Inpainting node] attempt={attempt+1} job={runpod_job_id} steps={steps}")

        data = _poll_runpod(runpod_job_id)
        images = data.get("output", {}).get("images", [])
        if not images:
            raise NodeFailed("No images returned from RunPod inpainting")

        r2_path = images[0]["r2_path"]
        image_bytes = _download_r2(r2_path)
        review = _review(image_bytes, subject)
        print(f"[Inpainting node] attempt={attempt+1} score={review['score']} passed={review['passed']}")

        if review["passed"]:
            return {
                "r2_path": r2_path,
                "prompt": prompt,
                "score": review["score"],
                "reason": review["reason"],
                "attempts_used": attempt + 1,
            }
        last_reason = review["reason"]

    raise NodeFailed(f"Inpainting failed after {MAX_ATTEMPTS} attempts. Last: {last_reason}")
