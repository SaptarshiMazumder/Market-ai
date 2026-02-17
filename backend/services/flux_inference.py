import replicate
import requests
import os
import uuid


def run_flux_lora(
    prompt,
    lora_version_id,
    trigger_word=None,
    width=1024,
    height=1024,
    num_outputs=1,
    lora_scale=1.0,
    num_inference_steps=28,
    guidance_scale=3.5,
    output_format="png",
    output_quality=100,
    prompt_strength=0.8,
    extra_lora_scale=1.0,
    extra_lora=None,
    disable_safety_checker=False,
    seed=None,
    output_dir="generated"
):
    """
    Run Flux.1-dev with trained LoRA weights.
    This replicates the "Run Model" functionality on Replicate.

    Args:
        prompt: The text prompt for image generation
        lora_version_id: The trained LoRA model version (e.g., 'owner/model:version_hash')
        trigger_word: Optional trigger word to prepend to prompt
        width: Output width (default 1024)
        height: Output height (default 1024)
        num_outputs: Number of images to generate (default 1)
        lora_scale: LoRA weight/strength (0.0 to 1.0, default 1.0)
        num_inference_steps: Number of denoising steps (default 28)
        guidance_scale: Guidance scale for prompt adherence (default 3.5)
        output_format: "png" or "webp" (default "png")
        output_quality: Output quality 0-100 (default 100)
        prompt_strength: Prompt strength when using image input (default 0.8)
        extra_lora_scale: Scale for additional LoRA if provided
        extra_lora: URL to additional LoRA weights (optional)
        disable_safety_checker: Disable safety checker (default False)
        seed: Random seed for reproducibility (optional)
        output_dir: Directory to save the output image

    Returns:
        List of local file paths of generated images
    """
    os.makedirs(output_dir, exist_ok=True)

    # Prepend trigger word to prompt if provided
    if trigger_word:
        full_prompt = f"{trigger_word}, {prompt}"
    else:
        full_prompt = prompt

    print(f"[Flux Inference] Running Flux with LoRA: {lora_version_id}")
    print(f"[Flux Inference] Prompt: {full_prompt}")
    print(f"[Flux Inference] LoRA Scale: {lora_scale}")

    # Build input parameters
    input_params = {
        "prompt": full_prompt,
        "width": width,
        "height": height,
        "num_outputs": num_outputs,
        "lora_scale": lora_scale,
        "num_inference_steps": num_inference_steps,
        "guidance_scale": guidance_scale,
        "output_format": output_format,
        "output_quality": output_quality,
        "disable_safety_checker": disable_safety_checker,
    }

    # Add optional parameters
    if seed is not None:
        input_params["seed"] = seed
    if extra_lora:
        input_params["extra_lora"] = extra_lora
        input_params["extra_lora_scale"] = extra_lora_scale

    # Run the model
    output = replicate.run(
        lora_version_id,
        input=input_params
    )

    # Download all generated images
    output_list = output if isinstance(output, list) else [output]
    filepaths = []

    for idx, image_url in enumerate(output_list):
        print(f"[Flux Inference] Downloading result {idx + 1}/{len(output_list)}: {image_url}")

        response = requests.get(str(image_url))
        if response.status_code != 200:
            raise ValueError(f"Failed to download image: HTTP {response.status_code}")

        filename = f"flux_{uuid.uuid4()}.{output_format}"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'wb') as f:
            f.write(response.content)

        print(f"[Flux Inference] Result saved to: {filepath}")
        filepaths.append(filepath)

    return filepaths


def run_flux_lora_with_image(
    prompt,
    image_url_or_path,
    lora_version_id,
    trigger_word=None,
    width=1024,
    height=1024,
    num_outputs=1,
    lora_scale=1.0,
    num_inference_steps=28,
    guidance_scale=3.5,
    prompt_strength=0.8,
    output_format="png",
    output_quality=100,
    seed=None,
    output_dir="generated"
):
    """
    Run Flux.1-dev with trained LoRA weights using an input image (img2img).

    Args:
        prompt: The text prompt for image generation
        image_url_or_path: URL or local path to input image
        lora_version_id: The trained LoRA model version
        trigger_word: Optional trigger word to prepend to prompt
        width: Output width (default 1024)
        height: Output height (default 1024)
        num_outputs: Number of images to generate
        lora_scale: LoRA weight/strength (0.0 to 1.0)
        num_inference_steps: Number of denoising steps
        guidance_scale: Guidance scale for prompt adherence
        prompt_strength: How much to transform the input image (0.0 to 1.0)
        output_format: "png" or "webp"
        output_quality: Output quality 0-100
        seed: Random seed for reproducibility
        output_dir: Directory to save output

    Returns:
        List of local file paths of generated images
    """
    os.makedirs(output_dir, exist_ok=True)

    # Prepend trigger word to prompt if provided
    if trigger_word:
        full_prompt = f"{trigger_word}, {prompt}"
    else:
        full_prompt = prompt

    print(f"[Flux Inference] Running Flux img2img with LoRA: {lora_version_id}")
    print(f"[Flux Inference] Prompt: {full_prompt}")
    print(f"[Flux Inference] Input image: {image_url_or_path}")
    print(f"[Flux Inference] Prompt strength: {prompt_strength}")

    # Build input parameters
    input_params = {
        "image": image_url_or_path,
        "prompt": full_prompt,
        "width": width,
        "height": height,
        "num_outputs": num_outputs,
        "lora_scale": lora_scale,
        "num_inference_steps": num_inference_steps,
        "guidance_scale": guidance_scale,
        "prompt_strength": prompt_strength,
        "output_format": output_format,
        "output_quality": output_quality,
    }

    if seed is not None:
        input_params["seed"] = seed

    # Run the model
    output = replicate.run(
        lora_version_id,
        input=input_params
    )

    # Download all generated images
    output_list = output if isinstance(output, list) else [output]
    filepaths = []

    for idx, image_url in enumerate(output_list):
        print(f"[Flux Inference] Downloading result {idx + 1}/{len(output_list)}: {image_url}")

        response = requests.get(str(image_url))
        if response.status_code != 200:
            raise ValueError(f"Failed to download image: HTTP {response.status_code}")

        filename = f"flux_{uuid.uuid4()}.{output_format}"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'wb') as f:
            f.write(response.content)

        filepaths.append(filepath)

    return filepaths
