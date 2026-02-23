# Use the official RunPod ComfyUI base worker
FROM runpod/worker-comfyui:5.7.1-base

# Install boto3 for Cloudflare R2 access
RUN pip install --no-cache-dir boto3

# Copy our custom handler, workflow, and startup script
COPY handler.py /handler.py
COPY LoraWorkflow.json /LoraWorkflow.json
COPY start.sh /start.sh

# Make start script executable
RUN chmod +x /start.sh

WORKDIR /comfyui

CMD [ "/start.sh" ]
