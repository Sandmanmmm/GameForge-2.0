# Hardened GPU AI Service Dockerfile (Alpine + Distroless)
# For CUDA-accelerated AI workloads with minimal attack surface

# Build stage - CUDA Alpine for GPU libraries
FROM nvidia/cuda:12.1-devel-alpine3.18 AS builder
WORKDIR /app

# Install build dependencies for GPU libraries
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gcc \
    g++ \
    musl-dev \
    libffi-dev \
    openssl-dev \
    && rm -rf /var/cache/apk/*

# Copy and build GPU-accelerated dependencies
COPY requirements-gpu.txt ./
RUN pip3 install --no-cache-dir --user torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
RUN pip3 install --no-cache-dir --user -r requirements-gpu.txt

# Runtime stage - CUDA Runtime Alpine (minimal)
FROM nvidia/cuda:12.1-runtime-alpine3.18

# Install minimal Python runtime
RUN apk add --no-cache \
    python3 \
    py3-pip \
    dumb-init \
    && rm -rf /var/cache/apk/* \
    && addgroup -g 1001 -S aiuser \
    && adduser -u 1001 -S aiuser -G aiuser

# Copy Python packages from builder
COPY --from=builder /root/.local /home/aiuser/.local

# Set environment for GPU and Python
ENV PATH=/home/aiuser/.local/bin:$PATH
ENV PYTHONPATH=/home/aiuser/.local/lib/python3.11/site-packages
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Copy application code
COPY --chown=aiuser:aiuser src/ /app/
WORKDIR /app

# Security: Non-root user
USER aiuser

# GPU health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["python3", "-c", "import torch; assert torch.cuda.is_available()"]

# Use dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]
CMD ["python3", "ai_service.py"]