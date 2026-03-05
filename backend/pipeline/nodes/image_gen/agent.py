"""
ADK agent for image generation.

Replaces the manual prompt-generate-review loop with a Gemini agent that:
- Writes prompts optimised for Z-Image Turbo
- Submits to RunPod, reviews quality and (template mode) character resemblance
- Adjusts prompt style and LoRA params intelligently across retries
"""
import asyncio
import random

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part

from .runner import NodeFailed, submit_and_fetch
from .review import review, review_character

MAX_ATTEMPTS = 3

# ── Agent system instruction ───────────────────────────────────────────────────

_INSTRUCTION = """\
You are a specialist product photography AI agent. Your job is to generate \
photorealistic, editorial-quality product images using the Z-Image Turbo pipeline.

## About Z-Image Turbo
- DiT-based model with a Qwen 3 4B text encoder (excellent at long, detailed prompts)
- Pipeline: main generation (15 steps, res_multistep sampler) → latent upscale → \
refinement pass (8 steps, dpmpp_sde sampler)
- LoRA injection at two stages:
  - lora_strength (0.8–1.4): how strongly the LoRA character is expressed in the initial generation
  - upscale_lora_strength (0.4–0.9): how strongly character detail is preserved during upscale refinement
- The model follows rich, editorial-style prose very well. Sparse or keyword-style prompts \
produce mediocre results. Prefer dense, flowing descriptions with concrete textures and specifics.

## Prompt Writing Rules
Write prompts in editorial photography style, 120–220 words. Choose one of three formats:

**Format A — Cinematic Hero Shot**
- Wide or medium framing, full subject in shot, strong sense of place and atmosphere
- Start with a shot type and camera description, then describe action, then environment

**Format B — Beauty/Lifestyle Editorial**
- Tighter framing, intimate, focus on emotion, texture and interaction with product
- Include camera movement or lens focal length early

**Format C — Action/Motion**
- Dynamic, energetic framing with motion verbs; two-part structure describing action then environment

Every prompt must include ALL of:
- The subject item clearly worn, held, or used by the character
- Specific camera/lens language (angle, focal length, depth of field)
- Lighting specifics (type, direction, quality, colour temperature)
- At least one strong motion/action verb
- Concrete textures and materials (no vague adjectives like "nice" or "beautiful")
- Environment details that contextualise the scene

**Character description — depends on mode (see task message):**
- **Template mode**: use the keyword as the ONLY character identifier. Never describe age, face, \
  hair, height, weight, skin tone, or any physical features — the LoRA encodes all of that.
- **No-template mode**: there is no LoRA and no keyword. Describe a complete, specific character — \
  gender, approximate age, ethnicity, hair, face, build, style — so the model can render a convincing \
  real person. Be specific and concrete; vague descriptors produce generic-looking results.

**Never include food or edible props in the scene unless the subject itself is a food product. Beverages are allowed.**

## Accessory-Specific Framing Rules
For accessories (watches, bracelets, rings, necklaces, lockets, earrings, ties, belts, caps, hats, \
sunglasses, bags, backpacks, wallets, scarves, gloves, socks, etc.), the shot framing is critical — \
a wide environmental shot will bury the accessory and make it invisible. Follow these rules:

- **Wrist accessories** (watch, bracelet): close-up or medium shot focused on the wrist/forearm; \
  character's hand in a natural resting or gesturing pose so the accessory fills a significant \
  portion of the frame
- **Neck/chest accessories** (necklace, locket, tie, scarf): portrait or upper-body shot; \
  accessory centred in frame, not hidden under clothing
- **Head accessories** (cap, hat, sunglasses): portrait or bust shot looking at or slightly away \
  from camera; hat/glasses prominent and fully visible
- **Waist accessories** (belt): mid-body framing showing the waist and the buckle clearly
- **Carried accessories** (bag, backpack, wallet, purse): character holding or carrying it at \
  a natural angle with the bag occupying foreground; use a medium or three-quarter shot so the \
  bag's design and shape are legible
- **Small accessories** (ring, earring, pin): macro or extreme close-up; fill the frame with \
  the accessory and the body part wearing it

**Never choose a wide, full-body, or environment-dominant shot for an accessory — \
the accessory must be immediately visible and identifiable without the viewer searching for it.**
- Quality threshold: score ≥ 7.0 (photorealistic, no AI artefacts, no body deformities, \
  subject clearly visible and correctly used/worn)
- Character match (template mode): generated character must be recognisably the same \
  as the reference template character

## Retry Strategy
**Quality fails:**
When review_quality fails, the result includes `suggested_prompt_adjustments` — concrete \
guidance on what to change in your next prompt. ALWAYS apply those adjustments. Do not \
write a similar prompt and hope for a different result.

If no suggested_prompt_adjustments are provided, use the reason text:
- Subject not visible / too small → use tighter framing, make subject fill the frame, \
  describe the subject as prominently worn/held/used in the foreground
- Subject obscured or blends in → add contrast to the subject, change background, \
  describe the subject as the clear focal point
- Body deformity → switch prompt format, simplify the pose/action, avoid complex gestures
- AI artefacts → reduce scene complexity, avoid busy backgrounds, use simpler lighting

**Character match fails:**
Follow suggested_params returned by check_character_match, or increase lora_strength \
towards 1.3–1.4 and upscale_lora_strength towards 0.8–0.9.

Never exceed your allowed attempt budget.
"""


# ── Agent factory + runner ────────────────────────────────────────────────────

def create_and_run(
    subject: str,
    mode: str,
    lora_name: str | None,
    keyword: str | None,
    scenario: str | None,
    preview_image_url: str | None,
    on_prompt=None,
    on_step=None,  # callback(key: str, status: str, label: str | None = None)
) -> dict:
    """
    Creates and runs an ADK image-gen agent.
    Returns result dict: {r2_path, prompt, score, reason, attempts_used}
    Raises NodeFailed if the agent exhausts attempts without a passing result.
    """
    result_store: dict = {}
    _image_cache: dict[str, bytes] = {}
    _params_cache: dict[str, dict] = {}
    attempt_count = [0]

    # ── Tools (closures so they capture local context) ────────────────────────

    def _step(key: str, status: str, label: str | None = None):
        if on_step:
            on_step(key, status, label)

    def notify_prompt(prompt: str) -> str:
        """
        Call this immediately after deciding on your prompt, before calling submit_image.
        This surfaces the prompt in the UI in real time.

        Args:
            prompt: The exact prompt text you are about to submit.
        Returns:
            Confirmation string.
        """
        if on_prompt:
            on_prompt(prompt)
        _step("prompt", "done")
        return "Prompt received."

    def submit_image(
        prompt: str,
        lora_strength: float = 1.0,
        upscale_lora_strength: float = 0.6,
    ) -> dict:
        """
        Submit a prompt to Z-Image Turbo for image generation.
        In template mode, lora_strength and upscale_lora_strength control character injection.
        In no_template mode, those params are ignored.

        Args:
            prompt: The image generation prompt.
            lora_strength: LoRA strength for the main generation stage (template mode). Range 0.8–1.4.
            upscale_lora_strength: LoRA strength for the upscale refinement stage (template mode). Range 0.4–0.9.
        Returns:
            {"r2_path": str} on success, {"error": str} on failure.
        """
        attempt_count[0] += 1
        _step("submit", "running", f"Generate image (attempt {attempt_count[0]})")
        _step("quality", "pending")
        if mode == "template" and preview_image_url:
            _step("character", "pending")

        seed = random.randint(1, 999_999)
        params = (
            {"lora_strength": lora_strength, "upscale_lora_strength": upscale_lora_strength}
            if mode == "template" else {}
        )
        try:
            r2_path, image_bytes = submit_and_fetch(
                mode=mode,
                prompt=prompt,
                width=1024,
                height=1024,
                lora_name=lora_name,
                seed=seed,
                **params,
            )
        except NodeFailed as e:
            _step("submit", "failed")
            return {"error": str(e)}

        _image_cache[r2_path] = image_bytes
        _params_cache[r2_path] = params
        _step("submit", "done", f"Generated (attempt {attempt_count[0]})")
        _step("quality", "running")
        print(f"[ImageGen agent] attempt={attempt_count[0]} submitted r2={r2_path}")
        return {"r2_path": r2_path}

    def review_quality(r2_path: str) -> dict:
        """
        Review the quality of the generated image against product photography standards.

        Args:
            r2_path: The r2_path returned by submit_image.
        Returns:
            {"score": float, "reason": str, "passed": bool,
             "suggested_prompt_adjustments": str | None}
            Score is 0–10; passed means score ≥ 7.0.
            When passed is False, suggested_prompt_adjustments contains concrete guidance
            on what to change in your next prompt. Always apply it if present.
        """
        image_bytes = _image_cache.get(r2_path)
        if not image_bytes:
            return {"error": "Image not in cache — pass the r2_path from submit_image"}
        result = review(image_bytes, subject)
        if result["passed"]:
            _step("quality", "done")
            if mode == "template" and preview_image_url:
                _step("character", "running")
        else:
            _step("quality", "failed")
            # Reset submit label for the next attempt
            _step("prompt", "running")
        return result

    def check_character_match(r2_path: str) -> dict:
        """
        Check whether the character in the generated image looks like the template reference character.
        Only call this in template mode after review_quality passes.

        Args:
            r2_path: The r2_path returned by submit_image.
        Returns:
            {"passed": bool, "reason": str, "suggested_params": dict | None}
            suggested_params (lora_strength, upscale_lora_strength) are provided when passed is false.
        """
        if not preview_image_url:
            _step("character", "done")
            return {"passed": True, "reason": "No template preview available — skipping character check."}
        image_bytes = _image_cache.get(r2_path)
        if not image_bytes:
            return {"error": "Image not in cache — pass the r2_path from submit_image"}
        params = _params_cache.get(r2_path, {"lora_strength": 1.0, "upscale_lora_strength": 0.6})
        result = review_character(image_bytes, preview_image_url, params)
        if result["passed"]:
            _step("character", "done")
        else:
            _step("character", "failed")
            _step("prompt", "running")
        return result

    def complete_task(
        r2_path: str,
        prompt: str,
        quality_score: float,
        quality_reason: str,
    ) -> str:
        """
        Mark the task as successfully completed. Call this when all checks pass.

        Args:
            r2_path: The r2_path of the accepted image.
            prompt: The prompt that produced it.
            quality_score: The score from review_quality.
            quality_reason: The reason from review_quality.
        Returns:
            Confirmation string.
        """
        result_store["result"] = {
            "r2_path": r2_path,
            "prompt": prompt,
            "score": quality_score,
            "reason": quality_reason,
            "attempts_used": attempt_count[0],
        }
        return "Task completed."

    # ── Build tool list and task message ─────────────────────────────────────
    tools = [notify_prompt, submit_image, review_quality]
    if mode == "template":
        tools.append(check_character_match)
    tools.append(complete_task)

    char_step = (
        f"5. Call check_character_match to verify the character resembles the template.\n"
        f"6. If both checks pass, call complete_task.\n"
    ) if (mode == "template" and preview_image_url) else (
        "5. If quality passes, call complete_task.\n"
    )

    mode_context = (
        f"Mode: template (LoRA character injection active)\n"
        f"Character keyword: '{keyword}'\n"
        f"Template preview: {'available' if preview_image_url else 'not available — skip character check'}\n"
    ) if mode == "template" else (
        f"Mode: no-template (no LoRA, no keyword)\n"
        f"Describe the character in full detail in your prompt (gender, age, ethnicity, hair, face, build, style).\n"
    )

    task_message = (
        f"Generate a product photography image.\n\n"
        f"Subject (product to feature): {subject}\n"
        f"{mode_context}"
        f"Scenario: {scenario if scenario else 'choose an appropriate scenario'}\n"
        f"Maximum submit attempts: {MAX_ATTEMPTS}\n\n"
        f"Sequence:\n"
        f"1. Write a prompt following the style guidelines in your instruction.\n"
        f"2. Call notify_prompt with your prompt.\n"
        f"3. Call submit_image with the prompt (and lora params if template mode).\n"
        f"4. Call review_quality on the result.\n"
        f"{char_step}"
        f"7. If a check fails, revise and retry. You have {MAX_ATTEMPTS} total submits."
    )

    # ── Create agent ──────────────────────────────────────────────────────────
    agent = Agent(
        name="image_gen_agent",
        model="gemini-2.0-flash",
        instruction=_INSTRUCTION,
        tools=tools,
    )

    # ── Run agent (sync wrapper around async ADK) ─────────────────────────────
    async def _run():
        runner = InMemoryRunner(agent=agent, app_name="image_gen")
        session = await runner.session_service.create_session(
            app_name="image_gen", user_id="pipeline"
        )
        events = runner.run_async(
            user_id="pipeline",
            session_id=session.id,
            new_message=Content(role="user", parts=[Part.from_text(text=task_message)]),
        )
        async for _ in events:
            pass  # tools populate result_store as side effects

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()
        asyncio.set_event_loop(None)

    if "result" not in result_store:
        raise NodeFailed(
            f"Agent did not complete image generation after {attempt_count[0]} attempt(s)."
        )
    return result_store["result"]
