import threading
import time

from orchestration.state import update_pipeline, get_pipeline, update_agent_step
from nodes import image_gen, masking, inpainting
from nodes.image_gen import NodeFailed as ImageGenFailed
from nodes.masking import NodeFailed as MaskingFailed
from nodes.inpainting import NodeFailed as InpaintingFailed


def run_pipeline(pipeline_id: str):
    """
    Runs in a daemon thread.
    Chains: image_gen node → masking node → inpainting node.
    Updates state at every transition so the status route reflects live progress.
    """
    p = get_pipeline(pipeline_id)
    if not p:
        return

    try:
        # ── Node 1: Image Generation ───────────────────────────────────────────
        update_pipeline(pipeline_id, current_node="image_gen")
        result1 = image_gen.run(
            subject=p["subject"],
            mode=p["mode"],
            lora_name=p.get("lora_name"),
            keyword=p.get("keyword"),
            template_name=p.get("template_name"),
            preview_image_url=p.get("preview_image_url"),
            on_prompt=lambda prompt: update_pipeline(pipeline_id, current_prompt=prompt),
            on_step=lambda key, status, label=None: update_agent_step(pipeline_id, key, status, label),
        )
        if not p.get("run_masking", True):
            update_pipeline(pipeline_id, image_gen_result=result1, current_node="done", status="completed", completed_at=time.time())
            print(f"[Orchestrator] Pipeline {pipeline_id} stopped after image_gen (run_masking=False).")
            return

        update_pipeline(pipeline_id, image_gen_result=result1, current_node="masking")

        # ── Node 2: Masking ────────────────────────────────────────────────────
        result2 = masking.run(
            generated_r2=result1["r2_path"],
            subject=p["subject"],
            product_r2=p["product_r2"],
            on_step=lambda key, status, label=None: update_agent_step(pipeline_id, key, status, label, steps_field="masking_agent_steps"),
        )

        if not p.get("run_inpainting", True):
            update_pipeline(pipeline_id, masking_result=result2, current_node="done", status="completed", completed_at=time.time())
            print(f"[Orchestrator] Pipeline {pipeline_id} stopped after masking (run_inpainting=False).")
            return

        update_pipeline(pipeline_id, masking_result=result2, current_node="inpainting")

        # ── Node 3: Inpainting ─────────────────────────────────────────────────
        result3 = inpainting.run(
            masked_r2=result2["r2_path"],
            product_r2=p["product_r2"],
            subject=p["subject"],
            on_prompt=lambda prompt: update_pipeline(pipeline_id, current_inpaint_prompt=prompt),
            on_step=lambda key, status, label=None: update_agent_step(pipeline_id, key, status, label, steps_field="inpainting_agent_steps"),
        )
        update_pipeline(
            pipeline_id,
            inpainting_result=result3,
            current_node="done",
            status="completed",
            completed_at=time.time(),
        )
        print(f"[Orchestrator] Pipeline {pipeline_id} completed.")

    except (ImageGenFailed, MaskingFailed, InpaintingFailed) as e:
        update_pipeline(pipeline_id, status="abandoned", error=str(e))
        print(f"[Orchestrator] Pipeline {pipeline_id} abandoned: {e}")

    except Exception as e:
        update_pipeline(pipeline_id, status="abandoned", error=f"Unexpected error: {e}")
        print(f"[Orchestrator] Pipeline {pipeline_id} unexpected error: {e}")


def start(pipeline_id: str):
    """Spawn orchestrator as a daemon thread."""
    threading.Thread(target=run_pipeline, args=(pipeline_id,), daemon=True).start()
