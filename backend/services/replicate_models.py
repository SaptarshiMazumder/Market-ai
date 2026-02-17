import replicate
import os
import re

REPLICATE_OWNER = os.getenv("REPLICATE_OWNER", "saptarshimazumder")
REPLICATE_HARDWARE = os.getenv("REPLICATE_HARDWARE", "gpu-t4")


def slugify(name):
    """Convert a product name to a valid Replicate model slug."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug


def get_or_create_model(product_name):
    """
    Check if a model named product_name exists under the owner's account.
    If not, create it. Returns the full model identifier 'owner/name'.
    """
    model_slug = slugify(product_name)
    full_name = f"{REPLICATE_OWNER}/{model_slug}"

    try:
        model = replicate.models.get(full_name)
        print(f"[Model] Found existing model: {full_name}")
        return full_name, model_slug
    except Exception:
        pass

    # Model does not exist, create it
    print(f"[Model] Creating new model: {full_name}")
    model = replicate.models.create(
        owner=REPLICATE_OWNER,
        name=model_slug,
        visibility="private",
        hardware=REPLICATE_HARDWARE
    )
    print(f"[Model] Created model: {full_name}")
    return full_name, model_slug


def ensure_model_exists(model_slug):
    """
    Ensure a Replicate model exists for the given slug under the configured owner.
    Returns the full model identifier 'owner/name'.
    """
    full_name = f"{REPLICATE_OWNER}/{model_slug}"

    try:
        replicate.models.get(full_name)
        print(f"[Model] Found existing model: {full_name}")
        return full_name, model_slug
    except Exception:
        pass

    print(f"[Model] Creating new model: {full_name}")
    replicate.models.create(
        owner=REPLICATE_OWNER,
        name=model_slug,
        visibility="private",
        hardware=REPLICATE_HARDWARE
    )
    print(f"[Model] Created model: {full_name}")
    return full_name, model_slug


def list_trained_models():
    """
    Fetch successful trainings from Replicate.
    Returns a list of trained models from recent trainings using ostris/flux-dev-lora-trainer.
    """
    try:
        print(f"[Model] Fetching Flux trainings...")

        # Get all trainings
        trainings = replicate.trainings.list()

        trained_models = {}

        for training in trainings:
            # Filter for Flux trainer model
            if "ostris/flux-dev-lora-trainer" not in training.model:
                continue

            # Only include successful trainings
            if training.status != "succeeded":
                continue

            # Get output object
            if not hasattr(training, 'output') or not training.output:
                continue

            # The output.version contains the full model string: owner/model:hash
            output = training.output
            if isinstance(output, dict):
                version_id = output.get('version')
            else:
                version_id = getattr(output, 'version', None)

            if not version_id:
                continue

            # Extract destination and hash from version_id
            # Format: owner/model:hash
            if ':' not in version_id:
                continue

            destination, version_hash = version_id.split(':', 1)

            # Extract model info from destination (format: owner/model-name)
            if '/' not in destination:
                continue

            owner, model_name = destination.split('/', 1)

            # Extract trigger word from training input
            trigger_word = None
            if hasattr(training, 'input') and training.input:
                if isinstance(training.input, dict):
                    trigger_word = training.input.get('trigger_word') or training.input.get('token_string')
                else:
                    trigger_word = getattr(training.input, 'trigger_word', None) or getattr(training.input, 'token_string', None)

            # Use model_name as key to avoid duplicates
            if model_name not in trained_models:
                trained_models[model_name] = {
                    'name': model_name,
                    'full_name': destination,
                    'owner': owner,
                    'trigger_word': trigger_word,
                    'description': f'Flux.1-dev LoRA trained model',
                    'visibility': 'private',
                    'url': f'https://replicate.com/{destination}',
                    'version_id': version_id,
                    'versions': []
                }

            # Add this version
            trained_models[model_name]['versions'].append({
                'id': version_hash,  # Just the hash
                'full_id': version_id,  # Full owner/model:hash format
                'created_at': str(getattr(training, 'created_at', '')),
                'training_id': training.id,
                'status': training.status
            })

            # Update trigger word if we found one and didn't have it
            if trigger_word and not trained_models[model_name]['trigger_word']:
                trained_models[model_name]['trigger_word'] = trigger_word

        result = list(trained_models.values())
        print(f"[Model] Found {len(result)} Flux-trained models from trainings")
        return result

    except Exception as e:
        print(f"[Model] Error fetching trainings: {str(e)}")
        raise


def get_model_details(model_name):
    """
    Get detailed information about a specific model.

    Args:
        model_name: Either 'model-slug' or 'owner/model-slug'

    Returns:
        Dictionary with model details and versions
    """
    try:
        # If model_name doesn't include owner, prepend it
        if '/' not in model_name:
            full_name = f"{REPLICATE_OWNER}/{model_name}"
        else:
            full_name = model_name

        print(f"[Model] Fetching details for: {full_name}")
        model = replicate.models.get(full_name)

        model_info = {
            'name': model.name,
            'owner': model.owner,
            'full_name': full_name,
            'description': getattr(model, 'description', ''),
            'visibility': getattr(model, 'visibility', 'private'),
            'url': getattr(model, 'url', ''),
            'versions': []
        }

        # Get all versions
        versions = list(model.versions.list())
        for version in versions:
            version_info = {
                'id': version.id,
                'created_at': str(getattr(version, 'created_at', '')),
                'cog_version': getattr(version, 'cog_version', ''),
            }
            model_info['versions'].append(version_info)

        return model_info

    except Exception as e:
        print(f"[Model] Error fetching model details: {str(e)}")
        raise
