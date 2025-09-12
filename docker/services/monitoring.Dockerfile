# Monitoring Service Dockerfile
FROM ghcr.io/sandmanmmm/ai-game-production-p/base-python:latest

# Install monitoring dependencies
RUN pip install --no-cache-dir prometheus-client grafana-api

# Copy monitoring configuration
COPY monitoring/ ./monitoring/
COPY src/common/ ./common/

# Expose monitoring ports
EXPOSE 9090 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9090/-/healthy || exit 1

CMD ["python", "monitoring_server.py"]