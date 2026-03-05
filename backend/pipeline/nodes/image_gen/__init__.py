import os
import requests as _http

from .prompt import generate_scenario
from .runner import NodeFailed
from . import agent as _agent

_TEMPLATES_BASE_URL = os.environ.get("TEMPLATES_SERVICE_URL", "http://localhost:5003")


def _verify_preview(url: str | None) -> str | None:
    """Return url if accessible, else None."""
    if not url:
        return None
    if os.path.exists(url):
        print(f"[ImageGen] Preview image found on disk: {url}")
        return url
    full_url = (_TEMPLATES_BASE_URL + url) if url.startswith("/") else url
    try:
        resp = _http.head(full_url, timeout=5)
        if resp.status_code == 200:
            print(f"[ImageGen] Preview image reachable: {full_url}")
            return url
        print(f"[ImageGen] Preview image not accessible (HTTP {resp.status_code}): {full_url} — skipping character check")
        return None
    except Exception as e:
        print(f"[ImageGen] Preview image check failed: {e} — skipping character check")
        return None


def run(
    subject: str,
    mode: str,
    lora_name: str | None = None,
    keyword: str | None = None,
    template_name: str | None = None,
    preview_image_url: str | None = None,
    scenario: str | None = None,
    width: int = 1024,
    height: int = 1024,
    on_prompt=None,
    on_step=None,
) -> dict:
    # Verify preview image is accessible before starting; fall back to None if not
    preview_image_url = _verify_preview(preview_image_url)

    # Pre-generate scenario once (cheap, non-agentic) so the agent has concrete context
    if template_name and not scenario:
        scenario = generate_scenario(subject, template_name)

    # Agent is about to start writing a prompt
    if on_step:
        on_step("prompt", "running")

    return _agent.create_and_run(
        subject=subject,
        mode=mode,
        lora_name=lora_name,
        keyword=keyword,
        scenario=scenario,
        preview_image_url=preview_image_url,
        on_prompt=on_prompt,
        on_step=on_step,
    )
