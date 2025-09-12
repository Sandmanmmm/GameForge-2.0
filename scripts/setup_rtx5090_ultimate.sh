#!/bin/bash
# GameForge RTX 5090 Ultimate Setup Script
# Instance ID: 25632987

echo "🚀🚀🚀 GAMEFORGE RTX 5090 ULTIMATE SETUP! 🚀🚀🚀"
echo "Instance: 25632987 | GPU: RTX 5090 | VRAM: 31.8GB | Disk: 126GB"
echo ""

# Connect to the instance
echo "📡 Connecting to RTX 5090 instance..."
ssh -L 8888:localhost:8888 -L 8080:localhost:8080 root@ssh8.vast.ai -p 32986 << 'EOF'

echo "✅ Connected to RTX 5090 Ultimate Instance!"
echo "🔍 Checking system specs..."

# Check GPU
nvidia-smi
echo ""

# Check disk space
df -h
echo ""

# Update system
echo "📦 Updating system packages..."
apt update -y
apt install -y git curl wget

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install diffusers transformers accelerate xformers safetensors
pip install fastapi uvicorn pillow numpy requests pydantic python-multipart
pip install opencv-python matplotlib gradio jupyter

# Setup workspace
mkdir -p /workspace
cd /workspace

echo "📚 Creating GameForge RTX 5090 server..."
# Download the notebook we just created
curl -o gameforge_rtx5090_setup.py << 'PYTHON_EOF'
# RTX 5090 Ultimate Setup
import torch
print(f"🎮 GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No GPU'}")
print(f"💾 CUDA Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB" if torch.cuda.is_available() else "No CUDA")
print("✅ RTX 5090 Ultimate ready for GameForge!")
PYTHON_EOF

# Start Jupyter server
echo "🚀 Starting Jupyter server..."
nohup jupyter notebook --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password='' > jupyter.log 2>&1 &

echo "🎯 Setup complete!"
echo "📡 Jupyter: http://localhost:8888"
echo "🌐 Use port forwarding: ssh -L 8888:localhost:8888 root@ssh8.vast.ai -p 32986"
echo "📋 Ready for GameForge RTX 5090 Ultimate deployment!"

EOF
