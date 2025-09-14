#!/bin/bash
# GameForge RTX 4090 Quick Start Script
# This script starts Docker and launches the production deployer

echo "🚀 GameForge RTX 4090 Quick Start"
echo "=================================="

# Check if we're running as root
if [ "$EUID" -ne 0 ]; then
    echo "⚠️  This script needs root privileges to start Docker"
    echo "💡 Run with: sudo ./start_gameforge_rtx4090.sh"
    exit 1
fi

# Start Docker daemon
echo "🐳 Starting Docker daemon..."
systemctl start docker
systemctl enable docker

# Wait for Docker to be ready
echo "⏳ Waiting for Docker to be ready..."
sleep 3

# Check Docker status
if systemctl is-active --quiet docker; then
    echo "✅ Docker is running!"
    docker --version
else
    echo "❌ Failed to start Docker"
    systemctl status docker
    exit 1
fi

# Check what's using port 8080
echo ""
echo "🔍 Checking port availability..."
if netstat -tuln | grep -q :8080; then
    echo "⚠️  Port 8080 is in use, will use port 8081"
    PORT=8081
else
    echo "✅ Port 8080 is available"
    PORT=8080
fi

# Install Python dependencies if requirements file exists
if [ -f "requirements_production_deployer.txt" ]; then
    echo ""
    echo "📦 Installing Python dependencies..."
    pip install -r requirements_production_deployer.txt
fi

# Start the GameForge Production Deployer
echo ""
echo "🏭 Starting GameForge Production Deployer on port $PORT..."
echo "📚 Access the API docs at: http://localhost:$PORT/docs"
echo "🔍 Health check at: http://localhost:$PORT/health"
echo ""

# Run as the original user (not root)
if [ -n "$SUDO_USER" ]; then
    sudo -u "$SUDO_USER" python3 gameforge_production_deployer.py --port $PORT
else
    python3 gameforge_production_deployer.py --port $PORT
fi