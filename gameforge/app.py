"""
GameForge Main FastAPI Application

This is the central FastAPI application that consolidates all GameForge services
into a single, well-structured application with proper health checks and
uvicorn/gunicorn configuration.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from gameforge.core.config import get_settings
from gameforge.core.health import HealthChecker
from gameforge.core.database import db_manager, setup_database_event_listeners
from gameforge.core.security_middleware import (
    setup_security_middleware, setup_exception_handlers
)
from gameforge.api.v1 import api_router


# Configure structured logging for ELK compatibility
from gameforge.core.logging_config import (
    setup_structured_logging, get_structured_logger
)

setup_structured_logging()
logger = get_structured_logger(__name__)

# Global state
redis_client: redis.Redis | None = None
health_checker: HealthChecker | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with graceful dependency handling"""
    global redis_client, health_checker
    
    logger.info("🚀 Starting GameForge application...")
    settings = get_settings()
    
    # Initialize SQLAlchemy database manager
    try:
        logger.info("📊 Connecting to database...")
        await db_manager.initialize()
        
        # Set up database event listeners for logging and performance monitoring
        setup_database_event_listeners(db_manager)
        
        logger.info("✅ Database connection configured")
    except Exception as e:
        logger.warning(f"⚠️  Database connection failed: {e}. Continuing without database.")
    
    # Initialize Redis connection with fallback
    try:
        logger.info("🔴 Connecting to Redis...")
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️  Redis connection failed: {e}. Continuing without Redis.")
        redis_client = None
    
    # Initialize health checker with available services
    health_checker = HealthChecker(db_manager, redis_client)
    
    # Store in app state for dependency injection
    app.state.db_manager = db_manager
    app.state.redis_client = redis_client
    app.state.health_checker = health_checker
    
    logger.info("🎉 GameForge application startup complete!")
    
    try:
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise
    finally:
        # Cleanup
        logger.info("🛑 Shutting down GameForge application...")
        
        if redis_client:
            await redis_client.close()
            logger.info("✅ Redis connection closed")
            
        # Close SQLAlchemy database connections
        try:
            await db_manager.close()
            logger.info("✅ Database connections closed")
        except Exception as e:
            logger.warning(f"⚠️  Error closing database: {e}")
            
        logger.info("👋 GameForge application shutdown complete!")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title="GameForge AI Platform",
        description=(
            "Unified API for GameForge AI-powered game development platform"
        ),
        version="1.0.0",
        docs_url="/docs" if settings.environment != "production" else None,
        redoc_url="/redoc" if settings.environment != "production" else None,
        openapi_url=(
            "/openapi.json" if settings.environment != "production" else None
        ),
        lifespan=lifespan
    )
    
    # Setup comprehensive security middleware
    setup_security_middleware(app, settings)
    
    # Setup global exception handlers
    setup_exception_handlers(app)
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Root health check endpoint
    @app.get("/health")
    async def health_check():
        """
        Simple health check endpoint for load balancers and monitoring.
        Returns 200 OK if the application is running.
        """
        health_check_condition = (
            not hasattr(app.state, 'health_checker') or
            app.state.health_checker is None
        )
        if health_check_condition:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "message": "Application is starting up",
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
        
        try:
            health_status = await app.state.health_checker.check_health()
            
            if health_status["status"] == "healthy":
                return JSONResponse(
                    status_code=200,
                    content=health_status
                )
            else:
                return JSONResponse(
                    status_code=503,
                    content=health_status
                )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "message": str(e),
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
    
    # Detailed health check endpoint
    @app.get("/health/detailed")
    async def detailed_health_check():
        """
        Detailed health check with dependency status information.
        """
        health_check_condition = (
            not hasattr(app.state, 'health_checker') or
            app.state.health_checker is None
        )
        if health_check_condition:
            raise HTTPException(
                status_code=503,
                detail="Health checker not initialized"
            )
        
        try:
            return await app.state.health_checker.detailed_health_check()
        except Exception as e:
            logger.error(f"Detailed health check failed: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Health check failed: {str(e)}"
            )
    
    # Readiness probe
    @app.get("/ready")
    async def readiness_check():
        """
        Kubernetes readiness probe endpoint.
        """
        health_check_condition = (
            not hasattr(app.state, 'health_checker') or
            app.state.health_checker is None
        )
        if health_check_condition:
            raise HTTPException(
                status_code=503,
                detail="Application not ready"
            )
        
        try:
            ready_status = await app.state.health_checker.check_readiness()
            if ready_status["ready"]:
                return ready_status
            else:
                raise HTTPException(status_code=503, detail=ready_status)
        except Exception as e:
            logger.error(f"Readiness check failed: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Readiness check failed: {str(e)}"
            )
    
    # Liveness probe
    @app.get("/live")
    async def liveness_check():
        """
        Kubernetes liveness probe endpoint.
        """
        return {
            "status": "alive",
            "timestamp": asyncio.get_event_loop().time()
        }
    
    # Application info endpoint
    @app.get("/info")
    async def app_info():
        """
        Application information endpoint.
        """
        return {
            "name": "GameForge AI Platform",
            "version": "1.0.0",
            "environment": settings.environment,
            "timestamp": asyncio.get_event_loop().time()
        }
    
    return app


# Create the application instance
app = create_app()