#!/bin/bash
# GameForge AI External Storage Setup
set -e

echo "=== Setting up GameForge AI External Storage ==="

# Create data directories
sudo mkdir -p /data/gameforge/{models,uploads,cache,postgres,redis,minio,elasticsearch,prometheus,grafana}

# Set proper permissions
sudo chown -R 1001:1001 /data/gameforge/models
sudo chown -R 1001:1001 /data/gameforge/uploads
sudo chown -R 1001:1001 /data/gameforge/cache
sudo chown -R 999:999 /data/gameforge/postgres
sudo chown -R 999:999 /data/gameforge/redis
sudo chown -R 1000:1000 /data/gameforge/minio
sudo chown -R 1000:1000 /data/gameforge/elasticsearch
sudo chown -R 65534:65534 /data/gameforge/prometheus
sudo chown -R 472:472 /data/gameforge/grafana

# Set directory permissions
sudo chmod 755 /data/gameforge
sudo chmod -R 755 /data/gameforge/*

echo "✅ External storage setup complete"
echo "Storage locations:"
echo "  Models: /data/gameforge/models"
echo "  Database: /data/gameforge/postgres"
echo "  Object Storage: /data/gameforge/minio"
echo "  Monitoring: /data/gameforge/{prometheus,grafana}"
