import os
from services.masking import generate_mask, generate_mask_with_description
from services.inpainting import inpaint_product
from models.product import update_batch_item, get_product


def process_batch(batch_job_id, product_name, template_urls, output_dir="generated"):
    """
    Process multiple templates for one product.
    For each template: auto-mask → inpaint with trained LoRA.
    Updates DB status for each item as it completes.
    """
    product = get_product(product_name)
    if not product:
        raise ValueError(f"Product '{product_name}' not found")

    if not product['version_id']:
        raise ValueError(f"Product '{product_name}' has no trained LoRA version")

    lora_version_id = product['version_id']
    trigger_word = product['trigger_word']

    print(f"[Batch] Starting batch processing for '{product_name}'")
    print(f"[Batch] LoRA version: {lora_version_id}")
    print(f"[Batch] Templates: {len(template_urls)}")

    results = []

    for i, template_url in enumerate(template_urls):
        try:
            # Step 1: Generate mask
            print(f"[Batch] Item {i+1}/{len(template_urls)} - Generating mask...")
            update_batch_item(batch_job_id, i, "masking", template_url=template_url)
            mask_path, mask_url = generate_mask(template_url, output_dir)

            # Step 2: Inpaint
            print(f"[Batch] Item {i+1}/{len(template_urls)} - Inpainting...")
            update_batch_item(batch_job_id, i, "inpainting")
            filepath = inpaint_product(
                template_url, mask_url, lora_version_id,
                trigger_word, product_name, output_dir
            )

            update_batch_item(batch_job_id, i, "completed", output_path=filepath)
            results.append({
                "index": i,
                "template": template_url,
                "output": filepath,
                "status": "completed"
            })
            print(f"[Batch] Item {i+1}/{len(template_urls)} - Completed!")

        except Exception as e:
            print(f"[Batch] Item {i+1}/{len(template_urls)} - Failed: {str(e)}")
            update_batch_item(batch_job_id, i, "failed", error=str(e))
            results.append({
                "index": i,
                "template": template_url,
                "error": str(e),
                "status": "failed"
            })

    print(f"[Batch] Batch complete. {sum(1 for r in results if r['status'] == 'completed')}/{len(results)} succeeded.")
    return results
