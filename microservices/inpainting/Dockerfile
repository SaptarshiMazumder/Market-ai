FROM runpod/worker-comfyui:5.7.1-base

# Install LanPaint custom node (provides LanPaint_KSampler)
RUN git clone https://github.com/scraed/LanPaint.git /comfyui/custom_nodes/LanPaint && \
    pip install --no-cache-dir -r /comfyui/custom_nodes/LanPaint/requirements.txt

RUN pip install --no-cache-dir boto3

COPY handler.py /handler.py
COPY Flux2Klein9bInpainting.json /Flux2Klein9bInpainting.json

WORKDIR /comfyui
