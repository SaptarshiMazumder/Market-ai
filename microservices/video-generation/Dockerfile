FROM runpod/worker-comfyui:5.7.1-base

# Install VideoHelperSuite custom node (required for VHS_VideoCombine)
RUN git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git /comfyui/custom_nodes/ComfyUI-VideoHelperSuite && \
    pip install --no-cache-dir -r /comfyui/custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt

RUN pip install --no-cache-dir boto3

COPY handler.py /handler.py
COPY workflow-api-C6gm9qJqfnksxkb0xKgFK.json /workflow-api-C6gm9qJqfnksxkb0xKgFK.json

WORKDIR /comfyui
