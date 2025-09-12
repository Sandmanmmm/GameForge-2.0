# AI Inference Service Dockerfile
FROM ghcr.io/sandmanmmm/ai-game-production-p/base-gpu:latest

# Copy AI inference source
COPY src/ai/inference/ ./
COPY src/common/ ./common/
COPY requirements-gpu.txt ./

# Install AI/ML dependencies
RUN pip install --no-cache-dir -r requirements-gpu.txt

# Download and cache models
RUN python download_models.py

# Expose port
EXPOSE 8080

# Health check with GPU validation
HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
    CMD python gpu_health_check.py || exit 1

CMD ["python", "inference_server.py"]