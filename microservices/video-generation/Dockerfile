FROM runpod/worker-comfyui:5.7.1-base

RUN pip install --no-cache-dir boto3

COPY handler.py /handler.py
COPY workflow-api-C6gm9qJqfnksxkb0xKgFK.json /workflow-api-C6gm9qJqfnksxkb0xKgFK.json

WORKDIR /comfyui
