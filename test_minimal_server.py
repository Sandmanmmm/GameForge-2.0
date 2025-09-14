#!/usr/bin/env python3
"""
Minimal test server to check if OAuth routes work
"""
import sys
from pathlib import Path
import uvicorn
from fastapi import FastAPI

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def create_minimal_app() -> FastAPI:
    """Create a minimal FastAPI app for basic testing."""
    app = FastAPI(
        title="GameForge Minimal Test",
        description="Minimal test app"
    )
    
    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "minimal-test"}
    
    @app.get("/test")
    async def test():
        return {"message": "Test endpoint working"}
    
    return app


if __name__ == "__main__":
    app = create_minimal_app()
    print("🧪 Starting minimal test server...")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )