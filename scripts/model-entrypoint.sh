#!/bin/bash
# GameForge AI - Model-aware container entrypoint
set -e

echo "🚀 Starting GameForge AI with smart model management..."

# Setup model cache
mkdir -p "$MODEL_CACHE_DIR"
export HF_HOME="$MODEL_CACHE_DIR/huggingface"

# Download required models on startup
if [ "$PRELOAD_MODELS" = "true" ]; then
    echo "📦 Pre-loading required models..."
    python scripts/model-management/model-downloader.py stable-diffusion-xl-base-1.0 --format safetensors fp16.safetensors
fi

# Health check for model availability
python -c "
import sys
import json
from pathlib import Path
from scripts.model_management.model_downloader import SmartModelDownloader

try:
    downloader = SmartModelDownloader()
    # Check if we can access model config
    print('✅ Model management system ready')
except Exception as e:
    print(f'❌ Model management system error: {e}')
    sys.exit(1)
"

echo "🎯 Model management ready, starting application..."

# Execute the main command
exec "$@"
