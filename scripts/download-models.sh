#!/bin/bash
set -e

# Model download script for GameForge AI
# Downloads models from MinIO at runtime instead of baking into images

echo "=== GameForge AI Model Download Script ==="

# Configuration
MINIO_ENDPOINT=${MINIO_ENDPOINT:-"minio:9000"}
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-"gameforge"}
MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-"gameforge123"}
MODELS_DIR=${MODELS_DIR:-"/app/models"}
MODEL_BUCKET=${MODEL_BUCKET:-"gameforge-models"}

# Install minio client if not present
if ! command -v mc &> /dev/null; then
    echo "Installing MinIO client..."
    wget https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/local/bin/mc
    chmod +x /usr/local/bin/mc
fi

# Configure minio client
echo "Configuring MinIO client..."
mc alias set gameforge-minio http://$MINIO_ENDPOINT $MINIO_ACCESS_KEY $MINIO_SECRET_KEY

# Create models directory
mkdir -p $MODELS_DIR

# Function to download model
download_model() {
    local model_name=$1
    local minio_path=$2
    local local_path="$MODELS_DIR/$model_name"
    
    echo "Checking for model: $model_name"
    
    # Check if model already exists locally
    if [ -d "$local_path" ] && [ "$(ls -A $local_path)" ]; then
        echo "✅ Model $model_name already exists locally"
        return 0
    fi
    
    echo "📥 Downloading model $model_name from MinIO..."
    mkdir -p "$local_path"
    
    # Download model files
    if mc cp --recursive gameforge-minio/$MODEL_BUCKET/$minio_path/ "$local_path/"; then
        echo "✅ Model $model_name downloaded successfully"
    else
        echo "❌ Failed to download model $model_name"
        # Try to download from Hugging Face as fallback
        echo "🔄 Attempting Hugging Face fallback..."
        python3 -c "
from transformers import AutoModel, AutoTokenizer
import os
model_name = '$model_name'
local_path = '$local_path'
try:
    model = AutoModel.from_pretrained(model_name, cache_dir=local_path)
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=local_path)
    print(f'✅ Downloaded {model_name} from Hugging Face')
except Exception as e:
    print(f'❌ Failed to download {model_name}: {e}')
"
    fi
}

# Download all required models
echo "Starting model downloads..."

download_model "dialogpt-medium" "text-generation/dialogpt-medium"
download_model "stable-diffusion-v1-5" "image-generation/stable-diffusion-v1-5"
download_model "clip-vit-base" "image-analysis/clip-vit-base"

echo "=== Model download complete ==="

# Verify models are available
echo "Verifying downloaded models..."
python3 -c "
import os
models_dir = os.environ.get('MODELS_DIR', '/app/models')
required_models = ['dialogpt-medium', 'stable-diffusion-v1-5', 'clip-vit-base']

for model in required_models:
    model_path = os.path.join(models_dir, model)
    if os.path.exists(model_path) and os.listdir(model_path):
        print(f'✅ {model} verified')
    else:
        print(f'❌ {model} missing or empty')
        exit(1)

print('🎉 All models verified successfully')
"

echo "🚀 Ready to start GameForge AI services"
