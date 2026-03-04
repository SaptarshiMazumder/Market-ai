import random

from .prompt import generate as generate_prompt
from .runner import NodeFailed, submit_and_fetch
from .review import review

MAX_ATTEMPTS = 3

_LORA_PARAMS = [
    {"lora_strength": 1.0, "upscale_lora_strength": 0.6},
    {"lora_strength": 1.1, "upscale_lora_strength": 0.7},
    {"lora_strength": 1.2, "upscale_lora_strength": 0.8},
]


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
        prompt = generate_prompt(subject, keyword or "", scenario)
        lora_params = _LORA_PARAMS[attempt] if mode == "template" else {}

        r2_path, image_bytes = submit_and_fetch(
            mode=mode,
            prompt=prompt,
            width=width,
            height=height,
            lora_name=lora_name,
            seed=seed,
            **lora_params,
        )

        result = review(image_bytes, subject)
        print(f"[ImageGen] attempt={attempt+1} score={result['score']} passed={result['passed']}")

        if result["passed"]:
            return {
                "r2_path": r2_path,
                "prompt": prompt,
                "score": result["score"],
                "reason": result["reason"],
                "attempts_used": attempt + 1,
            }
        last_reason = result["reason"]

    raise NodeFailed(f"Image gen failed after {MAX_ATTEMPTS} attempts. Last: {last_reason}")
