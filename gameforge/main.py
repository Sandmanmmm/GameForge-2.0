"""
Main entry point for GameForge application.

This module serves as the entry point for running the GameForge FastAPI
application with proper uvicorn/gunicorn configuration.
"""
import logging
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import after path setup
from gameforge.app import app  # noqa: E402

# Configure logging
# Configure logging
log_dir = os.path.join(project_root, "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "gameforge.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, mode="a")
    ]
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting GameForge application in development mode...")
    
    uvicorn.run(
        "gameforge.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
        access_log=True
    )