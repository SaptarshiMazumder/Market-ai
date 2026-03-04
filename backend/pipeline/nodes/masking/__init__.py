import random

from .runner import NodeFailed, submit_and_fetch
from .review import review

MAX_ATTEMPTS = 3

_MASK_PARAMS = [
    {"mask_blur": 30, "mask_dilation": 10},
    {"mask_blur": 20, "mask_dilation": 15},
    {"mask_blur": 15, "mask_dilation": 20},
]


def run(generated_r2: str, subject: str) -> dict:
    last_reason = ""
    for attempt in range(MAX_ATTEMPTS):
        params = _MASK_PARAMS[attempt]
        seed = random.randint(1, 999999)

        r2_path, image_bytes = submit_and_fetch(
            generated_r2=generated_r2,
            subject=subject,
            mask_blur=params["mask_blur"],
            mask_dilation=params["mask_dilation"],
            seed=seed,
        )

        result = review(image_bytes, subject)
        print(f"[Masking] attempt={attempt+1} score={result['score']} passed={result['passed']}")

        if result["passed"]:
            return {
                "r2_path": r2_path,
                "score": result["score"],
                "reason": result["reason"],
                "attempts_used": attempt + 1,
            }
        last_reason = result["reason"]

    raise NodeFailed(f"Masking failed after {MAX_ATTEMPTS} attempts. Last: {last_reason}")
