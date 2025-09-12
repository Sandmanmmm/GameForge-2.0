@echo off
echo ========================================
echo GameForge AI Dependency Installation  
echo ========================================
echo.

echo Upgrading pip...
python.exe -m pip install --upgrade pip

echo.
echo Installing core dependencies...
pip install fastapi uvicorn pydantic python-multipart httpx requests aiofiles

echo.
echo Installing AI/ML pipeline...
pip install torch torchvision diffusers transformers accelerate pillow numpy

echo.
echo Installing database components...
pip install psycopg2-binary asyncpg redis sqlalchemy alembic

echo.
echo Installing authentication...
pip install python-jose[cryptography] passlib[bcrypt] bcrypt cryptography

echo.
echo Installing utilities...
pip install python-dotenv click rich tqdm psutil typing-extensions pyyaml

echo.
echo Installing development tools...
pip install pytest pytest-asyncio black flake8 mypy

echo.
echo Installing production tools...
pip install gunicorn prometheus-client structlog sentry-sdk

echo.
echo ========================================
echo Installation Complete!
echo ========================================
pause
