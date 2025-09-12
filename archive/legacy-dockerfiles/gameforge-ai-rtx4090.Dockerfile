# GameForge AI System - Production Docker Container
# Phase 0: Foundation Containerization for Multi-Node SaaS
# RTX 4090 Optimized Build with CPU Fallback

FROM ubuntu:22.04 AS base

# Set environment variables for production
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# RTX 4090 Specific Environment Variables
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV CUDA_VERSION=12.1
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Install system dependencies including CUDA support
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3-pip \
    python3.10-venv \
    wget \
    curl \
    git \
    build-essential \
    software-properties-common \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgoogle-perftools4 \
    libtcmalloc-minimal4 \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install CUDA Toolkit (for RTX 4090 support)
RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb \
    && dpkg -i cuda-keyring_1.0-1_all.deb \
    && apt-get update \
    && apt-get install -y cuda-toolkit-12-1 \
    && rm cuda-keyring_1.0-1_all.deb \
    && rm -rf /var/lib/apt/lists/*

# Set CUDA paths
ENV PATH=/usr/local/cuda-12.1/bin:${PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:${LD_LIBRARY_PATH}

# Create application directory and user
WORKDIR /app
RUN groupadd -r gameforge && useradd -r -g gameforge gameforge

# Set up Python environment
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --upgrade pip setuptools wheel

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA support for RTX 4090
RUN pip install torch==2.1.0+cu121 torchvision==0.16.0+cu121 torchaudio==0.16.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

# Install ML dependencies optimized for RTX 4090
RUN pip install \
    transformers==4.35.2 \
    diffusers==0.24.0 \
    accelerate==0.24.1 \
    xformers==0.0.22.post7 \
    safetensors==0.4.0 \
    controlnet-aux==0.0.7 \
    opencv-python==4.8.1.78 \
    pillow==10.1.0 \
    numpy==1.24.3 \
    scipy==1.11.4

# Install FastAPI and server dependencies
RUN pip install \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    aiofiles==23.2.1 \
    python-multipart==0.0.6 \
    redis==5.0.1 \
    celery==5.3.4

# Copy the working GameForge AI system
COPY gameforge_rtx4090_optimized.py ./gameforge_server.py
COPY custom_sdxl_pipeline.py .
COPY sdxl_pipeline/ ./sdxl_pipeline/
COPY security_integration.py .

# Create necessary directories first
RUN mkdir -p /app/generated_assets /app/logs /app/cache /app/models_cache /app/config /app/models /app/static /app/templates

# Create a GPU detection and fallback script
RUN echo '#!/bin/bash\n\
import torch\n\
import os\n\
\n\
def check_gpu_support():\n\
    try:\n\
        if torch.cuda.is_available():\n\
            gpu_count = torch.cuda.device_count()\n\
            gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"\n\
            print(f"GPU Support: Available - {gpu_count} GPU(s) detected")\n\
            print(f"Primary GPU: {gpu_name}")\n\
            # Test RTX 4090 specific features\n\
            if "RTX 4090" in gpu_name or "RTX 5090" in gpu_name:\n\
                print("RTX 4090/5090 detected - Enabling high-performance mode")\n\
                os.environ["GAMEFORGE_GPU_MODE"] = "high_performance"\n\
            else:\n\
                print("Standard GPU detected - Using standard mode")\n\
                os.environ["GAMEFORGE_GPU_MODE"] = "standard"\n\
            return True\n\
        else:\n\
            print("GPU Support: Not available - Using CPU mode")\n\
            os.environ["GAMEFORGE_GPU_MODE"] = "cpu_fallback"\n\
            return False\n\
    except Exception as e:\n\
        print(f"GPU Detection failed: {e} - Using CPU mode")\n\
        os.environ["GAMEFORGE_GPU_MODE"] = "cpu_fallback"\n\
        return False\n\
\n\
if __name__ == "__main__":\n\
    check_gpu_support()\n\
' > /app/gpu_detect.py

# Create health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:8080/health || exit 1' > /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh

# Set permissions
RUN chown -R gameforge:gameforge /app
RUN chmod +x /app/gameforge_server.py /app/gpu_detect.py

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
LABEL description="GameForge AI System - RTX 4090 optimized game asset generation"
LABEL com.gameforge.service="ai-generator"
LABEL com.gameforge.tier="gpu"
LABEL com.gameforge.gpu="rtx4090"

# Configure RTX 4090 specific settings
ENV CUDA_VISIBLE_DEVICES=0
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
ENV CUDA_LAUNCH_BLOCKING=0
ENV TORCH_CUDA_ARCH_LIST="8.9"

# Start with GPU detection and fallback
CMD ["sh", "-c", "python gpu_detect.py && python gameforge_server.py"]
