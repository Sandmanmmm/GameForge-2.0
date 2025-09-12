# GameForge AI System - Lightweight Production Docker Container
# Optimized to prevent bus errors and memory issues during build
FROM ubuntu:22.04

# Set environment variables to prevent memory issues
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Memory optimization for builds
ENV MAKEFLAGS="-j1"
ENV MAX_JOBS=1

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-dev \
    python3-pip \
    python3.10-venv \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create application directory
WORKDIR /app

# Create non-root user
RUN groupadd -r gameforge && useradd -r -g gameforge gameforge

# Set up Python environment
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel --no-cache-dir

# Install lightweight dependencies first
COPY requirements-lightweight.txt .
RUN pip install --no-cache-dir -r requirements-lightweight.txt

# Install PyTorch CPU version (much lighter for testing)
RUN pip install --no-cache-dir torch==2.1.0+cpu torchvision==0.16.0+cpu torchaudio==0.16.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Install essential ML packages one by one
RUN pip install --no-cache-dir transformers==4.35.2
RUN pip install --no-cache-dir accelerate==0.24.1
RUN pip install --no-cache-dir safetensors==0.4.0

# Create necessary directories
RUN mkdir -p /app/generated_assets /app/logs /app/cache /app/models_cache /app/config /app/static

# Copy GameForge AI system files
COPY custom_sdxl_pipeline.py .
COPY sdxl_pipeline/ ./sdxl_pipeline/
COPY gameforge_rtx4090_optimized.py ./gameforge_server.py

# Create a simple security integration file if missing
RUN echo "# Placeholder security integration" > security_integration.py

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

# Add labels
LABEL maintainer="GameForge AI Team"
LABEL version="1.0.0-lightweight"
LABEL description="GameForge AI System - Lightweight CPU version"

# Set CPU-only environment
ENV CUDA_VISIBLE_DEVICES=""
ENV PYTORCH_CUDA_ALLOC_CONF=""

# Start the GameForge AI server
CMD ["python", "gameforge_server.py"]
