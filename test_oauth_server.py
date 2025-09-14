#!/usr/bin/env python3
"""
Simple test startup script for GitHub OAuth integration
"""
import sys
from pathlib import Path
import uvicorn
from fastapi import FastAPI

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gameforge.api.v1.auth import router as auth_router


def create_simple_app() -> FastAPI:
    """Create a minimal FastAPI app for testing OAuth."""
    app = FastAPI(
        title="GameForge OAuth Test",
        description="Simple OAuth testing app"
    )
    
    # Add OAuth routes
    app.include_router(auth_router, prefix="/api/v1")
    
    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "oauth-test"}
    
    return app


if __name__ == "__main__":
    app = create_simple_app()
    print("🔍 Starting simple OAuth test server...")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )