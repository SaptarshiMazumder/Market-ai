FROM runpod/worker-comfyui:5.5.1-base

# Install custom nodes
RUN comfy node install --exit-on-fail comfyui_controlnet_aux@1.1.4 --mode remote

# Models are NOT downloaded here — see README.md for all mkdir + wget commands.
# Store models on a RunPod network volume and mount it at /comfyui/models.

COPY handler.py /handler.py
COPY Qwen-Image-Edit-2506-Lightning-Control-Net-Pose.json /Qwen-Image-Edit-2506-Lightning-Control-Net-Pose.json
