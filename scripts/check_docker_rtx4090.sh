#!/bin/bash
# Docker Status Check and Startup Script for RTX 4090
# Usage: ./check_docker_rtx4090.sh

echo "🔍 Checking Docker status on RTX 4090..."

# Check if Docker daemon is running
if ! systemctl is-active --quiet docker; then
    echo "⚠️  Docker is not running. Starting Docker daemon..."
    systemctl start docker
    sleep 5
    
    # Verify Docker started successfully
    if systemctl is-active --quiet docker; then
        echo "✅ Docker daemon started successfully!"
    else
        echo "❌ Failed to start Docker daemon"
        systemctl status docker
        exit 1
    fi
else
    echo "✅ Docker daemon is already running!"
fi

# Check Docker version and info
echo ""
echo "🐳 Docker Information:"
docker --version
echo ""
echo "📊 Docker System Info:"
docker system info --format "table {{.Name}}\t{{.ServerVersion}}\t{{.OSType}}"

# Check running containers
echo ""
echo "📦 Running Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check Docker Compose
echo ""
echo "🏗️  Docker Compose Information:"
docker-compose --version

# Check available ports
echo ""
echo "🔌 Port Usage Check:"
echo "Port 8080 status:"
netstat -tuln | grep :8080 || echo "Port 8080 is available"
echo "Port 8081 status:"
netstat -tuln | grep :8081 || echo "Port 8081 is available"
echo "Port 8082 status:"
netstat -tuln | grep :8082 || echo "Port 8082 is available"

echo ""
echo "🚀 Docker is ready for GameForge deployment!"