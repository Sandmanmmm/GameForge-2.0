#!/bin/bash
# GameForge RTX 4090 Server Startup Script
# This script bypasses sudo issues by running directly

echo "🚀 Starting GameForge RTX 4090 Server..."
echo "📍 Current directory: $(pwd)"
echo "🐍 Python version: $(python3 --version)"

# Navigate to workspace
cd /workspace

# Check if server file exists
if [ -f "gameforge_server.py" ]; then
    echo "✅ Server file found: gameforge_server.py"
else
    echo "❌ Server file not found"
    echo "📂 Available files:"
    ls -la
    exit 1
fi

# Check Python and PyTorch
echo "🔍 Checking environment..."
python3 -c "import torch; print(f'PyTorch {torch.__version__} - CUDA: {torch.cuda.is_available()}')" || echo "❌ PyTorch check failed"

# Start server in background
echo "🚀 Starting server on port 8000..."
nohup python3 gameforge_server.py 8000 > server.log 2>&1 &
SERVER_PID=$!

echo "✅ Server started with PID: $SERVER_PID"
echo "📝 Logs: /workspace/server.log"
echo "🔗 Tunnel: https://moisture-simply-arab-fires.trycloudflare.com"

# Wait a moment and check if server is running
sleep 3
if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✅ Server is running"
    echo "📊 Test with: curl http://localhost:8000/health"
else
    echo "❌ Server failed to start"
    echo "📝 Server log:"
    cat server.log
fi
