import os

UPLOAD_FOLDER = 'uploads'
GENERATED_FOLDER = 'generated'
TEMPLATE_IMAGES_FOLDER = 'template_images'
DB_PATH = 'market_ai.db'

FLUX_TRAINER_MODEL = "ostris/flux-dev-lora-trainer"
FLUX_TRAINER_VERSION = "e440909d3512c31646ee2e0c7d6f6f4923224863a6a10c494606e79fb5844497"
REPLICATE_OWNER = os.getenv("REPLICATE_OWNER", "saptarshimazumder")
