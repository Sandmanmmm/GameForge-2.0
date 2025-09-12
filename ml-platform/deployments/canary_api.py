"""
GameForge Canary Deployment API
===============================

REST API for managing canary deployments with:
- Start/stop canary deployments
- Monitor deployment status
- Manual promotion/rollback
- Real-time metrics and analytics
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import asyncpg
import redis.asyncio as redis
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from canary_deployment import (
    CanaryDeploymentManager, CanaryConfig, DeploymentStatus, 
    MetricType, ComparisonResult
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="GameForge Canary Deployment API",
    description="REST API for managing ML model canary deployments",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for dependency injection
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[redis.Redis] = None
deployment_manager: Optional[CanaryDeploymentManager] = None

# Pydantic models
class CanaryConfigRequest(BaseModel):
    """Request model for canary deployment configuration"""
    model_name: str = Field(..., description="Name of the model")
    current_version: str = Field(..., description="Current production version")
    canary_version: str = Field(..., description="New version to test")
    initial_traffic_percentage: int = Field(5, ge=1, le=50, description="Initial traffic percentage")
    max_traffic_percentage: int = Field(50, ge=10, le=100, description="Maximum traffic percentage")
    traffic_increment: int = Field(5, ge=1, le=20, description="Traffic increment step")
    monitoring_duration_minutes: int = Field(30, ge=5, le=120, description="Monitoring duration")
    success_threshold: float = Field(0.95, ge=0.5, le=1.0, description="Success threshold")
    error_threshold: float = Field(0.05, ge=0.001, le=0.5, description="Error threshold")
    latency_threshold_ms: float = Field(500.0, ge=10.0, le=5000.0, description="Latency threshold")
    statistical_significance: float = Field(0.05, ge=0.001, le=0.1, description="Statistical significance")
    min_requests_for_promotion: int = Field(1000, ge=100, le=10000, description="Minimum requests")
    auto_promote: bool = Field(False, description="Enable auto promotion")
    auto_rollback: bool = Field(True, description="Enable auto rollback")

class DeploymentStatusResponse(BaseModel):
    """Response model for deployment status"""
    model_name: str
    current_version: str
    canary_version: str
    status: str
    traffic_percentage: int
    created_at: datetime
    updated_at: datetime
    metrics_summary: Optional[Dict] = None

class MetricsResponse(BaseModel):
    """Response model for metrics"""
    model_name: str
    version: str
    metric_type: str
    values: List[float]
    timestamps: List[datetime]
    statistics: Dict[str, float]

class ComparisonResponse(BaseModel):
    """Response model for version comparison"""
    metric_type: str
    current_mean: float
    canary_mean: float
    p_value: float
    is_significant: bool
    canary_is_better: bool
    confidence_interval: List[float]

# Dependency functions
async def get_db() -> asyncpg.Pool:
    """Get database connection pool"""
    if db_pool is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return db_pool

async def get_redis() -> redis.Redis:
    """Get Redis client"""
    if redis_client is None:
        raise HTTPException(status_code=500, detail="Redis not initialized")
    return redis_client

async def get_deployment_manager() -> CanaryDeploymentManager:
    """Get deployment manager"""
    if deployment_manager is None:
        raise HTTPException(status_code=500, detail="Deployment manager not initialized")
    return deployment_manager

# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

@app.post("/deployments", response_model=Dict[str, str])
async def create_deployment(
    config_request: CanaryConfigRequest,
    background_tasks: BackgroundTasks,
    manager: CanaryDeploymentManager = Depends(get_deployment_manager)
):
    """Start a new canary deployment"""
    try:
        # Convert request to config
        config = CanaryConfig(**config_request.dict())
        
        # Check if deployment already exists
        if config.model_name in manager.active_deployments:
            raise HTTPException(
                status_code=409, 
                detail=f"Canary deployment already active for {config.model_name}"
            )
        
        # Start deployment
        success = await manager.start_canary_deployment(config)
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to start canary deployment"
            )
        
        # Start background monitoring
        background_tasks.add_task(monitor_deployment_background, config.model_name, manager)
        
        return {
            "message": "Canary deployment started successfully",
            "model_name": config.model_name,
            "deployment_id": f"{config.model_name}-{config.canary_version}"
        }
        
    except Exception as e:
        logger.error(f"Error creating deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deployments", response_model=List[DeploymentStatusResponse])
async def list_deployments(
    db: asyncpg.Pool = Depends(get_db),
    manager: CanaryDeploymentManager = Depends(get_deployment_manager)
):
    """List all deployments"""
    try:
        async with db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT model_name, model_version, deployment_type, environment,
                       traffic_percentage, status, created_at, updated_at,
                       deployment_config
                FROM model_deployments
                WHERE deployment_type = 'canary'
                ORDER BY created_at DESC
                LIMIT 50
            """)
        
        deployments = []
        for row in rows:
            config_data = json.loads(row['deployment_config']) if row['deployment_config'] else {}
            
            # Get current traffic percentage
            traffic_percentage = 0
            if row['model_name'] in manager.active_deployments:
                weights = await manager.traffic_splitter.get_traffic_split(row['model_name'])
                traffic_percentage = weights.get(row['model_version'], 0)
            
            deployments.append(DeploymentStatusResponse(
                model_name=row['model_name'],
                current_version=config_data.get('current_version', 'unknown'),
                canary_version=row['model_version'],
                status=row['status'],
                traffic_percentage=traffic_percentage,
                created_at=row['created_at'],
                updated_at=row['updated_at']
            ))
        
        return deployments
        
    except Exception as e:
        logger.error(f"Error listing deployments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deployments/{model_name}", response_model=DeploymentStatusResponse)
async def get_deployment(
    model_name: str,
    db: asyncpg.Pool = Depends(get_db),
    manager: CanaryDeploymentManager = Depends(get_deployment_manager)
):
    """Get deployment status for a specific model"""
    try:
        async with db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT model_name, model_version, deployment_type, environment,
                       traffic_percentage, status, created_at, updated_at,
                       deployment_config
                FROM model_deployments
                WHERE model_name = $1 AND deployment_type = 'canary'
                ORDER BY created_at DESC
                LIMIT 1
            """, model_name)
        
        if not row:
            raise HTTPException(status_code=404, detail="Deployment not found")
        
        config_data = json.loads(row['deployment_config']) if row['deployment_config'] else {}
        
        # Get current traffic percentage and metrics
        traffic_percentage = 0
        metrics_summary = None
        
        if model_name in manager.active_deployments:
            weights = await manager.traffic_splitter.get_traffic_split(model_name)
            traffic_percentage = weights.get(row['model_version'], 0)
            
            # Get recent metrics summary
            metrics_summary = await get_metrics_summary(model_name, row['model_version'], db)
        
        return DeploymentStatusResponse(
            model_name=row['model_name'],
            current_version=config_data.get('current_version', 'unknown'),
            canary_version=row['model_version'],
            status=row['status'],
            traffic_percentage=traffic_percentage,
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            metrics_summary=metrics_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deployments/{model_name}/promote")
async def promote_deployment(
    model_name: str,
    manager: CanaryDeploymentManager = Depends(get_deployment_manager)
):
    """Manually promote canary deployment"""
    try:
        if model_name not in manager.active_deployments:
            raise HTTPException(status_code=404, detail="Active deployment not found")
        
        config = manager.active_deployments[model_name]
        await manager._promote_canary(config)
        
        return {"message": f"Canary deployment promoted for {model_name}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error promoting deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/deployments/{model_name}/rollback")
async def rollback_deployment(
    model_name: str,
    manager: CanaryDeploymentManager = Depends(get_deployment_manager)
):
    """Manually rollback canary deployment"""
    try:
        if model_name not in manager.active_deployments:
            raise HTTPException(status_code=404, detail="Active deployment not found")
        
        config = manager.active_deployments[model_name]
        await manager._rollback_canary(config)
        
        return {"message": f"Canary deployment rolled back for {model_name}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rolling back deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/deployments/{model_name}")
async def stop_deployment(
    model_name: str,
    manager: CanaryDeploymentManager = Depends(get_deployment_manager)
):
    """Stop canary deployment"""
    try:
        if model_name not in manager.active_deployments:
            raise HTTPException(status_code=404, detail="Active deployment not found")
        
        config = manager.active_deployments[model_name]
        await manager._rollback_canary(config)
        
        return {"message": f"Canary deployment stopped for {model_name}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping deployment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deployments/{model_name}/metrics", response_model=List[MetricsResponse])
async def get_deployment_metrics(
    model_name: str,
    metric_type: Optional[str] = None,
    hours: int = 24,
    db: asyncpg.Pool = Depends(get_db),
    manager: CanaryDeploymentManager = Depends(get_deployment_manager)
):
    """Get deployment metrics"""
    try:
        if model_name not in manager.active_deployments:
            raise HTTPException(status_code=404, detail="Active deployment not found")
        
        config = manager.active_deployments[model_name]
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        metrics_types = [MetricType(metric_type)] if metric_type else [
            MetricType.ACCURACY, MetricType.LATENCY, MetricType.ERROR_RATE
        ]
        
        responses = []
        for mt in metrics_types:
            # Get metrics for both versions
            for version in [config.current_version, config.canary_version]:
                metrics_data = await manager.metrics_collector.get_metrics(
                    model_name, version, mt, start_time, end_time
                )
                
                if metrics_data:
                    values = [d.value for d in metrics_data]
                    timestamps = [d.timestamp for d in metrics_data]
                    
                    import numpy as np
                    statistics = {
                        "mean": float(np.mean(values)),
                        "median": float(np.median(values)),
                        "std": float(np.std(values)),
                        "min": float(np.min(values)),
                        "max": float(np.max(values)),
                        "count": len(values)
                    }
                    
                    responses.append(MetricsResponse(
                        model_name=model_name,
                        version=version,
                        metric_type=mt.value,
                        values=values,
                        timestamps=timestamps,
                        statistics=statistics
                    ))
        
        return responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/deployments/{model_name}/comparison", response_model=List[ComparisonResponse])
async def get_version_comparison(
    model_name: str,
    hours: int = 24,
    db: asyncpg.Pool = Depends(get_db),
    manager: CanaryDeploymentManager = Depends(get_deployment_manager)
):
    """Get statistical comparison between current and canary versions"""
    try:
        if model_name not in manager.active_deployments:
            raise HTTPException(status_code=404, detail="Active deployment not found")
        
        config = manager.active_deployments[model_name]
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        comparisons = []
        
        for metric_type in [MetricType.ACCURACY, MetricType.LATENCY, MetricType.ERROR_RATE]:
            # Get metrics for both versions
            current_data = await manager.metrics_collector.get_metrics(
                model_name, config.current_version, metric_type, start_time, end_time
            )
            canary_data = await manager.metrics_collector.get_metrics(
                model_name, config.canary_version, metric_type, start_time, end_time
            )
            
            current_values = [d.value for d in current_data]
            canary_values = [d.value for d in canary_data]
            
            if current_values and canary_values:
                result = manager.analyzer.compare_metrics(
                    current_values, canary_values, metric_type, config.statistical_significance
                )
                
                comparisons.append(ComparisonResponse(
                    metric_type=result.metric_type.value,
                    current_mean=result.current_mean,
                    canary_mean=result.canary_mean,
                    p_value=result.p_value,
                    is_significant=result.is_significant,
                    canary_is_better=result.canary_is_better,
                    confidence_interval=list(result.confidence_interval)
                ))
        
        return comparisons
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/{model_name}/traffic")
async def get_traffic_split(
    model_name: str,
    manager: CanaryDeploymentManager = Depends(get_deployment_manager)
):
    """Get current traffic split for a model"""
    try:
        weights = await manager.traffic_splitter.get_traffic_split(model_name)
        return {"model_name": model_name, "traffic_split": weights}
        
    except Exception as e:
        logger.error(f"Error getting traffic split: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/models/{model_name}/traffic")
async def set_traffic_split(
    model_name: str,
    traffic_split: Dict[str, int],
    manager: CanaryDeploymentManager = Depends(get_deployment_manager)
):
    """Manually set traffic split for a model"""
    try:
        # Validate traffic split
        total_weight = sum(traffic_split.values())
        if total_weight != 100:
            raise HTTPException(
                status_code=400,
                detail="Traffic split weights must sum to 100"
            )
        
        await manager.traffic_splitter.set_traffic_split(model_name, traffic_split)
        
        return {
            "message": f"Traffic split updated for {model_name}",
            "traffic_split": traffic_split
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting traffic split: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background tasks
async def monitor_deployment_background(model_name: str, manager: CanaryDeploymentManager):
    """Background task to monitor deployment"""
    try:
        while model_name in manager.active_deployments:
            await manager.monitor_deployment(model_name)
            await asyncio.sleep(60)  # Check every minute
            
    except Exception as e:
        logger.error(f"Error in background monitoring for {model_name}: {e}")

# Helper functions
async def get_metrics_summary(model_name: str, version: str, db: asyncpg.Pool) -> Dict:
    """Get metrics summary for a model version"""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        async with db.acquire() as conn:
            # Get latest metrics
            metrics = await conn.fetch("""
                SELECT metric_type, AVG(metric_value) as avg_value, COUNT(*) as count
                FROM model_metrics
                WHERE model_name = $1 AND model_version = $2 
                  AND timestamp BETWEEN $3 AND $4
                GROUP BY metric_type
            """, model_name, version, start_time, end_time)
        
        summary = {}
        for metric in metrics:
            summary[metric['metric_type']] = {
                "average": float(metric['avg_value']),
                "count": int(metric['count'])
            }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}")
        return {}

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    global db_pool, redis_client, deployment_manager
    
    try:
        # Initialize database connection
        db_pool = await asyncpg.create_pool(
            host="mlflow-postgres",
            port=5432,
            user="mlflow",
            password="mlflow_password",
            database="mlflow",
            min_size=5,
            max_size=20
        )
        
        # Initialize Redis connection
        redis_client = redis.from_url("redis://mlflow-redis:6379/2")
        
        # Initialize deployment manager
        deployment_manager = CanaryDeploymentManager(db_pool, redis_client)
        
        logger.info("GameForge Canary Deployment API started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    global db_pool, redis_client
    
    if db_pool:
        await db_pool.close()
    
    if redis_client:
        await redis_client.close()
    
    logger.info("GameForge Canary Deployment API shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)