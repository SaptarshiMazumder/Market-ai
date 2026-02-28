FROM runpod/worker-comfyui:5.7.1-base

# Custom nodes
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# ComfyUI-segment-anything-2 (SAM2 segmentation + Florence2toCoordinates)
RUN git clone --depth 1 https://github.com/kijai/ComfyUI-segment-anything-2.git \
        /comfyui/custom_nodes/ComfyUI-segment-anything-2 \
    && pip install --no-cache-dir -r /comfyui/custom_nodes/ComfyUI-segment-anything-2/requirements.txt

# ComfyUI-Florence2 (Florence 2 model loader + inference)
RUN git clone --depth 1 https://github.com/kijai/ComfyUI-Florence2.git \
        /comfyui/custom_nodes/ComfyUI-Florence2 \
    && pip install --no-cache-dir -r /comfyui/custom_nodes/ComfyUI-Florence2/requirements.txt

# ComfyUI_essentials (MaskBlur+)
RUN git clone --depth 1 https://github.com/cubiq/ComfyUI_essentials.git \
        /comfyui/custom_nodes/ComfyUI_essentials \
    && ([ -f /comfyui/custom_nodes/ComfyUI_essentials/requirements.txt ] \
        && pip install --no-cache-dir -r /comfyui/custom_nodes/ComfyUI_essentials/requirements.txt || true)

# ComfyUI-KJNodes (ImageAndMaskPreview)
RUN git clone --depth 1 https://github.com/kijai/ComfyUI-KJNodes.git \
        /comfyui/custom_nodes/ComfyUI-KJNodes \
    && ([ -f /comfyui/custom_nodes/ComfyUI-KJNodes/requirements.txt ] \
        && pip install --no-cache-dir -r /comfyui/custom_nodes/ComfyUI-KJNodes/requirements.txt || true)

# R2 client
RUN pip install --no-cache-dir boto3

# Symlink model dirs from network volume into ComfyUI's models directory.
# The custom nodes look up models via folder_paths.models_dir (i.e. /comfyui/models/),
# so symlinks are needed since extra_model_paths.yaml alone won't work for these nodes.
RUN ln -sfn /runpod-volume/models/sam2 /comfyui/models/sam2 \
    && ln -sfn /runpod-volume/models/LLM  /comfyui/models/LLM

# App code
COPY handler.py /handler.py
COPY FlorenceSegmentationMaskingAPI.json /FlorenceSegmentationMaskingAPI.json
COPY extra_model_paths.yaml /comfyui/extra_model_paths.yaml

WORKDIR /comfyui
