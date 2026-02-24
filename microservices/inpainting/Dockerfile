FROM runpod/worker-comfyui:5.5.1-base

# --- LAYER 1: System tools (rarely changes) ---
RUN apt-get update && apt-get install -y wget git && rm -rf /var/lib/apt/lists/*

# --- LAYER 2: Python dependencies (rarely changes) ---
RUN pip install --no-cache-dir boto3

# --- LAYER 3: Custom nodes (changes only if you add/remove nodes) ---
RUN comfy node install --exit-on-fail lanpaint \
    comfyui-florence2 \
    comfyui-segment-anything-2 \
    comfyui-kjnodes \
    rgthree-comfy

# --- LAYER 4: App code (changes most often — always last) ---
COPY handler.py /handler.py
COPY Flux2Klein9bInpainting.json /Flux2Klein9bInpainting.json

WORKDIR /comfyui
CMD ["python3", "-u", "/handler.py"]
