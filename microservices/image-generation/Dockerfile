# Use the official RunPod ComfyUI base worker
FROM runpod/worker-comfyui:5.7.1-base

# Install boto3 for Cloudflare R2 access
RUN pip install --no-cache-dir boto3

# Copy our custom handler and workflow
COPY handler.py /handler.py
COPY LoraWorkflow.json /LoraWorkflow.json

WORKDIR /comfyui
