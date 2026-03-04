import random

from .prompt import generate as generate_prompt
from .runner import NodeFailed, submit_and_fetch
from .review import review

MAX_ATTEMPTS = 3
BASE_STEPS   = 4


def run(masked_r2: str, product_r2: str, subject: str) -> dict:
    last_reason = ""
    for attempt in range(MAX_ATTEMPTS):
        seed  = random.randint(1, 999999)
        steps = BASE_STEPS + attempt * 2   # 4 → 6 → 8
        prompt = generate_prompt(subject)

        r2_path, image_bytes = submit_and_fetch(
            masked_r2=masked_r2,
            product_r2=product_r2,
            prompt=prompt,
            seed=seed,
            steps=steps,
        )

        result = review(image_bytes, subject)
        print(f"[Inpainting] attempt={attempt+1} score={result['score']} passed={result['passed']}")

        if result["passed"]:
            return {
                "r2_path": r2_path,
                "prompt": prompt,
                "score": result["score"],
                "reason": result["reason"],
                "attempts_used": attempt + 1,
            }
        last_reason = result["reason"]

    raise NodeFailed(f"Inpainting failed after {MAX_ATTEMPTS} attempts. Last: {last_reason}")
