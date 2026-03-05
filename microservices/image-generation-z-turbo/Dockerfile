FROM runpod/worker-comfyui:5.7.1-base

# R2 client
RUN pip install --no-cache-dir boto3

# App code
COPY handler.py /handler.py
COPY DualLoraZTurboAPI.json /DualLoraZTurboAPI.json
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

WORKDIR /comfyui
