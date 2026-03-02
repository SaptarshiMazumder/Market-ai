FROM runpod/worker-comfyui:5.7.1-base

# R2 client
RUN pip install --no-cache-dir boto3

# Install SeedVR2 ComfyUI custom node (registry id: seedvr2_videoupscaler)
RUN cd /comfyui/custom_nodes && \
    git clone https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler.git seedvr2_videoupscaler && \
    pip install --no-cache-dir -r /comfyui/custom_nodes/seedvr2_videoupscaler/requirements.txt

# App code
COPY handler.py /handler.py
COPY image_generate_and_upscale_api.json /image_generate_and_upscale_api.json
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

WORKDIR /comfyui
