from flask import Blueprint, request, jsonify, send_file
import os
import uuid
import threading
import traceback

from services.batch_processor import process_batch
from models.product import create_batch_job, get_batch_status, get_product

batch_bp = Blueprint('batch', __name__, url_prefix='/api/batch')

GENERATED_DIR = os.path.join(os.path.dirname(__file__), '..', 'generated')


@batch_bp.route('/start', methods=['POST'])
def start_batch():
    """
    Start batch processing multiple templates for one product.
    Body: {
        "product_name": "Nike Air Max",
        "template_urls": ["https://...", "https://...", ...]
    }
    """
    try:
        data = request.json
        required = ['product_name', 'template_urls']
        for field in required:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        product_name = data['product_name']
        template_urls = data['template_urls']

        if not isinstance(template_urls, list) or len(template_urls) == 0:
            return jsonify({'error': 'template_urls must be a non-empty list'}), 400

        # Verify product exists and is trained
        product = get_product(product_name)
        if not product:
            return jsonify({'error': f'Product "{product_name}" not found'}), 404
        if not product['version_id']:
            return jsonify({'error': f'Product "{product_name}" has no trained LoRA. Train it first.'}), 400

        # Create batch job
        batch_job_id = str(uuid.uuid4())
        create_batch_job(batch_job_id, product_name, len(template_urls))

        # Start processing in background thread
        thread = threading.Thread(
            target=process_batch,
            args=(batch_job_id, product_name, template_urls, GENERATED_DIR)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'batch_job_id': batch_job_id,
            'total_items': len(template_urls),
            'message': 'Batch processing started'
        })

    except Exception as e:
        print(f"Error starting batch: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@batch_bp.route('/status/<batch_job_id>', methods=['GET'])
def batch_status(batch_job_id):
    """Get batch processing status."""
    try:
        status = get_batch_status(batch_job_id)
        if not status:
            return jsonify({'error': 'Batch job not found'}), 404

        # Add image URLs to completed items
        for item in status['items']:
            if item['output_path']:
                result_id = os.path.basename(item['output_path']).replace('.png', '')
                item['image_url'] = f'/api/generate/result/{result_id}'

        return jsonify({'success': True, **status})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
