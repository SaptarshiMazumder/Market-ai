FROM runpod/worker-comfyui:5.7.1-base

# Custom nodes
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# LanPaint — provides LanPaint_KSampler (required by this workflow)
RUN git clone --depth 1 https://github.com/scraed/LanPaint.git \
        /comfyui/custom_nodes/LanPaint \
    && pip install --no-cache-dir -e /comfyui/custom_nodes/LanPaint

# R2 client
RUN pip install --no-cache-dir boto3

# App code
COPY handler.py /handler.py
COPY Flux2Klein9bInpaintingAPI.json /Flux2Klein9bInpaintingAPI.json
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

WORKDIR /comfyui
