from .runner import NodeFailed, download_r2
from . import agent as _agent


def run(
    masked_r2: str,
    product_r2: str,
    subject: str,
    on_prompt=None,
    on_step=None,
) -> dict:
    # Download both images upfront so the agent can see them
    masked_image_bytes = download_r2(masked_r2)
    product_image_bytes = download_r2(product_r2)

    if on_step:
        on_step("prompt", "running")

    return _agent.create_and_run(
        subject=subject,
        masked_r2=masked_r2,
        product_r2=product_r2,
        masked_image_bytes=masked_image_bytes,
        product_image_bytes=product_image_bytes,
        on_prompt=on_prompt,
        on_step=on_step,
    )
