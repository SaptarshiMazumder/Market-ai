FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/runpod-volume/.cache/huggingface

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    wget \
    curl \
    unzip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone ai-toolkit and install its dependencies
RUN git clone https://github.com/ostris/ai-toolkit.git /app/ai-toolkit && \
    cd /app/ai-toolkit && \
    git submodule update --init --recursive && \
    pip install --no-cache-dir -r requirements.txt

# Install project-specific Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application files
COPY handler.py /app/handler.py
COPY train_config.py /app/train_config.py
COPY start.sh /app/start.sh
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
