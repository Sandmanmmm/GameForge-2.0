# GameForge AI System - Production Docker Container
# Phase 0: Foundation Containerization for Multi-Node SaaS
# RTX 4090 Optimized Build with Bus Error Prevention

FROM ubuntu:22.04

# Set environment variables to prevent memory issues
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=0
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Memory and build optimization
ENV MAKEFLAGS="-j1"
ENV MAX_JOBS=1

# RTX 4090 Specific Environment
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Install system dependencies with smaller memory footprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-dev \
    python3-pip \
    python3.10-venv \
    curl \
    wget \
    git \
    build-essential \
    software-properties-common \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application directory
WORKDIR /app

# Create non-root user
RUN groupadd -r gameforge && useradd -r -g gameforge gameforge

# Set up Python environment with memory optimization
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel with memory limits
RUN pip install --upgrade pip setuptools wheel --no-cache-dir

# Install core dependencies first (lighter packages)
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    aiofiles==23.2.1 \
    python-multipart==0.0.6 \
    redis==5.0.1 \
    celery==5.3.4

# Install basic scientific packages one by one to prevent memory issues
RUN pip install --no-cache-dir numpy==1.24.3
RUN pip install --no-cache-dir pillow==10.1.0
RUN pip install --no-cache-dir scipy==1.11.4
RUN pip install --no-cache-dir opencv-python==4.8.1.78

# Install PyTorch with CUDA support (largest package - install separately)
RUN pip install --no-cache-dir torch==2.1.0+cu121 torchvision==0.16.0+cu121 torchaudio==0.16.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

# Install ML dependencies one by one to prevent bus errors
RUN pip install --no-cache-dir transformers==4.35.2
RUN pip install --no-cache-dir diffusers==0.24.0
RUN pip install --no-cache-dir accelerate==0.24.1
RUN pip install --no-cache-dir safetensors==0.4.0

# Install optional dependencies (can fail gracefully)
RUN pip install --no-cache-dir xformers==0.0.22.post7 || echo "xformers failed - continuing without"
RUN pip install --no-cache-dir controlnet-aux==0.0.7 || echo "controlnet-aux failed - continuing without"

# Copy GameForge AI system files (handle missing files gracefully)
COPY gameforge_rtx4090_optimized.py ./gameforge_server.py
COPY custom_sdxl_pipeline.py .
COPY sdxl_pipeline/ ./sdxl_pipeline/

# Copy optional files if they exist, create directories if they don't
RUN mkdir -p ./config ./static ./models ./templates
COPY security_integration.py ./security_integration.py

# Create necessary directories
RUN mkdir -p /app/generated_assets /app/logs /app/cache /app/models_cache

# Set permissions
RUN chown -R gameforge:gameforge /app
RUN chmod +x /app/gameforge_server.py

# Create health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8080/health || exit 1' > /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh

# Switch to non-root user
USER gameforge

# Expose port
EXPOSE 8080

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/healthcheck.sh

# Add labels for container management
LABEL maintainer="GameForge AI Team"
LABEL version="1.0.0"
LABEL description="GameForge AI System - GPU-accelerated game asset generation"
LABEL com.gameforge.service="ai-generator"
LABEL com.gameforge.tier="gpu"

# Set memory and GPU configuration
ENV CUDA_VISIBLE_DEVICES=0
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Configure memory management
ENV PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:512"
ENV CUDA_LAUNCH_BLOCKING=0

# Start the GameForge AI server
CMD ["python", "gameforge_server.py"]
