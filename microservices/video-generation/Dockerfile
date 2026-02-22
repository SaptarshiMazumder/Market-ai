FROM runpod/worker-comfyui:5.7.1-base

# Install boto3 for Cloudflare R2 access
RUN pip install --no-cache-dir boto3

# Copy handler and workflow
COPY handler.py /handler.py
COPY wanI2bWorkflow.json /wanI2bWorkflow.json

# Copy and set up start script
COPY start.sh /start.sh
RUN sed -i 's/\r$//' /start.sh && chmod +x /start.sh

WORKDIR /comfyui

CMD ["/start.sh"]
