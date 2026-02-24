FROM runpod/worker-comfyui:5.5.1-base

# --- LAYER 1: Custom nodes ---
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/scraed/LanPaint.git /comfyui/custom_nodes/LanPaint

# --- LAYER 3: Python dependencies ---
RUN pip install --no-cache-dir boto3

# --- LAYER 4: App code ---
COPY handler.py /handler.py
COPY Flux2Klein9bInpaintingAPI.json /Flux2Klein9bInpaintingAPI.json

WORKDIR /comfyui
