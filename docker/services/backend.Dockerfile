# Backend API Service Dockerfile
FROM ghcr.io/sandmanmmm/ai-game-production-p/base-python:latest

# Copy backend source
COPY src/backend/api/ ./
COPY src/common/ ./common/
COPY requirements.txt ./

# Install additional backend dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "main:app"]