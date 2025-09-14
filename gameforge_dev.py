"""
GameForge Development FastAPI Application

Simplified version for frontend testing without complex dependencies like Vault, PostgreSQL, Redis.
"""
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Simple logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env.minimal
from dotenv import load_dotenv
load_dotenv(".env.minimal")

def create_minimal_app() -> FastAPI:
    """Create a minimal FastAPI application for frontend testing"""
    
    app = FastAPI(
        title="GameForge AI Platform (Development)",
        description="Simplified API for frontend testing",
        version="1.0.0-dev",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Configure CORS for frontend development
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check endpoints
    @app.get("/health")
    async def health_check():
        """Simple health check for development"""
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "message": "Development server running",
                "environment": "development"
            }
        )
    
    @app.get("/api/v1/health")
    async def api_health_check():
        """API health check"""
        return {
            "status": "healthy",
            "version": "1.0.0-dev",
            "environment": "development"
        }
    
    # Basic info endpoint
    @app.get("/info")
    async def app_info():
        """Application information"""
        return {
            "name": "GameForge AI Platform",
            "version": "1.0.0-dev",
            "environment": "development",
            "docs": "/docs"
        }
    
    # Mock API endpoints for frontend testing
    @app.get("/api/v1/projects")
    async def get_projects():
        """Mock projects endpoint"""
        return {
            "projects": [
                {
                    "id": "1",
                    "name": "Sample Game Project",
                    "description": "A sample game project for testing",
                    "status": "active",
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": "2", 
                    "name": "RPG Adventure",
                    "description": "Fantasy RPG with AI-generated assets",
                    "status": "in_development",
                    "created_at": "2024-01-02T00:00:00Z"
                }
            ]
        }
    
    @app.get("/api/v1/assets")
    async def get_assets():
        """Mock assets endpoint"""
        return {
            "assets": [
                {
                    "id": "1",
                    "name": "Hero Character",
                    "type": "character",
                    "status": "completed",
                    "project_id": "1"
                },
                {
                    "id": "2",
                    "name": "Forest Background",
                    "type": "environment",
                    "status": "in_progress", 
                    "project_id": "1"
                }
            ]
        }
    
    @app.get("/api/v1/ai/generate")
    async def ai_generate():
        """Mock AI generation endpoint"""
        return {
            "status": "success",
            "message": "AI generation service available",
            "models": ["stable-diffusion", "gpt-4", "music-gen"]
        }
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information"""
        return {
            "message": "GameForge AI Platform API (Development)",
            "version": "1.0.0-dev",
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1"
        }
    
    logger.info("🚀 GameForge development server configured")
    logger.info(f"📡 CORS origins: {cors_origins}")
    
    return app

# Create the app instance
app = create_minimal_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "gameforge_dev:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )