# AI Training Service Dockerfile
FROM ghcr.io/sandmanmmm/ai-game-production-p/base-gpu:latest

# Copy AI training source
COPY src/ai/training/ ./
COPY src/ai/datasets/ ./datasets/
COPY src/common/ ./common/
COPY requirements-gpu.txt ./

# Install training dependencies
RUN pip install --no-cache-dir -r requirements-gpu.txt && \
    pip install --no-cache-dir wandb tensorboard

# Create directories for model outputs
RUN mkdir -p /app/models /app/logs /app/checkpoints

# Expose port for monitoring
EXPOSE 6006

# Health check
HEALTHCHECK --interval=120s --timeout=60s --start-period=60s --retries=3 \
    CMD python training_health_check.py || exit 1

CMD ["python", "training_pipeline.py"]