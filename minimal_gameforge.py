"""
Minimal GameForge app for debugging lifespan issue
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from gameforge.core.config import get_settings
from gameforge.core.logging_config import setup_structured_logging, get_structured_logger

setup_structured_logging()
logger = get_structured_logger(__name__)


@asynccontextmanager
async def minimal_lifespan(app: FastAPI):
    """Minimal lifespan manager for debugging"""
    logger.info("🚀 Starting minimal GameForge application...")
    
    # Minimal setup
    settings = get_settings()
    logger.info(f"✅ Settings loaded: environment={settings.environment}")
    
    logger.info("🎉 Minimal GameForge application startup complete!")
    
    try:
        yield
        logger.info("📱 Application is running normally...")
    except Exception as e:
        logger.error(f"❌ Error during runtime: {e}")
        raise
    finally:
        logger.info("🛑 Shutting down minimal GameForge application...")
        logger.info("👋 Minimal GameForge application shutdown complete!")


def create_minimal_app() -> FastAPI:
    """Create minimal FastAPI app"""
    app = FastAPI(
        title="Minimal GameForge",
        lifespan=minimal_lifespan
    )
    
    @app.get("/")
    async def root():
        return {"message": "Minimal GameForge API"}
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    return app


app = create_minimal_app()