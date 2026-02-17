from flask import Blueprint, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import uuid
import traceback

from services.replicate_models import (
    get_or_create_model, ensure_model_exists, slugify, list_trained_models, get_model_details
)
from services.training import start_training, poll_training_status
from models.product import (
    save_product, get_product, list_products, get_trained_products, upsert_trained_product
)

products_bp = Blueprint('products', __name__, url_prefix='/api/products')

TRAINING_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'training')
os.makedirs(TRAINING_UPLOAD_DIR, exist_ok=True)


@products_bp.route('', methods=['GET'])
def get_products():
    """List all registered products."""
    try:
        products = list_products()
        return jsonify({'success': True, 'products': products})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@products_bp.route('/trained', methods=['GET'])
def get_trained():
    """List only products with completed training (have a LoRA version)."""
    try:
        products = get_trained_products()
        return jsonify({'success': True, 'products': products})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@products_bp.route('/<product_name>', methods=['GET'])
def get_single_product(product_name):
    """Get a single product's details."""
    try:
        product = get_product(product_name)
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify({'success': True, 'product': product})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@products_bp.route('/register', methods=['POST'])
def register_product():
    """
    Register a new product. Creates a Replicate model if it doesn't exist.
    Body: { "product_name": "Nike Air Max" }
    """
    try:
        data = request.json
        if not data or 'product_name' not in data:
            return jsonify({'error': 'Missing required field: product_name'}), 400

        product_name = data['product_name'].strip()
        if not product_name:
            return jsonify({'error': 'product_name cannot be empty'}), 400

        # Check if already registered locally
        existing = get_product(product_name)
        if existing:
            return jsonify({
                'success': True,
                'product': existing,
                'message': 'Product already registered'
            })

        # Create model on Replicate
        full_name, model_slug = get_or_create_model(product_name)

        # Save to database
        save_product(product_name, model_slug)

        return jsonify({
            'success': True,
            'product_name': product_name,
            'model_slug': model_slug,
            'replicate_model': full_name,
            'message': 'Product registered successfully'
        })

    except Exception as e:
        print(f"Error registering product: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@products_bp.route('/upload-training-data', methods=['POST'])
def upload_training_data():
    """
    Upload a ZIP file of training images.
    Returns a URL that Replicate can access for training.
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.lower().endswith('.zip'):
            return jsonify({'error': 'Only ZIP files are accepted'}), 400

        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(TRAINING_UPLOAD_DIR, unique_filename)
        file.save(filepath)

        # Generate a URL that serves this file
        # In production, this should be a public URL (S3, etc.)
        file_url = f"/api/products/training-file/{unique_filename}"

        return jsonify({
            'success': True,
            'filename': unique_filename,
            'file_url': file_url,
            'message': 'Training data uploaded successfully'
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@products_bp.route('/training-file/<filename>', methods=['GET'])
def serve_training_file(filename):
    """Serve an uploaded training ZIP file."""
    return send_from_directory(TRAINING_UPLOAD_DIR, filename)


@products_bp.route('/train', methods=['POST'])
def train_product():
    """
    Start LoRA training for a product.
    Body: { "product_name": "Nike Air Max", "zip_url": "https://..." }
    OR: { "product_name": "Nike Air Max", "uploaded_file": "uuid_filename.zip" }
    """
    try:
        data = request.json
        if not data or 'product_name' not in data:
            return jsonify({'error': 'Missing required field: product_name'}), 400

        product_name = data['product_name'].strip()

        # Get or create the Replicate model
        product = get_product(product_name)
        if not product:
            # Auto-register if not yet registered
            full_name, model_slug = get_or_create_model(product_name)
            save_product(product_name, model_slug)
        else:
            # Ensure model still exists in Replicate for this slug
            full_name, _ = ensure_model_exists(product['model_slug'])

        # Determine ZIP URL
        zip_url = data.get('zip_url')
        uploaded_file = data.get('uploaded_file')

        if not zip_url and not uploaded_file:
            return jsonify({'error': 'Provide either zip_url or uploaded_file'}), 400

        if uploaded_file and not zip_url:
            # Build the full URL from the uploaded file
            # This needs the server's public URL in production
            host = request.host_url.rstrip('/')
            zip_url = f"{host}/api/products/training-file/{uploaded_file}"

        # Start training
        training_id, trigger_word = start_training(product_name, zip_url, full_name)

        return jsonify({
            'success': True,
            'training_id': training_id,
            'trigger_word': trigger_word,
            'message': 'Training started. This will take 15-30 minutes.'
        })

    except Exception as e:
        print(f"Error starting training: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@products_bp.route('/train-status/<training_id>', methods=['GET'])
def get_training_status(training_id):
    """Poll training status."""
    try:
        result = poll_training_status(training_id)
        return jsonify({'success': True, **result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@products_bp.route('/import-trained', methods=['POST'])
def import_trained_product():
    """
    Import an already-trained LoRA from Replicate output JSON.
    Body can be either:
      {
        "product_name": "Anime Blue Headphones",
        "version_id": "owner/model:version_hash",
        "trigger_word": "TOK_...",
        "model_slug": "anime-blue-headphones",
        "training_id": "optional"
      }
    OR
      {
        "product_name": "Anime Blue Headphones",
        "replicate_payload": { ... full Replicate training JSON ... }
      }
    """
    try:
        data = request.json or {}
        product_name = (data.get('product_name') or '').strip()
        if not product_name:
            return jsonify({'error': 'Missing required field: product_name'}), 400

        version_id = data.get('version_id')
        trigger_word = data.get('trigger_word')
        model_slug = data.get('model_slug')
        training_id = data.get('training_id')

        payload = data.get('replicate_payload')
        if payload:
            training_id = training_id or payload.get('id')
            version_id = version_id or (payload.get('output') or {}).get('version') or payload.get('version')
            trigger_word = trigger_word or (payload.get('input') or {}).get('token_string')

        if not version_id:
            return jsonify({'error': 'Missing version_id (or replicate_payload.output.version)'}), 400
        if not trigger_word:
            return jsonify({'error': 'Missing trigger_word (or replicate_payload.input.token_string)'}), 400

        if not model_slug:
            # Derive from version_id when possible, otherwise slugify product name
            if '/' in version_id:
                model_slug = version_id.split('/')[-1].split(':')[0]
            else:
                model_slug = slugify(product_name)

        upsert_trained_product(product_name, model_slug, trigger_word, version_id, training_id)

        return jsonify({
            'success': True,
            'product_name': product_name,
            'model_slug': model_slug,
            'version_id': version_id,
            'trigger_word': trigger_word,
            'training_id': training_id,
            'message': 'Trained product imported successfully'
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@products_bp.route('/replicate/list-models', methods=['GET'])
def list_replicate_models():
    """
    Fetch all trained models from Replicate account.
    Returns models with their versions and metadata.
    """
    try:
        models = list_trained_models()

        return jsonify({
            'success': True,
            'models': models,
            'count': len(models)
        })

    except Exception as e:
        print(f"Error fetching Replicate models: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@products_bp.route('/replicate/model-details/<path:model_name>', methods=['GET'])
def get_replicate_model_details(model_name):
    """
    Get detailed information about a specific model from Replicate.
    """
    try:
        model_details = get_model_details(model_name)

        return jsonify({
            'success': True,
            'model': model_details
        })

    except Exception as e:
        print(f"Error fetching model details: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@products_bp.route('/import-from-replicate', methods=['POST'])
def import_from_replicate():
    """
    Import a trained model from Replicate by model name and optional version.
    Makes it easy to select and use existing trained models.

    Body: {
        "model_name": "owner/model-slug" or "model-slug",
        "product_name": "Nike Air Max" (optional, defaults to model name),
        "version_index": 0 (optional, defaults to latest version),
        "trigger_word": "TOK_NIKE" (optional, auto-detected if possible)
    }
    """
    try:
        data = request.json or {}

        if 'model_name' not in data:
            return jsonify({'error': 'Missing required field: model_name'}), 400

        model_name = data['model_name']

        # Get model details from Replicate
        model_details = get_model_details(model_name)

        if not model_details['versions']:
            return jsonify({'error': f'Model "{model_name}" has no trained versions'}), 400

        # Determine which version to use
        version_index = data.get('version_index', 0)
        if version_index >= len(model_details['versions']):
            version_index = 0

        selected_version = model_details['versions'][version_index]
        version_id = f"{model_details['full_name']}:{selected_version['id']}"

        # Determine product name
        product_name = data.get('product_name', model_details['name'].replace('-', ' ').title())

        # Determine trigger word
        trigger_word = data.get('trigger_word')
        if not trigger_word:
            # Try to auto-detect from model metadata
            trigger_word = model_details.get('trigger_word')
            if not trigger_word:
                # Generate a default trigger word
                trigger_word = f"TOK_{product_name.upper().replace(' ', '').replace('-', '')}"

        # Import into database
        model_slug = model_details['name']
        training_id = None  # No training ID since this is an import

        upsert_trained_product(
            product_name=product_name,
            model_slug=model_slug,
            trigger_word=trigger_word,
            version_id=version_id,
            training_id=training_id
        )

        return jsonify({
            'success': True,
            'product_name': product_name,
            'model_slug': model_slug,
            'version_id': version_id,
            'trigger_word': trigger_word,
            'message': f'Successfully imported model "{model_name}"',
            'available_versions': len(model_details['versions'])
        })

    except Exception as e:
        print(f"Error importing from Replicate: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
