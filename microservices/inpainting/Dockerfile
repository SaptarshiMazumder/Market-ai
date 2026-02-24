FROM runpod/worker-comfyui:5.5.1-base

# --- LAYER 1: System tools ---
RUN apt-get update && apt-get install -y wget git && rm -rf /var/lib/apt/lists/*

# --- FIX: Update ComfyUI to the latest version to support Flux 2 ---
WORKDIR /comfyui
RUN git pull && pip install --no-cache-dir -r requirements.txt

# --- LAYER 2: Python dependencies ---
RUN pip install --no-cache-dir boto3

# --- LAYER 3: Custom nodes ---
RUN git clone https://github.com/scraed/LanPaint.git /comfyui/custom_nodes/LanPaint
# Ensure you also have the necessary nodes for Flux if not already present
RUN git clone https://github.com/comfyanonymous/ComfyUI_bitsandbytes_NF4.git /comfyui/custom_nodes/ComfyUI_bitsandbytes_NF4

# --- LAYER 4: App code ---
COPY handler.py /handler.py
COPY Flux2Klein9bInpainting.json /Flux2Klein9bInpainting.json

WORKDIR /comfyui