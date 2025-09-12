# Dataset Versioning API Service Dockerfile
FROM python:3.11-alpine

# Install system dependencies for compilation and Git
RUN apk add --no-cache \
    build-base \
    git \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev \
    && rm -rf /var/cache/apk/*

# Security: Create non-root user
RUN addgroup -g 1001 -S apiuser && \
    adduser -u 1001 -S apiuser -G apiuser

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY dataset_api.py .
COPY dataset_versioning.py .

# Create necessary directories
RUN mkdir -p /app/data /app/logs && \
    chown -R apiuser:apiuser /app

# Security: Switch to non-root user
USER apiuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)"

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "dataset_api:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]