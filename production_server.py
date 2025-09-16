"""
GameForge 2.0 Production Server
Runs the full GameForge application with GitHub OAuth on port 8080
"""
import uvicorn
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the main app
from gameforge.app import app

if __name__ == "__main__":
    print("🚀 Starting GameForge 2.0 Production Server on port 8080...")
    print("📍 GitHub OAuth will be available at: http://localhost:8080/api/v1/auth/github")
    print("📍 Frontend should connect to: http://localhost:8080")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
        access_log=True
    )