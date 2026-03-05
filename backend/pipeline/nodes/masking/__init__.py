from .runner import NodeFailed, download_r2
from . import agent as _agent


def run(
    generated_r2: str,
    subject: str,
    product_r2: str,
    on_step=None,
) -> dict:
    # Download both images upfront so the agent can see them
    generated_image_bytes = download_r2(generated_r2)
    product_image_bytes = download_r2(product_r2)

    if on_step:
        on_step("submit", "running")

    return _agent.create_and_run(
        subject=subject,
        generated_r2=generated_r2,
        generated_image_bytes=generated_image_bytes,
        product_image_bytes=product_image_bytes,
        on_step=on_step,
    )
