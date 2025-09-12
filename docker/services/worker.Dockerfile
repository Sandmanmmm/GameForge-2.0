# Worker Service Dockerfile
FROM ghcr.io/sandmanmmm/ai-game-production-p/base-python:latest

# Copy worker source
COPY src/backend/worker/ ./
COPY src/common/ ./common/
COPY requirements.txt ./

# Install worker dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir celery redis

# Expose port for monitoring
EXPOSE 5555

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD celery -A worker.celery inspect ping || exit 1

CMD ["celery", "-A", "worker.celery", "worker", "--loglevel=info"]