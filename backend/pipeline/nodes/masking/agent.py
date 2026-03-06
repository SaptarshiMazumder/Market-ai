"""
ADK agent for masking.

Wraps the Florence2 + SAM2 masking pipeline with an agent that:
- Analyses the generated image AND the product to choose appropriate mask params
- Submits to RunPod masking worker
- Reviews the mask quality considering the product to be inpainted
"""
import asyncio
import random

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part

from .runner import NodeFailed, submit_and_fetch
from .review import review

MAX_ATTEMPTS = 3

# ── Agent system instruction ───────────────────────────────────────────────────

_INSTRUCTION = """\
You are a specialist masking agent for a product photography inpainting pipeline.

## About the Masking Pipeline
The pipeline uses Florence2 (object grounding) + SAM2 (segmentation) to create a mask \
around the subject in a generated scene. The mask defines the area that will be replaced \
with the actual product during inpainting.

## Workflow Parameters (FlorenceSegmentationMaskingAPI)
- object_name: text description of the subject — already set from pipeline context
- seed: randomises Florence2 grounding — use a different seed on retry if segmentation fails
- mask_blur (node 104 'MaskBlur+', param: amount):
  Controls softness of mask edges. Maximum value is 10 — do not exceed this.
  - 1–5: very sharp, crisp edges — good for hard-edged objects (bags, shoes, accessories)
  - 6–10: slightly softened — acceptable for clothing; this is the maximum allowed
- mask_dilation (node 110 'ImpactDilateMask', param: dilation):
  Expands the mask outward from the detected boundary. Use generous values to ensure
  the inpainting model has enough margin to blend the product naturally.
  - 20–35: standard — good for small accessories and precise objects
  - 35–55: recommended for most clothing and medium-sized items
  - 55–80: large — use for big items (coats, full-body garments, large bags)

## Parameter Selection Strategy
Before submitting, look at BOTH images provided:
1. The generated scene — understand the subject's size, shape, and position in the frame
2. The product image — understand the object type (soft clothing vs hard accessory vs structured item)

Choose blur and dilation to match:
- Soft/flowing clothing → blur (6–10), dilation (40–55)
- Structured garments (jackets, coats) → blur (5–8), dilation (35–50)
- Hard accessories (bags, shoes, bottles) → blur (2–6), dilation (25–40)
- Jewellery / small items → blur (1–5), dilation (20–30)

## Review Criteria
After generating the mask, review by looking at BOTH the mask image AND the product image:
1. Does the mask fully cover the subject region? (no gaps or holes)
2. Are the edges appropriate for the product type?
   - Hard products: edges should be fairly crisp
   - Soft clothing: moderate softness is fine
3. Is the mask contiguous — not fragmented into many disconnected pieces?
4. Is the dilation reasonable — enough inpainting margin without bleeding far into background?

Pass threshold: score ≥ 5.0 out of 10. Only retry if the mask fundamentally failed to cover the subject.

## Retry Strategy
- Fragmented or missed subject: change seed (Florence2 is non-deterministic)
- Edges too blurry: reduce mask_blur
- Edges too sharp for soft clothing: increase mask_blur slightly
- Mask too tight: increase mask_dilation
- Never exceed your attempt budget
"""


# ── Agent factory + runner ────────────────────────────────────────────────────

def create_and_run(
    subject: str,
    generated_r2: str,
    generated_image_bytes: bytes,
    product_image_bytes: bytes,
    on_step=None,
) -> dict:
    """
    Creates and runs the masking ADK agent.
    Returns: {r2_path, score, reason, attempts_used}
    Raises NodeFailed if agent exhausts attempts without a passing mask.
    """
    result_store: dict = {}
    _mask_cache: dict[str, bytes] = {}
    _last_attempt: dict = {}
    attempt_count = [0]

    def _step(key: str, status: str, label: str | None = None, reason: str | None = None):
        if on_step:
            on_step(key, status, label, reason)

    def submit_mask(mask_blur: int, mask_dilation: int) -> dict:
        """
        Submit the generated image to the masking worker with your chosen parameters.

        Args:
            mask_blur: Softness of mask edges (1–10 max). Lower = sharper. Values above 10 are capped to 10.
            mask_dilation: How far to expand the mask outward (20–80). Use generous values for good inpainting margin.
        Returns:
            {"r2_path": str} on success, {"error": str} on failure.
        """
        attempt_count[0] += 1
        _step("submit", "running", f"Generate mask (attempt {attempt_count[0]})")
        _step("review", "pending")

        seed = random.randint(1, 999_999)
        try:
            r2_path, mask_bytes = submit_and_fetch(
                generated_r2=generated_r2,
                subject=subject,
                mask_blur=mask_blur,
                mask_dilation=mask_dilation,
                seed=seed,
            )
        except NodeFailed as e:
            _step("submit", "failed")
            return {"error": str(e)}

        _mask_cache[r2_path] = mask_bytes
        _last_attempt["r2_path"] = r2_path
        _step("submit", "done", f"Masked (attempt {attempt_count[0]})")
        _step("review", "running")
        print(f"[Masking agent] attempt={attempt_count[0]} r2={r2_path}")
        return {"r2_path": r2_path}

    def review_mask(r2_path: str) -> dict:
        """
        Review the quality of the generated mask against the product to be inpainted.

        Args:
            r2_path: The r2_path returned by submit_mask.
        Returns:
            {"score": float, "reason": str, "passed": bool}
            Score is 0–10; passed means score ≥ 5.0.
        """
        mask_bytes = _mask_cache.get(r2_path)
        if not mask_bytes:
            return {"error": "Mask not in cache — pass the r2_path from submit_mask"}
        result = review(mask_bytes, subject, product_bytes=product_image_bytes)
        if result["passed"]:
            _step("review", "done")
        else:
            _step("review", "failed", reason=result.get("reason"))
            _step("submit", "running")
        return result

    def complete_task(r2_path: str, score: float, reason: str) -> str:
        """
        Mark masking as successfully completed. Call this when review_mask passes.

        Args:
            r2_path: The r2_path of the accepted mask.
            score: The score from review_mask.
            reason: The reason from review_mask.
        Returns:
            Confirmation string.
        """
        result_store["result"] = {
            "r2_path": r2_path,
            "score": score,
            "reason": reason,
            "attempts_used": attempt_count[0],
        }
        return "Masking task completed."

    # ── Build task message with both images ───────────────────────────────────
    task_parts = [
        Part.from_bytes(data=generated_image_bytes, mime_type="image/png"),
        Part.from_bytes(data=product_image_bytes, mime_type="image/png"),
        Part.from_text(text=(
            f"Create a mask for the subject in the generated scene above.\n\n"
            f"Image 1 (above): the generated scene — mask the '{subject}' in this image.\n"
            f"Image 2 (above): the actual product that will be inpainted — use this to "
            f"understand the object type and choose appropriate mask parameters.\n\n"
            f"Subject to mask: '{subject}'\n"
            f"Maximum attempts: {MAX_ATTEMPTS}\n\n"
            f"Sequence:\n"
            f"1. Analyse both images and choose mask_blur and mask_dilation.\n"
            f"2. Call submit_mask with your chosen parameters.\n"
            f"3. Call review_mask on the result.\n"
            f"4. If passed, call complete_task. If not, adjust params and retry.\n"
            f"You have {MAX_ATTEMPTS} total submits."
        )),
    ]

    # ── Create agent ──────────────────────────────────────────────────────────
    agent = Agent(
        name="masking_agent",
        model="gemini-2.0-flash",
        instruction=_INSTRUCTION,
        tools=[submit_mask, review_mask, complete_task],
    )

    # ── Run agent (sync wrapper around async ADK) ─────────────────────────────
    async def _run():
        runner = InMemoryRunner(agent=agent, app_name="masking")
        session = await runner.session_service.create_session(
            app_name="masking", user_id="pipeline"
        )
        events = runner.run_async(
            user_id="pipeline",
            session_id=session.id,
            new_message=Content(role="user", parts=task_parts),
        )
        async for _ in events:
            pass

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()
        asyncio.set_event_loop(None)

    if "result" not in result_store:
        if _last_attempt.get("r2_path"):
            print(f"[Masking agent] Exhausted attempts — proceeding with last attempt r2={_last_attempt['r2_path']}")
            _step("review", "done")
            return {
                "r2_path": _last_attempt["r2_path"],
                "score": 0.0,
                "reason": "Proceeding after exhausting retry budget.",
                "attempts_used": attempt_count[0],
            }
        raise NodeFailed(
            f"Masking agent did not produce any mask after {attempt_count[0]} attempt(s)."
        )
    return result_store["result"]
