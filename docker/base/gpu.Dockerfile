# GPU-enabled Python Base Image for AI/ML Services
FROM nvidia/cuda:12.1-devel-ubuntu22.04

# Security: Run as non-root user
RUN groupadd -r aiuser && useradd -r -g aiuser aiuser

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    CUDA_VISIBLE_DEVICES=all

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    build-essential \
    curl \
    git \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic links for Python
RUN ln -s /usr/bin/python3.11 /usr/bin/python && \
    ln -s /usr/bin/python3.11 /usr/bin/python3

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements-gpu.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir -r requirements-gpu.txt

# Copy application code
COPY --chown=aiuser:aiuser . .

# Switch to non-root user
USER aiuser

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=10s --retries=3 \
    CMD python health_check.py || exit 1

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "ai_server.py"]