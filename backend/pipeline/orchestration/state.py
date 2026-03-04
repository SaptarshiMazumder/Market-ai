import threading
import time
import uuid

_pipelines: dict = {}
_lock = threading.Lock()


def create_pipeline(
    subject: str,
    mode: str,            # "template" | "no_template"
    product_r2: str,
    lora_name: str | None = None,
    keyword: str | None = None,
) -> str:
    pipeline_id = str(uuid.uuid4())
    with _lock:
        _pipelines[pipeline_id] = {
            "pipeline_id": pipeline_id,
            "status": "running",
            "mode": mode,
            "subject": subject,
            "product_r2": product_r2,
            "lora_name": lora_name,
            "keyword": keyword,
            "current_node": "image_gen",   # "image_gen" | "masking" | "inpainting" | "done"
            "image_gen_result": None,
            "masking_result": None,
            "inpainting_result": None,
            "created_at": time.time(),
            "completed_at": None,
            "error": None,
        }
    return pipeline_id


def update_pipeline(pipeline_id: str, **fields):
    with _lock:
        if pipeline_id in _pipelines:
            _pipelines[pipeline_id].update(fields)


def get_pipeline(pipeline_id: str) -> dict | None:
    with _lock:
        p = _pipelines.get(pipeline_id)
        return dict(p) if p else None


def list_pipelines(limit: int = 50) -> list:
    with _lock:
        items = list(_pipelines.values())
    items.sort(key=lambda p: p["created_at"], reverse=True)
    return [dict(p) for p in items[:limit]]


def get_queue_counts() -> dict:
    """Active pipeline counts per service."""
    counts = {"lora_z_turbo": 0, "z_turbo": 0, "masking": 0, "inpainting": 0}
    with _lock:
        for p in _pipelines.values():
            if p["status"] != "running":
                continue
            node = p.get("current_node")
            if node == "image_gen":
                key = "lora_z_turbo" if p.get("mode") == "template" else "z_turbo"
                counts[key] += 1
            elif node == "masking":
                counts["masking"] += 1
            elif node == "inpainting":
                counts["inpainting"] += 1
    return counts
