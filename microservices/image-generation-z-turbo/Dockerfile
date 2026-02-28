FROM runpod/worker-comfyui:5.7.1-base

# R2 client
RUN pip install --no-cache-dir boto3

# App code
COPY handler.py /handler.py
COPY image_z_image_turbo_api.json /image_z_image_turbo_api.json
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

WORKDIR /comfyui
