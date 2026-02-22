FROM runpod/worker-comfyui:5.7.1-base

# Install boto3 for Cloudflare R2 access
RUN pip install --no-cache-dir boto3

# Install custom nodes required by the WAN I2V workflow
RUN cd /comfyui/custom_nodes && \
    git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git && \
    pip install --no-cache-dir -r ComfyUI-WanVideoWrapper/requirements.txt && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    pip install --no-cache-dir -r ComfyUI-VideoHelperSuite/requirements.txt

# Copy handler and workflow
COPY handler.py /handler.py
COPY workflow-api-C6gm9qJqfnksxkb0xKgFK.json /workflow-api-C6gm9qJqfnksxkb0xKgFK.json

WORKDIR /comfyui
