# Hardened Python AI Service Dockerfile (Distroless)
# Optimized for security and minimal attack surface

# Build stage - Alpine for build tools
FROM python:3.11-alpine AS builder
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust \
    && rm -rf /var/cache/apk/*

# Copy and install Python dependencies
COPY requirements*.txt ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage - Distroless (no shell, package manager, etc.)
FROM gcr.io/distroless/python3-debian12:nonroot

# Copy Python packages from builder
COPY --from=builder /root/.local /home/nonroot/.local
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Set path for user-installed packages
ENV PATH=/home/nonroot/.local/bin:$PATH
ENV PYTHONPATH=/home/nonroot/.local/lib/python3.11/site-packages

# Copy application code
COPY --chown=nonroot:nonroot src/ /app/
WORKDIR /app

# Security: Non-root user (distroless default)
USER nonroot

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import requests; requests.get('http://localhost:8000/health')"]

# Run application
ENTRYPOINT ["python", "main.py"]