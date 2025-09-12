#!/bin/bash
echo "========================================"
echo "GameForge AI Dependency Installation"  
echo "========================================"
echo

echo "Upgrading pip..."
python3 -m pip install --upgrade pip

echo
echo "Installing core dependencies..."
pip3 install fastapi uvicorn pydantic python-multipart httpx requests aiofiles

echo
echo "Installing AI/ML pipeline..."
pip3 install torch torchvision diffusers transformers accelerate pillow numpy

echo
echo "Installing database components..."
pip3 install psycopg2-binary asyncpg redis sqlalchemy alembic

echo
echo "Installing authentication..."
pip3 install "python-jose[cryptography]" "passlib[bcrypt]" bcrypt cryptography

echo
echo "Installing utilities..."
pip3 install python-dotenv click rich tqdm psutil typing-extensions pyyaml

echo
echo "Installing development tools..."
pip3 install pytest pytest-asyncio black flake8 mypy

echo
echo "Installing production tools..."
pip3 install gunicorn prometheus-client structlog sentry-sdk

echo
echo "========================================"
echo "Installation Complete!"
echo "========================================"
