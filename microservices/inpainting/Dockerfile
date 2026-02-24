FROM runpod/worker-comfyui:5.5.1-base

# --- LAYER 1: Custom nodes (installs via comfy CLI, matches Comfy Cloud approach) ---
RUN comfy node install --exit-on-fail rgthree-comfy@1.0.2512112053 --mode remote
RUN comfy node install --exit-on-fail lanpaint@1.4.13

# --- LAYER 3: Python dependencies ---
RUN pip install --no-cache-dir boto3

# --- LAYER 4: App code ---
COPY handler.py /handler.py
COPY Flux2Klein9bInpaintingAPI.json /Flux2Klein9bInpaintingAPI.json

WORKDIR /comfyui
