# Pipeline Orchestration Plan
## Market-AI — One-Click Product Photography Pipeline

**Context:** Replace the manual 3-tab flow (Generate → Masking → Inpainting) with a single automated pipeline. User uploads a product image (e.g., a jacket), types the subject, picks a mode (template/no-template), and one click runs three independent groups in sequence. Each group has internal retry logic (up to 3 attempts). Per-service queue counters visible live.

---

## Key Design Principle — 3 Independent Groups

Each group is a black box: takes input dict, returns output dict. **Zero shared code between groups.** The orchestrator only chains them — passing one group's output as the next group's input.

```
Group 1: IMAGE GEN                Group 2: MASKING              Group 3: INPAINTING
─────────────────────────         ─────────────────────         ──────────────────────────
IN:                               IN:                           IN:
  subject, mode, lora_name,         generated_r2, subject,        masked_r2, product_r2,
  keyword, product_r2, params       params                         subject, params

  ┌─────────────────────┐           ┌──────────────────┐          ┌──────────────────────┐
  │ 1. generate_prompt  │           │ 1. RunPod mask   │          │ 1. generate_inpaint_ │
  │ 2. RunPod image gen │ ──fail──► │ 2. review_mask   │ ──fail►  │      prompt          │
  │ 3. review_image_gen │ retry     │    retry masking │ retry    │ 2. RunPod inpainting │
  └─────────────────────┘ ≤3x       └──────────────────┘ ≤3x     │ 3. review_inpaint    │
                                                                   └──────────────────────┘
OUT:                              OUT:                          OUT:                    ≤3x
  {r2_path, prompt,                 {r2_path, score,             {r2_path, prompt,
   score, attempts_used}             attempts_used}               score, attempts_used}
  OR raises PipelineGroupFailed     OR raises PipelineGroupFailed  OR raises PipelineGroupFailed
```

---

## Full Pipeline Flow

```
USER INPUT
  ├─ Product image (upload → R2  products/)
  ├─ Subject text  (e.g. "jacket")
  └─ Mode: [Template] → TemplateGrid → picks lora_name + keyword
           [No Template] → Z-Turbo only

Click "Run Pipeline"
         │
         ▼
  ┌─────────────────────────────────────────────────────┐
  │  GROUP 1: IMAGE GENERATION               QUEUE ←──── active count tracked here
  │                                                     │
  │  generate_prompt(subject, keyword, scenario)        │
  │       ↓                                             │
  │  RunPod (LoRA-Z-Turbo or Z-Turbo)                   │
  │       ↓  result lands in R2  generated/             │
  │  Gemini Vision review (threshold 7.0):              │
  │    • Subject worn correctly?                        │
  │    • Photorealistic? No deformities?                │
  │  FAIL → retry from step 1 (≤3x, tweak params)      │
  │  PASS → output: { generated_r2, prompt, score }    │
  └──────────────────────────────┬──────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────┐
  │  GROUP 2: MASKING                        QUEUE ←──── active count tracked here
  │                                                     │
  │  RunPod masking (object_name = subject)             │
  │       ↓  result lands in R2  masks/                 │
  │  Gemini Vision review (threshold 6.0):              │
  │    • Subject properly isolated?                     │
  │    • Mask not too blurry/fragmented?                │
  │  FAIL → retry from step 1 (≤3x, tweak params)      │
  │  PASS → output: { masked_r2, score }               │
  └──────────────────────────────┬──────────────────────┘
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────┐
  │  GROUP 3: INPAINTING                     QUEUE ←──── active count tracked here
  │                                                     │
  │  generate_inpaint_prompt(subject)                   │
  │       ↓                                             │
  │  RunPod inpainting:                                 │
  │    scene_url  = masked_r2                           │
  │    ref_url    = product_r2 (uploaded image)         │
  │       ↓  result lands in R2  inpainted/             │
  │  Gemini Vision review (threshold 6.5):              │
  │    • Product naturally integrated?                  │
  │    • Realistic lighting? No artifacts?              │
  │  FAIL → retry from step 1 (≤3x, tweak params)      │
  │  PASS → output: { final_r2, prompt, score }        │
  └──────────────────────────────┬──────────────────────┘
                                 │
                                 ▼
                          COMPLETED ✓


QUEUE DASHBOARD (polls /api/pipeline/queues every 5s)
┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ LoRA-Z-Turbo   │ │ Z-Turbo        │ │ Masking        │ │ Inpainting     │
│  active: N     │ │  active: N     │ │  active: N     │ │  active: N     │
└────────────────┘ └────────────────┘ └────────────────┘ └────────────────┘
```

---

## Retry Param Escalation

**Group 1 — Template (LoRA)**
| Attempt | lora_strength | upscale_lora_strength | seed   |
|---------|--------------|----------------------|--------|
| 1       | 1.0          | 0.6                  | random |
| 2       | 1.1          | 0.7                  | random |
| 3       | 1.2          | 0.8                  | random |

**Group 1 — No Template (Z-Turbo):** new random seed each attempt.

**Group 2 — Masking**
| Attempt | mask_blur | mask_dilation | seed   |
|---------|-----------|---------------|--------|
| 1       | 30        | 10            | random |
| 2       | 20        | 15            | random |
| 3       | 15        | 20            | random |

**Group 3 — Inpainting:** new random seed each attempt; steps +2 per retry (4 → 6 → 8).

---

## Pipeline Job State Model

```python
{
  "pipeline_id": str,
  "status": "running" | "completed" | "abandoned",
  "mode": "template" | "no_template",
  "subject": str,
  "product_r2": str,         # r2://bucket/products/uuid.ext

  # Template mode only
  "lora_name": str | None,
  "keyword":   str | None,

  # current group (for queue counting)
  "current_group": "image_gen" | "masking" | "inpainting" | "done",

  # Step results (only set when group passes review)
  "image_gen_result":  { "r2_path", "prompt", "score", "reason", "attempts_used" } | None,
  "masking_result":    { "r2_path", "score", "reason", "attempts_used" } | None,
  "inpainting_result": { "r2_path", "prompt", "score", "reason", "attempts_used" } | None,

  "created_at": float,
  "completed_at": float | None,
  "error": str | None,
}
```

---

## Backend File Structure

```
backend/generate/
└── services/
    └── pipeline/
        ├── __init__.py              (empty)
        ├── state.py                 (thread-safe in-memory pipeline store)
        ├── orchestrator.py          (chains groups 1→2→3, runs in daemon thread)
        └── groups/
            ├── __init__.py          (empty)
            ├── image_gen.py         (Group 1 — fully self-contained)
            ├── masking.py           (Group 2 — fully self-contained)
            └── inpainting.py        (Group 3 — fully self-contained)
routes/
└── pipeline.py                      (5 API routes)
```

### `state.py`
Same pattern as existing `_jobs`/`_lock` stores in routes. Functions:
- `create_pipeline(**kwargs) → str`
- `update_pipeline(id, **fields)`
- `get_pipeline(id) → dict`
- `list_pipelines(limit=50) → list`
- `get_queue_counts() → dict`  — counts `current_group` values across running pipelines

### `groups/image_gen.py` — Group 1 (self-contained)
```python
def run(subject, mode, lora_name, keyword, scenario,
        width, height, lora_strength, upscale_lora_strength) -> dict:
    """
    Tries up to 3 times:
      1. generate_prompt(subject, keyword, scenario)
      2. RunPod submit (LoRA or Z-Turbo based on mode)
      3. Poll RunPod until COMPLETED
      4. download_image(r2_path)
      5. Gemini Vision review — score >= 7.0 → return result
         score < 7.0 → escalate params, loop
    Returns: {"r2_path", "prompt", "score", "reason", "attempts_used"}
    Raises:  PipelineGroupFailed after 3 failed attempts
    """
```
Imports only: `services.image_generation.lora_z_turbo_upscale.runpod`, `services.image_generation.z_turbo.runpod`, `services.image_generation.shared.prompt.generate_prompt`, `services.r2.download_image`, `routes.config.*`
Gemini Vision client created locally in this module.

### `groups/masking.py` — Group 2 (self-contained)
```python
def run(generated_r2, subject, mask_blur, mask_dilation) -> dict:
    """
    Tries up to 3 times:
      1. RunPod masking submit
      2. Poll until COMPLETED
      3. download_image(r2_path)
      4. Gemini Vision review — score >= 6.0 → return result
         score < 6.0 → escalate params, loop
    Returns: {"r2_path", "score", "reason", "attempts_used"}
    Raises:  PipelineGroupFailed after 3 failed attempts
    """
```
Imports only: `services.masking.runpod`, `services.r2.download_image`, `routes.config.MASKING_ENDPOINT_ID`
Gemini Vision client created locally in this module.

### `groups/inpainting.py` — Group 3 (self-contained)
```python
def run(masked_r2, product_r2, subject, steps, denoise, guidance) -> dict:
    """
    Tries up to 3 times:
      1. Gemini generate_inpaint_prompt(subject)
      2. RunPod inpainting submit
      3. Poll until COMPLETED
      4. download_image(r2_path)
      5. Gemini Vision review — score >= 6.5 → return result
         score < 6.5 → new seed + steps+2, loop
    Returns: {"r2_path", "prompt", "score", "reason", "attempts_used"}
    Raises:  PipelineGroupFailed after 3 failed attempts
    """
```
Imports only: `services.inpainting.runpod`, `services.r2.download_image`, `routes.config.INPAINTING_ENDPOINT_ID`
Gemini Vision client created locally in this module.

### `orchestrator.py`
```python
def run_pipeline(pipeline_id: str):
    """Runs in daemon thread. Chains group1 → group2 → group3."""
    p = get_pipeline(pipeline_id)
    try:
        update_pipeline(pipeline_id, current_group="image_gen")
        result1 = image_gen_group.run(...)
        update_pipeline(pipeline_id, image_gen_result=result1, current_group="masking")

        result2 = masking_group.run(result1["r2_path"], p["subject"], ...)
        update_pipeline(pipeline_id, masking_result=result2, current_group="inpainting")

        result3 = inpainting_group.run(result2["r2_path"], p["product_r2"], p["subject"], ...)
        update_pipeline(pipeline_id, inpainting_result=result3, current_group="done",
                        status="completed", completed_at=time.time())
    except PipelineGroupFailed as e:
        update_pipeline(pipeline_id, status="abandoned", error=str(e))
```

### `routes/pipeline.py`
```
POST /api/pipeline/upload     → upload product image → R2 products/, return {r2_path, preview_url}
POST /api/pipeline/submit     → create state, spawn orchestrator thread, return {pipeline_id}
GET  /api/pipeline/status/:id → return full pipeline state
GET  /api/pipeline/list       → return list_pipelines(50)
GET  /api/pipeline/queues     → return get_queue_counts()
```

---

## Frontend File Structure

```
frontend/src/
├── components/
│   ├── PipelineTab.jsx        (new — owns polling, renders form + dashboard + job list)
│   └── QueueDashboard.jsx     (new — 4 service cards with active counts)
└── services/
    └── api.js                 (add 5 new pipeline functions)
```

### `api.js` additions
- `uploadProductImage(file)` — POST /api/pipeline/upload (FormData)
- `submitPipeline({subject, mode, product_r2, lora_name, keyword})` — POST /api/pipeline/submit
- `getPipelineStatus(id)` — GET /api/pipeline/status/:id
- `listPipelines()` — GET /api/pipeline/list
- `getPipelineQueues()` — GET /api/pipeline/queues

### `PipelineTab.jsx` layout
```
[ QueueDashboard — 4 cards, auto-refresh every 5s ]

Form:
  [ Upload product image ]  ← preview thumbnail shown after upload
  [ Subject: __________ ]
  ( ) Use Template  → shows TemplateGrid (reuse existing component)
  ( ) Custom Prompt → no template grid
  [ Run Pipeline ] button

Job List (newest first):
  Each card:
    - Subject + created time + status badge
    - Step timeline: [Group 1 ✓ score:8.2] → [Group 2 ✓ score:7.1] → [Group 3 ⏳]
    - Thumbnails per group (presigned preview_url from r2_path)
    - Final image large preview when completed
    - "Abandoned at Group N: reason" if failed
```

---

## Files to Create / Modify

| File | Action |
|------|--------|
| `backend/generate/services/r2.py` | add `upload_product_image()` |
| `backend/generate/services/pipeline/__init__.py` | create (empty) |
| `backend/generate/services/pipeline/state.py` | create |
| `backend/generate/services/pipeline/orchestrator.py` | create |
| `backend/generate/services/pipeline/groups/__init__.py` | create (empty) |
| `backend/generate/services/pipeline/groups/image_gen.py` | create |
| `backend/generate/services/pipeline/groups/masking.py` | create |
| `backend/generate/services/pipeline/groups/inpainting.py` | create |
| `backend/generate/routes/pipeline.py` | create |
| `backend/generate/app.py` | register pipeline_bp |
| `frontend/vite.config.js` | add /api/pipeline proxy |
| `frontend/src/services/api.js` | add 5 pipeline functions |
| `frontend/src/components/QueueDashboard.jsx` | create |
| `frontend/src/components/PipelineTab.jsx` | create |
| `frontend/src/App.jsx` | add Pipeline tab |

## Existing Code to Reuse (do not rewrite)

| What | File |
|------|------|
| `submit_job` / `get_job_status` LoRA | `services/image_generation/lora_z_turbo_upscale/runpod.py` |
| `submit_job` / `get_job_status` Z-Turbo | `services/image_generation/z_turbo/runpod.py` |
| `submit_job` / `get_job_status` Masking | `services/masking/runpod.py` |
| `submit_job` / `get_job_status` Inpainting | `services/inpainting/runpod.py` |
| `generate_prompt()` | `services/image_generation/shared/prompt.py` |
| `download_image()` | `services/r2.py` |
| `TemplateGrid` component | `frontend/src/components/TemplateGrid.jsx` |
| RunPod endpoint constants | `routes/config.py` |

## Implementation Order
1. `services/pipeline/state.py`
2. `services/pipeline/groups/image_gen.py`
3. `services/pipeline/groups/masking.py`
4. `services/pipeline/groups/inpainting.py`
5. `services/pipeline/orchestrator.py`
6. `routes/pipeline.py` + `services/r2.py` (add upload_product_image) + wire into `app.py`
7. Frontend: `api.js` → `vite.config.js` → `QueueDashboard.jsx` → `PipelineTab.jsx` → `App.jsx`

## Verification
1. `POST /api/pipeline/upload` with image → `{r2_path, preview_url}`
2. `POST /api/pipeline/submit` → `{pipeline_id}`
3. Poll `GET /api/pipeline/status/:id` — `current_group` advances: `image_gen` → `masking` → `inpainting` → `done`
4. `GET /api/pipeline/queues` → non-zero active counts while pipeline runs
5. Frontend: upload jacket.jpg, type "jacket", pick template, click Run → queue dashboard increments → job card steps fill in with scores → final image appears

## R2 Bucket Structure (same bucket, separate prefixes)
- `products/`   — uploaded product images
- `generated/`  — Group 1 output images
- `masks/`      — Group 2 output images
- `inpainted/`  — Group 3 output images
