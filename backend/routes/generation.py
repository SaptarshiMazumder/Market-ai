from flask import Blueprint, request, jsonify, send_file
import os
import uuid
import traceback

from services.masking import generate_mask, generate_mask_with_description
from services.masking import MaskingError
from services.inpainting import inpaint_product
from services.flux_inference import run_flux_lora, run_flux_lora_with_image
from models.product import get_product

generation_bp = Blueprint('generation', __name__, url_prefix='/api/generate')

GENERATED_DIR = os.path.join(os.path.dirname(__file__), '..', 'generated')
os.makedirs(GENERATED_DIR, exist_ok=True)


@generation_bp.route('/mask', methods=['POST'])
def create_mask():
    """
    Generate a segmentation mask for a template image.
    Body: { "template_url": "https://...", "object_description": "shoes" (optional) }
    """
    try:
        data = request.json
        if not data or 'template_url' not in data:
            return jsonify({'error': 'Missing required field: template_url'}), 400

        template_url = data['template_url']
        object_description = data.get('object_description')

        if object_description:
            mask_path, mask_url = generate_mask_with_description(
                template_url, object_description, GENERATED_DIR
            )
        else:
            mask_path, mask_url = generate_mask(template_url, GENERATED_DIR)

        # Create a job ID for serving the mask
        mask_id = os.path.basename(mask_path).replace('.png', '')

        return jsonify({
            'success': True,
            'mask_id': mask_id,
            'mask_url': mask_url,
            'local_mask_url': f'/api/generate/mask-image/{mask_id}'
        })

    except MaskingError as e:
        # Keep status 500 per product decision, but return a stable code and clearer message.
        print(f"MaskingError: {str(e)}")
        if getattr(e, "details", None):
            print(f"MaskingError details: {e.details}")
        return jsonify({
            'error': str(e),
            'code': getattr(e, "code", "MASKING_FAILED"),
        }), 500
    except Exception as e:
        print(f"Error generating mask: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@generation_bp.route('/mask-image/<mask_id>', methods=['GET'])
def serve_mask_image(mask_id):
    """Serve a generated mask image."""
    filepath = os.path.join(GENERATED_DIR, f"{mask_id}.png")
    if not os.path.exists(filepath):
        return jsonify({'error': 'Mask not found'}), 404
    return send_file(filepath, mimetype='image/png')


@generation_bp.route('/inpaint', methods=['POST'])
def create_inpainting():
    """
    Run inpainting with a trained LoRA.
    Body: {
        "template_url": "https://...",
        "mask_url": "https://...",
        "product_name": "Nike Air Max",
        "product_description": "red and white running shoes" (optional)
    }
    """
    try:
        data = request.json
        required = ['template_url', 'mask_url', 'product_name']
        for field in required:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        product_name = data['product_name']
        product = get_product(product_name)

        if not product:
            return jsonify({'error': f'Product "{product_name}" not found'}), 404

        if not product['version_id']:
            return jsonify({'error': f'Product "{product_name}" has no trained LoRA. Train it first.'}), 400

        product_description = data.get('product_description', product_name)

        filepath = inpaint_product(
            template_url=data['template_url'],
            mask_url=data['mask_url'],
            lora_version_id=product['version_id'],
            trigger_word=product['trigger_word'],
            product_description=product_description,
            output_dir=GENERATED_DIR
        )

        result_id = os.path.basename(filepath).replace('.png', '')

        return jsonify({
            'success': True,
            'result_id': result_id,
            'image_url': f'/api/generate/result/{result_id}'
        })

    except Exception as e:
        print(f"Error inpainting: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@generation_bp.route('/pipeline', methods=['POST'])
def full_pipeline():
    """
    Full pipeline: auto-mask template → inpaint with trained LoRA.
    Body: {
        "template_url": "https://...",
        "product_name": "Nike Air Max",
        "product_description": "red and white running shoes" (optional),
        "object_description": "shoes" (optional, for mask prompt)
    }
    """
    try:
        data = request.json
        required = ['template_url', 'product_name']
        for field in required:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        product_name = data['product_name']
        product = get_product(product_name)

        if not product:
            return jsonify({'error': f'Product "{product_name}" not found'}), 404

        if not product['version_id']:
            return jsonify({'error': f'Product "{product_name}" has no trained LoRA. Train it first.'}), 400

        template_url = data['template_url']
        object_description = data.get('object_description')
        product_description = data.get('product_description', product_name)

        # Step 1: Generate mask
        print(f"[Pipeline] Step 1: Generating mask...")
        if object_description:
            mask_path, mask_url = generate_mask_with_description(
                template_url, object_description, GENERATED_DIR
            )
        else:
            mask_path, mask_url = generate_mask(template_url, GENERATED_DIR)

        mask_id = os.path.basename(mask_path).replace('.png', '')

        # Step 2: Inpaint
        print(f"[Pipeline] Step 2: Inpainting with LoRA...")
        filepath = inpaint_product(
            template_url=template_url,
            mask_url=mask_url,
            lora_version_id=product['version_id'],
            trigger_word=product['trigger_word'],
            product_description=product_description,
            output_dir=GENERATED_DIR
        )

        result_id = os.path.basename(filepath).replace('.png', '')

        return jsonify({
            'success': True,
            'result_id': result_id,
            'mask_id': mask_id,
            'image_url': f'/api/generate/result/{result_id}',
            'mask_url': f'/api/generate/mask-image/{mask_id}'
        })

    except Exception as e:
        print(f"Error in pipeline: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@generation_bp.route('/result/<result_id>', methods=['GET'])
def serve_result(result_id):
    """Serve a generated result image."""
    filepath = os.path.join(GENERATED_DIR, f"{result_id}.png")
    if not os.path.exists(filepath):
        return jsonify({'error': 'Result not found'}), 404
    return send_file(filepath, mimetype='image/png')


@generation_bp.route('/download/<result_id>', methods=['GET'])
def download_result(result_id):
    """Download a generated result image."""
    filepath = os.path.join(GENERATED_DIR, f"{result_id}.png")
    if not os.path.exists(filepath):
        return jsonify({'error': 'Result not found'}), 404
    return send_file(filepath, as_attachment=True, download_name=f'product_image_{result_id}.png')


@generation_bp.route('/flux-lora', methods=['POST'])
def run_trained_lora():
    """
    Run a trained Flux LoRA model (text-to-image).
    Provides full control over all parameters, just like Replicate's "Run Model" interface.

    Body: {
        "product_name": "Nike Air Max",  // Required
        "prompt": "running shoes on a track",  // Required
        "width": 1024,  // Optional, default 1024
        "height": 1024,  // Optional, default 1024
        "num_outputs": 1,  // Optional, default 1
        "lora_scale": 1.0,  // Optional, default 1.0 (LoRA weight)
        "num_inference_steps": 28,  // Optional, default 28
        "guidance_scale": 3.5,  // Optional, default 3.5
        "output_format": "png",  // Optional, "png" or "webp"
        "output_quality": 100,  // Optional, 0-100
        "seed": null,  // Optional, for reproducibility
        "disable_safety_checker": false  // Optional
    }
    """
    try:
        data = request.json
        if not data or 'product_name' not in data or 'prompt' not in data:
            return jsonify({'error': 'Missing required fields: product_name, prompt'}), 400

        product_name = data['product_name']
        product = get_product(product_name)

        if not product:
            return jsonify({'error': f'Product "{product_name}" not found'}), 404

        if not product['version_id']:
            return jsonify({'error': f'Product "{product_name}" has no trained LoRA. Train it first.'}), 400

        # Extract parameters with defaults
        prompt = data['prompt']
        width = data.get('width', 1024)
        height = data.get('height', 1024)
        num_outputs = data.get('num_outputs', 1)
        lora_scale = data.get('lora_scale', 1.0)
        num_inference_steps = data.get('num_inference_steps', 28)
        guidance_scale = data.get('guidance_scale', 3.5)
        output_format = data.get('output_format', 'png')
        output_quality = data.get('output_quality', 100)
        seed = data.get('seed')
        disable_safety_checker = data.get('disable_safety_checker', False)

        # Run the model
        filepaths = run_flux_lora(
            prompt=prompt,
            lora_version_id=product['version_id'],
            trigger_word=product.get('trigger_word'),
            width=width,
            height=height,
            num_outputs=num_outputs,
            lora_scale=lora_scale,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            output_format=output_format,
            output_quality=output_quality,
            seed=seed,
            disable_safety_checker=disable_safety_checker,
            output_dir=GENERATED_DIR
        )

        # Build response with all generated images
        results = []
        for filepath in filepaths:
            result_id = os.path.basename(filepath).rsplit('.', 1)[0]
            results.append({
                'result_id': result_id,
                'image_url': f'/api/generate/result-file/{result_id}.{output_format}'
            })

        return jsonify({
            'success': True,
            'results': results,
            'num_generated': len(results)
        })

    except Exception as e:
        print(f"Error running Flux LoRA: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@generation_bp.route('/flux-lora-img2img', methods=['POST'])
def run_trained_lora_img2img():
    """
    Run a trained Flux LoRA model with an input image (image-to-image).

    Body: {
        "product_name": "Nike Air Max",  // Required
        "prompt": "running shoes on a track",  // Required
        "image_url": "https://...",  // Required (or image_path for local files)
        "width": 1024,  // Optional
        "height": 1024,  // Optional
        "num_outputs": 1,  // Optional
        "lora_scale": 1.0,  // Optional (LoRA weight)
        "prompt_strength": 0.8,  // Optional, how much to transform the image
        "num_inference_steps": 28,  // Optional
        "guidance_scale": 3.5,  // Optional
        "output_format": "png",  // Optional
        "output_quality": 100,  // Optional
        "seed": null  // Optional
    }
    """
    try:
        data = request.json
        required_fields = ['product_name', 'prompt', 'image_url']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        product_name = data['product_name']
        product = get_product(product_name)

        if not product:
            return jsonify({'error': f'Product "{product_name}" not found'}), 404

        if not product['version_id']:
            return jsonify({'error': f'Product "{product_name}" has no trained LoRA. Train it first.'}), 400

        # Extract parameters
        prompt = data['prompt']
        image_url = data['image_url']
        width = data.get('width', 1024)
        height = data.get('height', 1024)
        num_outputs = data.get('num_outputs', 1)
        lora_scale = data.get('lora_scale', 1.0)
        prompt_strength = data.get('prompt_strength', 0.8)
        num_inference_steps = data.get('num_inference_steps', 28)
        guidance_scale = data.get('guidance_scale', 3.5)
        output_format = data.get('output_format', 'png')
        output_quality = data.get('output_quality', 100)
        seed = data.get('seed')

        # Run the model
        filepaths = run_flux_lora_with_image(
            prompt=prompt,
            image_url_or_path=image_url,
            lora_version_id=product['version_id'],
            trigger_word=product.get('trigger_word'),
            width=width,
            height=height,
            num_outputs=num_outputs,
            lora_scale=lora_scale,
            prompt_strength=prompt_strength,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            output_format=output_format,
            output_quality=output_quality,
            seed=seed,
            output_dir=GENERATED_DIR
        )

        # Build response
        results = []
        for filepath in filepaths:
            result_id = os.path.basename(filepath).rsplit('.', 1)[0]
            results.append({
                'result_id': result_id,
                'image_url': f'/api/generate/result-file/{result_id}.{output_format}'
            })

        return jsonify({
            'success': True,
            'results': results,
            'num_generated': len(results)
        })

    except Exception as e:
        print(f"Error running Flux LoRA img2img: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@generation_bp.route('/result-file/<filename>', methods=['GET'])
def serve_result_file(filename):
    """Serve a generated result file (supports multiple formats)."""
    filepath = os.path.join(GENERATED_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'Result not found'}), 404

    # Determine mime type from extension
    ext = filename.rsplit('.', 1)[-1].lower()
    mime_types = {
        'png': 'image/png',
        'webp': 'image/webp',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg'
    }
    mime_type = mime_types.get(ext, 'image/png')

    return send_file(filepath, mimetype=mime_type)
