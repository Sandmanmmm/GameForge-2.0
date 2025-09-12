#!/bin/bash
# GameForge AI - Model Storage Migration Script
# Migrate 71.63 GB of models to external storage
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="services/asset-gen/models"
BACKUP_DIR="model-backup"

echo "🚀 Starting Model Storage Migration"
echo "=" * 50

# Check current model size
if [ -d "$MODELS_DIR" ]; then
    CURRENT_SIZE=$(du -sh "$MODELS_DIR" | cut -f1)
    echo "📊 Current model storage: $CURRENT_SIZE"
else
    echo "❌ Models directory not found: $MODELS_DIR"
    exit 1
fi

# Create backup before migration
echo "💾 Creating backup..."
mkdir -p "$BACKUP_DIR"
if [ ! -d "$BACKUP_DIR/$(date +%Y%m%d)" ]; then
    cp -r "$MODELS_DIR" "$BACKUP_DIR/$(date +%Y%m%d)-models-backup"
    echo "✅ Backup created: $BACKUP_DIR/$(date +%Y%m%d)-models-backup"
fi

# Start MinIO for local testing
echo "🗄️  Starting MinIO storage..."
docker-compose -f docker-compose.model-storage.yml up -d minio
sleep 10

# Wait for MinIO to be ready
echo "⏳ Waiting for MinIO to be ready..."
until curl -f http://localhost:9000/minio/health/live > /dev/null 2>&1; do
    sleep 2
done
echo "✅ MinIO is ready"

# Upload models to MinIO
echo "📤 Uploading models to external storage..."
python scripts/model-management/model-uploader.py \
    stable-diffusion-xl-base-1.0 \
    "$MODELS_DIR/stable-diffusion-xl-base-1.0" \
    --backend minio \
    --format safetensors fp16.safetensors

# Verify upload
echo "🔍 Verifying upload..."
python scripts/model-management/model-uploader.py stable-diffusion-xl-base-1.0 --verify

# Test download
echo "📥 Testing model download..."
rm -rf /tmp/test-download
python scripts/model-management/model-downloader.py stable-diffusion-xl-base-1.0 --format safetensors fp16.safetensors

if [ -d "/tmp/model-cache/stable-diffusion-xl-base-1.0" ]; then
    echo "✅ Download test successful"
    
    # Calculate space savings
    ORIGINAL_SIZE=$(du -s "$MODELS_DIR" | cut -f1)
    NEW_SIZE=$(du -s "/tmp/model-cache/stable-diffusion-xl-base-1.0" | cut -f1)
    SAVINGS=$((ORIGINAL_SIZE - NEW_SIZE))
    SAVINGS_GB=$((SAVINGS / 1024 / 1024))
    
    echo ""
    echo "💰 SPACE SAVINGS ANALYSIS"
    echo "========================"
    echo "Original size: $ORIGINAL_SIZE KB"
    echo "Optimized size: $NEW_SIZE KB"
    echo "Space saved: $SAVINGS KB (~$SAVINGS_GB GB)"
    echo ""
    
    # Prompt for local model removal
    read -p "🗑️  Remove local models to save space? (y/N): " REMOVE_LOCAL
    if [[ $REMOVE_LOCAL =~ ^[Yy]$ ]]; then
        echo "🧹 Removing local models..."
        mv "$MODELS_DIR" "$BACKUP_DIR/$(date +%Y%m%d)-models-removed"
        mkdir -p "$MODELS_DIR"
        
        # Create placeholder
        cat > "$MODELS_DIR/README.md" << EOF
# GameForge AI Models - External Storage

Models have been migrated to external storage for space optimization.

## Usage

Models are automatically downloaded on-demand using:
```bash
python scripts/model-management/model-downloader.py <model-name>
```

## Available Models

- stable-diffusion-xl-base-1.0 (Text-to-Image)

## Storage Backends

- MinIO (Local): http://localhost:9000
- S3 (Production): s3://gameforge-ai-models

## Configuration

See \`config/models/model-registry.json\` for full configuration.
EOF
        
        echo "✅ Local models removed, saved ~$SAVINGS_GB GB"
        echo "📝 Created README with usage instructions"
    fi
else
    echo "❌ Download test failed"
    exit 1
fi

echo ""
echo "🎉 Model Storage Migration Complete!"
echo "====================================="
echo "• Models uploaded to external storage"
echo "• On-demand downloading configured"
echo "• Docker integration ready"
echo "• Space savings: ~$SAVINGS_GB GB"
echo ""
echo "Next steps:"
echo "1. Test application with: docker-compose -f docker-compose.model-storage.yml up"
echo "2. Set PRELOAD_MODELS=true for production deployment"
echo "3. Configure S3 credentials for production storage"
