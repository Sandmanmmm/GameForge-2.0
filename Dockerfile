# GameForge Multi-Stage Production Dockerfile
# Supports multiple build targets: development, production, gpu-inference, gpu-training
# ========================================================================

# Build Arguments
ARG BUILD_DATE
ARG VCS_REF  
ARG BUILD_VERSION=latest
ARG VARIANT=cpu
ARG PYTHON_VERSION=3.10
ARG NODE_VERSION=20
ARG GPU_BASE_IMAGE=nvidia/cuda:12.1-runtime-alpine
ARG CPU_BASE_IMAGE=python:3.10-alpine
ARG BUILD_ENV=production
ARG ENABLE_GPU=false
ARG SECURITY_HARDENING=true

# ========================================================================
# Stage 1: Base System Setup
# ========================================================================
FROM ${CPU_BASE_IMAGE} AS base-cpu

# GPU base with Python installation (Alpine CUDA doesn't include Python)
FROM ${GPU_BASE_IMAGE} AS base-gpu
RUN apk add --no-cache \
        python3 \
        python3-dev \
        py3-pip \
        && ln -sf python3 /usr/bin/python

# Select base based on variant
FROM base-${VARIANT} AS base-system

# Alpine-specific environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Security: Create non-root user (Alpine style)
RUN addgroup -g 1001 gameforge && \
    adduser -u 1001 -G gameforge -D -h /home/gameforge -s /bin/sh gameforge

# Install system dependencies (Alpine style)
RUN apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    curl \
    wget \
    git \
    build-base \
    ca-certificates \
    linux-headers

# ========================================================================
# Stage 2: Python Dependencies
# ========================================================================
FROM base-system AS python-deps

# Create virtual environment
RUN python${PYTHON_VERSION} -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements*.txt ./

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ========================================================================
# Stage 3: Node.js Dependencies (for frontend builds)
# ========================================================================
FROM node:${NODE_VERSION}-alpine AS node-deps

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# ========================================================================
# Stage 4: Application Base
# ========================================================================
FROM python-deps AS app-base

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=gameforge:gameforge . .

# Install additional Python packages if needed
RUN if [ -f requirements-dev.txt ] && [ "$BUILD_ENV" = "development" ]; then \
        pip install -r requirements-dev.txt; \
    fi

# ========================================================================
# Stage 5: Development Target
# ========================================================================
FROM app-base AS development

# Install development tools
RUN pip install debugpy ipdb

# Set development environment
ENV GAMEFORGE_ENV=development
ENV DEBUG=true
ENV LOG_LEVEL=debug

# Expose debug port
EXPOSE 5678 8080

USER gameforge
CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "src/main.py"]

# ========================================================================
# Stage 6: Production Target (Distroless)
# ========================================================================
FROM gcr.io/distroless/python3-debian12:nonroot AS production

# Copy Python virtual environment from previous stage
COPY --from=python-deps /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code with proper ownership
COPY --from=app-base --chown=nonroot:nonroot /app /app

# Set working directory
WORKDIR /app

# Set production environment
ENV GAMEFORGE_ENV=production
ENV LOG_LEVEL=info
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8080

# Use nonroot user (distroless default)
USER nonroot

# Run application
ENTRYPOINT ["python", "src/main.py"]

# ========================================================================
# Stage 7: GPU Inference Target
# ========================================================================
FROM production AS gpu-inference

# Install GPU-specific dependencies
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# GPU-specific environment
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Specialized entrypoint for inference
CMD ["python", "src/inference_server.py"]

# ========================================================================
# Stage 8: GPU Training Target
# ========================================================================
FROM gpu-inference AS gpu-training

# Install training-specific dependencies
RUN pip install wandb tensorboard accelerate

# Training-specific environment
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024,garbage_collection_threshold:0.6

# Specialized entrypoint for training
CMD ["python", "src/training_server.py"]

# ========================================================================
# Stage 9: Frontend Target
# ========================================================================
FROM node-deps AS frontend

# Copy frontend source
COPY --from=node-deps /app/node_modules ./node_modules
COPY frontend/ ./

# Build frontend
RUN npm run build

# Production frontend with nginx
FROM nginx:alpine AS frontend-production
COPY --from=frontend /app/dist /usr/share/nginx/html
COPY docker/nginx/nginx.conf /etc/nginx/nginx.conf

# Security: Run as non-root
RUN addgroup -g 101 -S nginx && \
    adduser -S -D -H -u 101 -h /var/cache/nginx -s /sbin/nologin -G nginx -g nginx nginx

USER nginx
EXPOSE 80

# ========================================================================
# Stage 10: Monitoring Target
# ========================================================================
FROM production AS monitoring

# Install monitoring dependencies
RUN pip install prometheus-client grafana-api

# Monitoring-specific configuration
ENV METRICS_ENABLED=true
ENV PROMETHEUS_PORT=9090

EXPOSE 9090
CMD ["python", "src/monitoring_server.py"]

# ========================================================================
# Metadata
# ========================================================================
LABEL maintainer="GameForge Team"
LABEL version="${BUILD_VERSION}"
LABEL build-date="${BUILD_DATE}"
LABEL vcs-ref="${VCS_REF}"
LABEL variant="${VARIANT}"
LABEL security-hardened="${SECURITY_HARDENING}"