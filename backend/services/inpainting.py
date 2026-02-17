import replicate
import requests
import os
import uuid


def inpaint_product(template_url, mask_url, lora_version_id, trigger_word,
                    product_description, output_dir="generated"):
    """
    Run SDXL inpainting with trained LoRA weights.
    Places the trained product into the masked area of the template image.

    Args:
        template_url: URL or file path of the template image
        mask_url: URL of the binary mask (white = area to inpaint)
        lora_version_id: The trained LoRA model version (e.g., 'owner/model:version_hash')
        trigger_word: The trigger word used during training (e.g., 'TOK_NIKE')
        product_description: Additional description of the product
        output_dir: Directory to save the output image

    Returns:
        Local file path of the generated image
    """
    os.makedirs(output_dir, exist_ok=True)

    prompt = (
        f"a photo of {trigger_word}, {product_description}, "
        f"professional product photography, high quality, detailed, realistic, "
        f"natural lighting, seamless integration, 8k uhd"
    )

    negative_prompt = (
        "ugly, blurry, low quality, distorted, watermark, text, logo, "
        "bad anatomy, deformed, disfigured, artifacts, unrealistic"
    )

    print(f"[Inpainting] Starting inpainting with LoRA: {lora_version_id}")
    print(f"[Inpainting] Prompt: {prompt}")

    input_params = {
        "image": template_url,
        "mask": mask_url,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "prompt_strength": 0.8,
        "guidance_scale": 7.5,
        "num_inference_steps": 50,
        "width": 1024,
        "height": 1024,
        "scheduler": "DPMSolverMultistep",
    }

    output = replicate.run(
        lora_version_id,
        input=input_params
    )

    # Download the generated image
    image_url = output[0] if isinstance(output, list) else output

    print(f"[Inpainting] Downloading result: {image_url}")

    response = requests.get(str(image_url))
    if response.status_code != 200:
        raise ValueError(f"Failed to download inpainted image: HTTP {response.status_code}")

    filename = f"inpaint_{uuid.uuid4()}.png"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(response.content)

    print(f"[Inpainting] Result saved to: {filepath}")
    return filepath


def inpaint_product_with_local_files(template_path, mask_path, lora_version_id,
                                      trigger_word, product_description, output_dir="generated"):
    """
    Same as inpaint_product but accepts local file paths instead of URLs.
    Opens files and passes them as binary to the Replicate API.
    """
    os.makedirs(output_dir, exist_ok=True)

    prompt = (
        f"a photo of {trigger_word}, {product_description}, "
        f"professional product photography, high quality, detailed, realistic, "
        f"natural lighting, seamless integration, 8k uhd"
    )

    negative_prompt = (
        "ugly, blurry, low quality, distorted, watermark, text, logo, "
        "bad anatomy, deformed, disfigured, artifacts, unrealistic"
    )

    print(f"[Inpainting] Starting inpainting with local files")
    print(f"[Inpainting] Template: {template_path}")
    print(f"[Inpainting] Mask: {mask_path}")

    with open(template_path, 'rb') as template_file, open(mask_path, 'rb') as mask_file:
        input_params = {
            "image": template_file,
            "mask": mask_file,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "prompt_strength": 0.8,
            "guidance_scale": 7.5,
            "num_inference_steps": 50,
            "width": 1024,
            "height": 1024,
            "scheduler": "DPMSolverMultistep",
        }

        output = replicate.run(
            lora_version_id,
            input=input_params
        )

    image_url = output[0] if isinstance(output, list) else output

    print(f"[Inpainting] Downloading result: {image_url}")

    response = requests.get(str(image_url))
    if response.status_code != 200:
        raise ValueError(f"Failed to download inpainted image: HTTP {response.status_code}")

    filename = f"inpaint_{uuid.uuid4()}.png"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(response.content)

    print(f"[Inpainting] Result saved to: {filepath}")
    return filepath
