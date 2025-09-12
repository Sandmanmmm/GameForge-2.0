# GPU-enabled Python Base Image for AI/ML Services (Alpine)
FROM nvidia/cuda:12.1-devel-alpine3.18

# Security: Create non-root user (Alpine style)
RUN addgroup -g 1001 aiuser && \
    adduser -u 1001 -G aiuser -D -h /home/aiuser -s /bin/sh aiuser

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    CUDA_VISIBLE_DEVICES=all

# Install system dependencies (Alpine)
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    gcc \
    g++ \
    musl-dev \
    linux-headers \
    libffi-dev \
    openssl-dev \
    curl \
    git \
    && rm -rf /var/cache/apk/*

# Create symbolic links for Python
RUN ln -sf /usr/bin/python3 /usr/bin/python

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