#!/usr/bin/env python3
"""
OAuth test server with manual route import
"""
import sys
from pathlib import Path
import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException
import secrets

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def create_oauth_app() -> FastAPI:
    """Create FastAPI app with manual OAuth routes."""
    app = FastAPI(
        title="GameForge OAuth Test Manual",
        description="OAuth test with manual routes"
    )
    
    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "oauth-manual-test"}
    
    @app.get("/api/v1/auth/github")
    async def github_oauth_login():
        """Initiate GitHub OAuth flow."""
        try:
            # For testing, return mock response (no credentials configured)
            state = secrets.token_urlsafe(32)
            
            # In a real implementation, this would redirect to GitHub
            return {
                "message": "GitHub OAuth would redirect here",
                "state": state,
                "note": "Test implementation - credentials not configured"
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"OAuth error: {str(e)}"
            )
    
    @app.get("/api/v1/auth/github/callback")
    async def github_oauth_callback(
        code: Optional[str] = None, 
        state: Optional[str] = None
    ):
        """Handle GitHub OAuth callback."""
        if not code:
            raise HTTPException(
                status_code=400, 
                detail="Missing authorization code"
            )
        
        return {
            "message": "GitHub OAuth callback received",
            "code": code,
            "state": state,
            "note": "Would exchange code for token in real implementation"
        }
    
    return app


if __name__ == "__main__":
    app = create_oauth_app()
    print("🔐 Starting manual OAuth test server...")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,
        log_level="info"
    )