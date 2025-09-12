# GameForge AI - Lightweight Test Dockerfile (Phase 0 Verification)
# This version excludes PyTorch for faster testing of containerization infrastructure

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create user
RUN groupadd -r gameforge && useradd --no-log-init -r -g gameforge gameforge

# Copy requirements (excluding heavy ML dependencies for testing)
COPY requirements.txt .

# Install basic Python dependencies (excluding PyTorch/ML packages for testing)
RUN pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    aiofiles==23.2.1 \
    python-multipart==0.0.6 \
    redis==5.0.1 \
    pillow==10.1.0 \
    aiohttp==3.9.1 \
    python-jose[cryptography]==3.3.0

# Copy application code
COPY gameforge_production_server.py .
COPY auth_middleware.py .

# Create directories
RUN mkdir -p /app/generated_assets /app/logs /app/models_cache /app/config \
    && chown -R gameforge:gameforge /app

# Switch to non-root user
USER gameforge

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/api/v1/health || exit 1

# Expose port
EXPOSE 8080

# Start command
CMD ["python", "-m", "uvicorn", "gameforge_production_server:app", "--host", "0.0.0.0", "--port", "8080"]
