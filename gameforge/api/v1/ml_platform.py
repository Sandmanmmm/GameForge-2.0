"""
ML Platform API Integration

Exposes ML platform functionality to the GameForge frontend including
model registry, experiment tracking, monitoring dashboards, and AI job traceability.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
import logging
import sys
import os

logger = logging.getLogger(__name__)

# Add ML platform to path
ml_platform_path = os.path.join(os.path.dirname(__file__), '../../../ml-platform')
sys.path.insert(0, ml_platform_path)

# Import with graceful fallback
ML_PLATFORM_ENABLED = os.getenv("ML_PLATFORM_ENABLED", "false").lower() == "true"

ModelRegistry = None
ModelStage = None
Environment = None
MLMonitor = None
ExperimentTracker = None
MLArchivalManager = None

if ML_PLATFORM_ENABLED:
    try:
        from registry.registry_manager import (
            ModelRegistry as ProdModelRegistry,
            ModelStage as ProdModelStage,
            Environment as ProdEnvironment
        )
        from monitoring.drift_detector import MLMonitor as ProdMLMonitor
        from training.scripts.experiment_tracker import (
            ExperimentTracker as ProdExperimentTracker
        )
        from archival.archival_manager import (
            MLArchivalManager as ProdMLArchivalManager
        )
        
        ModelRegistry = ProdModelRegistry
        ModelStage = ProdModelStage
        Environment = ProdEnvironment
        MLMonitor = ProdMLMonitor
        ExperimentTracker = ProdExperimentTracker
        MLArchivalManager = ProdMLArchivalManager
        
        ML_PLATFORM_AVAILABLE = True
        logger.info("✅ ML Platform production modules loaded")
    except ImportError as e:
        logger.warning(f"Production ML Platform failed: {e}. Using mocks.")
        ML_PLATFORM_AVAILABLE = False
else:
    logger.info("ML Platform disabled. Using mock implementations.")
    ML_PLATFORM_AVAILABLE = False

if not ML_PLATFORM_AVAILABLE:
    # Create mock classes for graceful degradation
    class MockModelRegistry:
        def __init__(self, *args, **kwargs):
            pass

        def list_models(self, *args, **kwargs):
            return []

        def register_model(self, *args, **kwargs):
            return {"status": "mock", "message": "ML Platform not available"}
    
    class MockModelStage:
        DEVELOPMENT = "development"
        STAGING = "staging"
        PRODUCTION = "production"
    
    class MockEnvironment:
        DEV = "dev"
        STAGING = "staging"
        PROD = "prod"
    
    class MockMLMonitor:
        def __init__(self, *args, **kwargs):
            pass

        def get_metrics(self, *args, **kwargs):
            return {"status": "mock", "message": "ML Platform not available"}
    
    class MockExperimentTracker:
        def __init__(self, *args, **kwargs):
            pass

        def list_experiments(self, *args, **kwargs):
            return []
    
    class MockMLArchivalManager:
        def __init__(self, *args, **kwargs):
            pass

        def list_archived_models(self, *args, **kwargs):
            return []

    # Assign mocks
    ModelRegistry = MockModelRegistry
    ModelStage = MockModelStage
    Environment = MockEnvironment
    MLMonitor = MockMLMonitor
    ExperimentTracker = MockExperimentTracker
    MLArchivalManager = MockMLArchivalManager

router = APIRouter()

# Initialize ML platform components
try:
    if ML_PLATFORM_AVAILABLE:
        # Initialize production components with proper config
        model_registry = ModelRegistry()  # Will use default config
        ml_monitor = MLMonitor()
        experiment_tracker = ExperimentTracker()
        archival_manager = MLArchivalManager()
        logger.info("✅ ML Platform production components initialized")
    else:
        # Initialize mock components
        model_registry = ModelRegistry()
        ml_monitor = MLMonitor()
        experiment_tracker = ExperimentTracker()
        archival_manager = MLArchivalManager()
        logger.info("✅ ML Platform mock components initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize ML Platform: {e}")
    logger.error(f"Falling back to None components")
    model_registry = None
    ml_monitor = None
    experiment_tracker = None
    archival_manager = None


# ============================================================================
# Pydantic Models for Frontend Integration
# ============================================================================

class ModelRegistryEntry(BaseModel):
    """Model registry entry for frontend display"""
    model_id: str
    name: str
    version: str
    framework: str
    stage: str
    environment: Optional[str]
    description: str
    author: str
    created_at: datetime
    updated_at: datetime
    performance_metrics: Dict[str, float]
    tags: List[str]


class ExperimentInfo(BaseModel):
    """Experiment information for frontend"""
    experiment_id: str
    name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    parameters: Dict[str, Any]
    metrics: Dict[str, float]
    artifacts: List[str]
    model_id: Optional[str]


class MonitoringDashboard(BaseModel):
    """Monitoring dashboard data for frontend"""
    model_id: str
    status: str
    accuracy: Optional[float]
    latency_p95: Optional[float]
    error_rate: Optional[float]
    drift_alerts: List[Dict[str, Any]]
    performance_trend: str
    last_updated: datetime


class PromotionRequest(BaseModel):
    """Model promotion request"""
    model_id: str
    from_stage: str
    to_stage: str
    justification: str


class PromotionApproval(BaseModel):
    """Model promotion approval"""
    request_id: str
    approved: bool
    notes: Optional[str]


class AIJobTraceability(BaseModel):
    """AI job traceability information"""
    job_id: str
    model_used: Optional[str]
    model_version: Optional[str]
    experiment_id: Optional[str]
    training_job_id: Optional[str]
    generation_params: Dict[str, Any]
    quality_metrics: Dict[str, float]
    created_at: datetime


class MetricsResponse(BaseModel):
    """Prometheus metrics response"""
    metrics: Dict[str, float]
    labels: Dict[str, str]
    timestamp: datetime


# ============================================================================
# Model Registry Endpoints
# ============================================================================

@router.get("/models", response_model=List[ModelRegistryEntry])
async def list_models(
    stage: Optional[str] = Query(None),
    environment: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    limit: int = Query(50, le=200)
):
    """List models in the registry with optional filtering"""
    
    if not model_registry:
        raise HTTPException(status_code=503, detail="Model registry not available")
    
    try:
        # Convert string parameters to enums
        stage_enum = ModelStage(stage) if stage else None
        env_enum = Environment(environment) if environment else None
        
        models = model_registry.list_models(
            stage=stage_enum,
            environment=env_enum,
            author=author
        )
        
        # Convert to frontend format
        result = []
        for model in models[:limit]:
            result.append(ModelRegistryEntry(
                model_id=model.model_id,
                name=model.name,
                version=model.version,
                framework=model.framework,
                stage=model.stage.value,
                environment=model.environment.value if model.environment else None,
                description=model.description,
                author=model.author,
                created_at=model.created_at,
                updated_at=model.updated_at,
                performance_metrics=model.performance_metrics,
                tags=model.tags
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/{model_id}", response_model=ModelRegistryEntry)
async def get_model(model_id: str):
    """Get specific model details"""
    
    if not model_registry:
        raise HTTPException(status_code=503, detail="Model registry not available")
    
    try:
        model = model_registry.get_model(model_id)
        
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        return ModelRegistryEntry(
            model_id=model.model_id,
            name=model.name,
            version=model.version,
            framework=model.framework,
            stage=model.stage.value,
            environment=model.environment.value if model.environment else None,
            description=model.description,
            author=model.author,
            created_at=model.created_at,
            updated_at=model.updated_at,
            performance_metrics=model.performance_metrics,
            tags=model.tags
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/{model_id}/promote")
async def request_model_promotion(
    model_id: str,
    promotion: PromotionRequest,
    current_user: str = "api_user"  # TODO: Get from auth
):
    """Request model promotion to next stage"""
    
    if not model_registry:
        raise HTTPException(status_code=503, detail="Model registry not available")
    
    try:
        to_stage = ModelStage(promotion.to_stage)
        
        request_id = model_registry.request_promotion(
            model_id=model_id,
            to_stage=to_stage,
            requestor=current_user,
            justification=promotion.justification
        )
        
        return {
            "request_id": request_id,
            "status": "pending",
            "message": f"Promotion request created for {model_id}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to request promotion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/promotions/{request_id}/approve")
async def approve_model_promotion(
    request_id: str,
    approval: PromotionApproval,
    current_user: str = "api_user"  # TODO: Get from auth
):
    """Approve or reject model promotion"""
    
    if not model_registry:
        raise HTTPException(status_code=503, detail="Model registry not available")
    
    try:
        success = model_registry.approve_promotion(
            request_id=request_id,
            approver=current_user,
            approved=approval.approved
        )
        
        return {
            "success": success,
            "status": "approved" if approval.approved else "rejected",
            "message": f"Promotion {'approved' if approval.approved else 'rejected'}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to approve promotion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Experiment Tracking Endpoints  
# ============================================================================

@router.get("/experiments", response_model=List[ExperimentInfo])
async def list_experiments(
    status: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    limit: int = Query(50, le=200)
):
    """List experiments with optional filtering"""
    
    if not experiment_tracker:
        raise HTTPException(status_code=503, detail="Experiment tracker not available")
    
    try:
        experiments = experiment_tracker.list_experiments(
            limit=limit,
            status_filter=status,
            author_filter=author
        )
        
        result = []
        for exp in experiments:
            result.append(ExperimentInfo(
                experiment_id=exp.get("experiment_id", ""),
                name=exp.get("name", ""),
                status=exp.get("status", "unknown"),
                start_time=exp.get("start_time", datetime.utcnow()),
                end_time=exp.get("end_time"),
                parameters=exp.get("parameters", {}),
                metrics=exp.get("metrics", {}),
                artifacts=exp.get("artifacts", []),
                model_id=exp.get("model_id")
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to list experiments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments/{experiment_id}", response_model=ExperimentInfo)
async def get_experiment(experiment_id: str):
    """Get specific experiment details"""
    
    if not experiment_tracker:
        raise HTTPException(status_code=503, detail="Experiment tracker not available")
    
    try:
        exp = experiment_tracker.get_experiment(experiment_id)
        
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
        
        return ExperimentInfo(
            experiment_id=exp.get("experiment_id", ""),
            name=exp.get("name", ""),
            status=exp.get("status", "unknown"),
            start_time=exp.get("start_time", datetime.utcnow()),
            end_time=exp.get("end_time"),
            parameters=exp.get("parameters", {}),
            metrics=exp.get("metrics", {}),
            artifacts=exp.get("artifacts", []),
            model_id=exp.get("model_id")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get experiment {experiment_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Monitoring Dashboard Endpoints
# ============================================================================

@router.get("/monitoring/{model_id}", response_model=MonitoringDashboard)
async def get_model_monitoring(model_id: str):
    """Get monitoring dashboard data for a model"""
    
    if not ml_monitor:
        raise HTTPException(status_code=503, detail="ML monitor not available")
    
    try:
        # Get monitoring report
        report = ml_monitor.generate_monitoring_report(model_id, days=7)
        
        # Extract key metrics
        performance = report.get("performance_trends", {})
        drift_summary = report.get("drift_summary", {})
        alerts_summary = report.get("alerts_summary", {})
        
        return MonitoringDashboard(
            model_id=model_id,
            status="healthy" if alerts_summary.get("total_alerts", 0) == 0 else "warning",
            accuracy=performance.get("avg_accuracy"),
            latency_p95=performance.get("avg_latency_p95"),
            error_rate=0.0,  # Calculate from alerts
            drift_alerts=[
                {
                    "feature": feature["name"],
                    "drift_count": feature["drift_count"],
                    "max_score": feature["max_score"]
                }
                for feature in drift_summary.get("features", [])
            ],
            performance_trend=performance.get("accuracy_trend", "stable"),
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get monitoring data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/{model_id}/drift")
async def get_drift_detection(model_id: str, days: int = Query(7, ge=1, le=30)):
    """Get drift detection results for a model"""
    
    if not ml_monitor:
        raise HTTPException(status_code=503, detail="ML monitor not available")
    
    try:
        # Get drift detection history from database
        # This is a simplified version - in practice you'd query the monitoring database
        return {
            "model_id": model_id,
            "period_days": days,
            "drift_events": [],  # TODO: Implement actual drift data retrieval
            "overall_drift_score": 0.0,
            "recommendations": ["No drift detected"]
        }
        
    except Exception as e:
        logger.error(f"Failed to get drift data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Prometheus Metrics Endpoints
# ============================================================================

@router.get("/metrics", response_model=MetricsResponse)
async def get_prometheus_metrics():
    """Get Prometheus metrics for monitoring dashboards"""
    
    try:
        # Collect metrics from various sources
        metrics = {
            "gameforge_models_total": len(model_registry.list_models()) if model_registry else 0,
            "gameforge_models_production": len([
                m for m in (model_registry.list_models() if model_registry else [])
                if m.stage == ModelStage.PRODUCTION
            ]),
            "gameforge_experiments_total": 0,  # TODO: Get from experiment tracker
            "gameforge_monitoring_alerts_total": 0,  # TODO: Get from monitoring
            "gameforge_archival_items_total": 0,  # TODO: Get from archival manager
        }
        
        return MetricsResponse(
            metrics=metrics,
            labels={"service": "gameforge", "component": "ml_platform"},
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/prometheus")
async def get_prometheus_format():
    """Get metrics in Prometheus format"""
    
    try:
        metrics_data = await get_prometheus_metrics()
        
        # Convert to Prometheus format
        prometheus_output = []
        for metric_name, value in metrics_data.metrics.items():
            labels_str = ",".join([f'{k}="{v}"' for k, v in metrics_data.labels.items()])
            prometheus_output.append(f"{metric_name}{{{labels_str}}} {value}")
        
        return "\n".join(prometheus_output)
        
    except Exception as e:
        logger.error(f"Failed to generate Prometheus metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AI Job Traceability Endpoints
# ============================================================================

@router.post("/ai-jobs/{job_id}/trace")
async def create_ai_job_trace(
    job_id: str,
    model_info: Dict[str, Any],
    generation_params: Dict[str, Any]
):
    """Create traceability record for AI generation job"""
    
    try:
        # Extract model information
        model_name = model_info.get("model", "unknown")
        model_version = model_info.get("version", "unknown")
        
        # Create experiment entry for traceability
        if experiment_tracker:
            experiment_id = experiment_tracker.start_experiment(
                name=f"ai_generation_{job_id}",
                parameters={
                    "job_id": job_id,
                    "model": model_name,
                    "model_version": model_version,
                    **generation_params
                },
                tags=["ai_generation", "production"]
            )
        else:
            experiment_id = None
        
        # Store traceability information
        trace_info = AIJobTraceability(
            job_id=job_id,
            model_used=model_name,
            model_version=model_version,
            experiment_id=experiment_id,
            training_job_id=None,  # Could be linked if model has training history
            generation_params=generation_params,
            quality_metrics={},  # Will be updated when job completes
            created_at=datetime.utcnow()
        )
        
        # TODO: Store in database for persistent traceability
        
        return {
            "trace_id": f"trace_{job_id}",
            "experiment_id": experiment_id,
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Failed to create AI job trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-jobs/{job_id}/trace", response_model=AIJobTraceability)
async def get_ai_job_trace(job_id: str):
    """Get traceability information for AI job"""
    
    try:
        # TODO: Retrieve from database
        # For now, return mock data
        return AIJobTraceability(
            job_id=job_id,
            model_used="stable-diffusion-xl",
            model_version="1.0.0",
            experiment_id=f"exp_{job_id}",
            training_job_id=None,
            generation_params={"prompt": "sample", "steps": 20},
            quality_metrics={"aesthetic_score": 0.8},
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get AI job trace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# System Status Endpoints
# ============================================================================

@router.get("/status")
async def get_ml_platform_status():
    """Get overall ML platform status"""
    
    status = {
        "ml_platform": "healthy",
        "components": {
            "model_registry": "healthy" if model_registry else "unavailable",
            "monitoring": "healthy" if ml_monitor else "unavailable", 
            "experiment_tracker": "healthy" if experiment_tracker else "unavailable",
            "archival_manager": "healthy" if archival_manager else "unavailable"
        },
        "statistics": {},
        "timestamp": datetime.utcnow().isoformat()
    }
    
    try:
        # Get registry stats
        if model_registry:
            status["statistics"]["registry"] = model_registry.get_registry_stats()
        
        # Get archival stats  
        if archival_manager:
            status["statistics"]["archival"] = archival_manager.get_archival_statistics()
            
    except Exception as e:
        logger.warning(f"Failed to get some statistics: {e}")
    
    return status


# ============================================================================
# WebSocket for Real-time Updates
# ============================================================================

@router.websocket("/ws/monitoring/{model_id}")
async def monitoring_websocket(websocket, model_id: str):
    """WebSocket endpoint for real-time monitoring updates"""
    
    await websocket.accept()
    
    try:
        while True:
            # Send monitoring updates every 30 seconds
            if ml_monitor:
                dashboard_data = await get_model_monitoring(model_id)
                await websocket.send_json(dashboard_data.dict())
            
            await asyncio.sleep(30)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()