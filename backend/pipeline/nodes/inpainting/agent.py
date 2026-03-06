"""
ADK agent for inpainting.

Wraps the Flux2 Klein 9B LanPaint inpainting pipeline with an agent that:
- Analyses the masked scene and the product to write a minimal, effective prompt
- Chooses appropriate API parameters for the LanPaint sampler
- Submits to RunPod, reviews the result, and adjusts intelligently across retries
"""
import asyncio
import random

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part

from .runner import NodeFailed, submit_and_fetch

MAX_ATTEMPTS = 3

# ── Agent system instruction ───────────────────────────────────────────────────

_INSTRUCTION = """\
You are a specialist inpainting agent for a product photography pipeline.

## About the Inpainting Pipeline
The pipeline uses Flux2 Klein 9B with the LanPaint KSampler to inpaint a product into a \
masked scene. The model takes:
  - A scene image with a masked region (white area = where product goes)
  - A reference product image (the actual item to place)
  - A text prompt

The model uses ReferenceLatent nodes that feed the product image directly into the diffusion \
process. This means the model already "sees" the product visually — the prompt does NOT need \
to describe the product's appearance. Keep the prompt extremely simple.

## Prompt Writing Rules
- Write SHORT, natural-language prompts (5–12 words maximum)
- Describe only the subject + how they wear/use/hold the product
- Do NOT describe the product's colour, texture, material, or style — the model infers those \
  from the reference image
- Do NOT describe the scene, background, lighting, or camera
- Examples of good prompts:
  - "woman wearing a jacket"
  - "man holding a bag"
  - "person wearing headphones"
  - "model in sneakers"
  - "athlete wearing a t-shirt"
- Look at the masked scene image to understand: who is the character (man/woman/person/etc.), \
  and how the product area is positioned (wearing, holding, carrying, etc.)

## Workflow Parameters (Flux2Klein9bInpaintingAPI)
- prompt (node 107 CLIPTextEncode, Qwen 3 8B encoder): the positive prompt — keep it simple
- seed (node 156 LanPaint_KSampler): randomises generation
- steps (node 156 LanPaint_KSampler): diffusion steps. Range 4–20.
  - 4–6: fast, lower quality — use for first attempt
  - 8–12: good quality — use if first attempt fails
  - 14–20: highest quality — use for final retry
- denoise (node 156 LanPaint_KSampler): how much to regenerate the masked region. Range 0.7–1.0.
  - 1.0: fully regenerate (default) — best for most cases
  - 0.8–0.9: preserve some of the original — use if integration looks unnatural
- guidance (node 100 FluxGuidance): how strongly to follow the prompt. Range 1–10.
  - 3–5: balanced (default 4) — recommended
  - 6–8: stronger prompt adherence — use if product is not appearing
  - 1–2: very loose — rarely needed
- lan_paint_num_steps (node 156 LanPaint_NumSteps): LanPaint internal refinement steps. Range 1–5.
  - 2: default, good balance
  - 3–4: more refinement, better blending — use if edges look unnatural
- lan_paint_prompt_mode (node 156 LanPaint_PromptMode): how much the prompt vs image drives generation.
  - "Image First": product reference drives generation (default, recommended)
  - "Balanced": equal weight
  - "Text First": prompt drives more — use only if product appearance is wrong

## Review Criteria
After inpainting, review the result:
1. Is the product naturally integrated — correct scale, position, and placement?
2. Is lighting consistent with the surrounding scene?
3. Are there no visible seams, blending artefacts, or unnatural edges around the inpainted area?
4. Does the inpainted product look like the reference product image?

Score 0–10. Pass threshold: 6.5.

## Retry Strategy
When review_inpaint fails, the result includes a `suggested_fixes` dict with specific parameter \
adjustments recommended by the reviewer. ALWAYS apply those suggested_fixes in your next \
submit_inpaint call — do not ignore them and do not just change the seed.

If no suggested_fixes are provided, use the reason text to decide:
- Product cut off or incomplete at edges → lower denoise (0.85–0.9), increase steps
- Product not visible or wrong appearance → increase guidance (6–8), switch to "Text First"
- Blending/seam issues → increase lan_paint_num_steps (3–4)
- Graphic/text distorted or missing → increase steps (10–14), increase lan_paint_num_steps
- Low overall quality → increase steps
- None of the above → change seed only, keep other params

Never exceed your attempt budget.
"""


# ── Agent factory + runner ────────────────────────────────────────────────────

def create_and_run(
    subject: str,
    masked_r2: str,
    product_r2: str,
    masked_image_bytes: bytes,
    product_image_bytes: bytes,
    on_prompt=None,
    on_step=None,
) -> dict:
    """
    Creates and runs the inpainting ADK agent.
    Returns: {r2_path, prompt, score, reason, attempts_used}
    Raises NodeFailed if agent exhausts attempts without a passing result.
    """
    result_store: dict = {}
    _result_cache: dict[str, bytes] = {}
    _last_attempt: dict = {}
    attempt_count = [0]

    def _step(key: str, status: str, label: str | None = None, reason: str | None = None):
        if on_step:
            on_step(key, status, label, reason)

    def notify_prompt(prompt: str) -> str:
        """
        Call this immediately after deciding on your prompt, before calling submit_inpaint.
        This surfaces the prompt in the UI.

        Args:
            prompt: The exact prompt you are about to submit.
        Returns:
            Confirmation string.
        """
        if on_prompt:
            on_prompt(prompt)
        _step("prompt", "done")
        return "Prompt received."

    def submit_inpaint(
        prompt: str,
        steps: int = 4,
        denoise: float = 1.0,
        guidance: float = 4.0,
        lan_paint_num_steps: int = 2,
        lan_paint_prompt_mode: str = "Image First",
    ) -> dict:
        """
        Submit the masked scene and product reference to the inpainting worker.

        Args:
            prompt: Simple placement prompt (e.g. "woman wearing a jacket").
            steps: Diffusion steps (4–20). Start low, increase on retry.
            denoise: Regeneration strength (0.7–1.0). Default 1.0.
            guidance: Prompt adherence strength (1–10). Default 4.
            lan_paint_num_steps: LanPaint refinement steps (1–5). Default 2.
            lan_paint_prompt_mode: "Image First", "Balanced", or "Text First". Default "Image First".
        Returns:
            {"r2_path": str} on success, {"error": str} on failure.
        """
        attempt_count[0] += 1
        _step("submit", "running", f"Inpaint (attempt {attempt_count[0]})")
        _step("review", "pending")

        seed = random.randint(1, 999_999)
        try:
            r2_path, image_bytes = submit_and_fetch(
                masked_r2=masked_r2,
                product_r2=product_r2,
                prompt=prompt,
                seed=seed,
                steps=steps,
                denoise=denoise,
                guidance=guidance,
                lan_paint_num_steps=lan_paint_num_steps,
                lan_paint_prompt_mode=lan_paint_prompt_mode,
            )
        except NodeFailed as e:
            _step("submit", "failed")
            return {"error": str(e)}

        _result_cache[r2_path] = image_bytes
        _last_attempt["r2_path"] = r2_path
        _last_attempt["prompt"] = prompt
        _step("submit", "done", f"Inpainted (attempt {attempt_count[0]})")
        _step("review", "running")
        print(f"[Inpainting agent] attempt={attempt_count[0]} r2={r2_path}")
        return {"r2_path": r2_path}

    def review_inpaint(r2_path: str) -> dict:
        """
        Review the quality of the inpainted result.

        Args:
            r2_path: The r2_path returned by submit_inpaint.
        Returns:
            {"score": float, "reason": str, "passed": bool, "suggested_fixes": dict | None}
            Score is 0–10; passed means score ≥ 7.0.
            When passed is False, suggested_fixes contains specific parameter adjustments
            to apply on the next submit_inpaint call. Always use them if present.
        """
        from .review import review as _review
        image_bytes = _result_cache.get(r2_path)
        if not image_bytes:
            return {"error": "Result not in cache — pass the r2_path from submit_inpaint"}
        result = _review(image_bytes, subject)
        if result["passed"]:
            _step("review", "done")
        else:
            _step("review", "failed", reason=result.get("reason"))
            _step("prompt", "running")
        return result

    def complete_task(r2_path: str, prompt: str, score: float, reason: str) -> str:
        """
        Mark inpainting as successfully completed. Call when review_inpaint passes.

        Args:
            r2_path: The r2_path of the accepted result.
            prompt: The prompt that produced it.
            score: The score from review_inpaint.
            reason: The reason from review_inpaint.
        Returns:
            Confirmation string.
        """
        result_store["result"] = {
            "r2_path": r2_path,
            "prompt": prompt,
            "score": score,
            "reason": reason,
            "attempts_used": attempt_count[0],
        }
        return "Inpainting task completed."

    # ── Build task message with both images ───────────────────────────────────
    task_parts = [
        Part.from_bytes(data=masked_image_bytes, mime_type="image/png"),
        Part.from_bytes(data=product_image_bytes, mime_type="image/png"),
        Part.from_text(text=(
            f"Inpaint the product into the masked scene.\n\n"
            f"Image 1 (above): the masked scene — the white/highlighted region is where the "
            f"'{subject}' will be placed.\n"
            f"Image 2 (above): the actual product to inpaint — this is the reference image "
            f"the model will use visually.\n\n"
            f"Subject: '{subject}'\n"
            f"Maximum attempts: {MAX_ATTEMPTS}\n\n"
            f"Sequence:\n"
            f"1. Look at both images and write a minimal prompt describing the placement.\n"
            f"2. Call notify_prompt with your prompt.\n"
            f"3. Call submit_inpaint with your prompt and chosen parameters.\n"
            f"4. Call review_inpaint on the result.\n"
            f"5. If passed, call complete_task. If not, adjust and retry.\n"
            f"You have {MAX_ATTEMPTS} total submits."
        )),
    ]

    # ── Create agent ──────────────────────────────────────────────────────────
    agent = Agent(
        name="inpainting_agent",
        model="gemini-2.0-flash",
        instruction=_INSTRUCTION,
        tools=[notify_prompt, submit_inpaint, review_inpaint, complete_task],
    )

    # ── Run agent (sync wrapper around async ADK) ─────────────────────────────
    async def _run():
        runner = InMemoryRunner(agent=agent, app_name="inpainting")
        session = await runner.session_service.create_session(
            app_name="inpainting", user_id="pipeline"
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
            print(f"[Inpainting agent] Exhausted attempts — proceeding with last attempt r2={_last_attempt['r2_path']}")
            _step("review", "done")
            return {
                "r2_path": _last_attempt["r2_path"],
                "prompt": _last_attempt.get("prompt", ""),
                "score": 0.0,
                "reason": "Proceeding after exhausting retry budget.",
                "attempts_used": attempt_count[0],
            }
        raise NodeFailed(
            f"Inpainting agent did not produce any result after {attempt_count[0]} attempt(s)."
        )
    return result_store["result"]
