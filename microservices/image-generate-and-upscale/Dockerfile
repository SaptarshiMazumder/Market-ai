FROM runpod/worker-comfyui:5.7.1-base

# R2 client
RUN pip install --no-cache-dir boto3

# Install SeedVR2 ComfyUI custom node (registry id: seedvr2_videoupscaler)
# TODO: Replace with the correct repo URL once confirmed
RUN cd /comfyui/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-SeedVR2Wrapper.git && \
    pip install --no-cache-dir -r /comfyui/custom_nodes/ComfyUI-SeedVR2Wrapper/requirements.txt || true

# Install cg-use-everywhere (provides "Anything Everywhere" node — used for global VAE routing)
# NOTE: Our API workflow wires VAE explicitly so this is not strictly required,
# but install it in case the workflow is ever run with a UI snapshot.
# RUN cd /comfyui/custom_nodes && git clone https://github.com/chrisgoringe/cg-use-everywhere.git

# App code
COPY handler.py /handler.py
COPY image_generate_and_upscale_api.json /image_generate_and_upscale_api.json
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

WORKDIR /comfyui
