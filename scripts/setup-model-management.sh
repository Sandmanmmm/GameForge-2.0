#!/bin/bash
# GameForge AI - Quick Model Management Setup
# One-command setup for external model storage

set -e

echo "🚀 GameForge AI - Model Management Quick Setup"
echo "=============================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Install Python dependencies for model management
echo "📦 Installing model management dependencies..."
pip install -r requirements-model-management.txt

# Start MinIO for local development
echo "🗄️  Starting MinIO local storage..."
docker run -d \
  --name gameforge-minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=password123" \
  -v minio-data:/data \
  minio/minio server /data --console-address ":9001"

# Wait for MinIO to be ready
echo "⏳ Waiting for MinIO to start..."
sleep 10

# Verify MinIO is running
until curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; do
    echo "Waiting for MinIO..."
    sleep 2
done

echo "✅ MinIO is ready at http://localhost:9001 (admin/password123)"

# Test model downloader setup
echo "🔧 Testing model downloader configuration..."
python -c "
from scripts.model_management.model_downloader import SmartModelDownloader
try:
    downloader = SmartModelDownloader()
    print('✅ Model downloader configured successfully')
except Exception as e:
    print(f'⚠️  Model downloader setup issue: {e}')
"

# Show current model status
echo "📊 Current Model Status:"
echo "======================="
if [ -d "services/asset-gen/models/stable-diffusion-xl-base-1.0" ]; then
    CURRENT_SIZE=$(du -sh services/asset-gen/models | cut -f1)
    echo "• Local models: $CURRENT_SIZE"
    echo "• Status: Ready for migration"
else
    echo "• Local models: Not found"
    echo "• Status: External storage mode"
fi

echo ""
echo "🎯 NEXT STEPS:"
echo "============="
echo "1. Migrate models to external storage:"
echo "   bash scripts/migrate-model-storage.sh"
echo ""
echo "2. Test model downloading:"
echo "   python scripts/model-management/model-downloader.py stable-diffusion-xl-base-1.0"
echo ""
echo "3. Run health check:"
echo "   python scripts/model-management/health-check.py"
echo ""
echo "4. Start application with model management:"
echo "   docker-compose -f docker-compose.model-storage.yml up"
echo ""
echo "🌐 MinIO Console: http://localhost:9001"
echo "🔑 Credentials: admin / password123"