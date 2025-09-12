"""
GameForge Dataset Versioning API
===============================

REST API for managing dataset versions with DVC integration:
- Upload and version datasets
- Download specific dataset versions
- Data validation and quality checks
- Drift detection between versions
- Lineage tracking
"""

import os
import json
import logging
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import asyncpg
import redis.asyncio as redis
from prometheus_client import generate_latest

from dataset_versioning import (
    DatasetVersionManager, DatasetMetadata, ValidationStatus, 
    DriftStatus, DataLineage
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="GameForge Dataset Versioning API",
    description="REST API for dataset versioning and management with DVC",
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
dataset_manager: Optional[DatasetVersionManager] = None

# Pydantic models
class DatasetCreateRequest(BaseModel):
    """Request model for creating a new dataset version"""
    name: str = Field(..., description="Dataset name")
    version: str = Field(..., description="Dataset version")
    description: str = Field("", description="Dataset description")
    tags: Dict[str, str] = Field(default_factory=dict, description="Dataset tags")
    parent_datasets: List[Dict[str, str]] = Field(default_factory=list, description="Parent datasets")

class DatasetResponse(BaseModel):
    """Response model for dataset information"""
    name: str
    version: str
    description: str
    format: str
    size_bytes: int
    size_mb: float
    file_count: int
    created_at: datetime
    created_by: str
    tags: Dict[str, str]
    status: str
    validation_status: Optional[str] = None
    quality_score: Optional[float] = None

class ValidationResultResponse(BaseModel):
    """Response model for validation results"""
    status: str
    timestamp: str
    errors: List[str]
    warnings: List[str]
    info: List[str]
    summary: Dict[str, Any]

class DriftAnalysisResponse(BaseModel):
    """Response model for drift analysis"""
    overall_drift_score: float
    drift_status: str
    baseline_version: str
    current_version: str
    column_drifts: Dict[str, Any]
    summary: Dict[str, Any]
    analysis_timestamp: datetime

class LineageResponse(BaseModel):
    """Response model for dataset lineage"""
    dataset_name: str
    version: str
    parent_datasets: List[Dict[str, str]]
    transformation_info: Optional[Dict[str, Any]] = None
    created_at: datetime

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

async def get_dataset_manager() -> DatasetVersionManager:
    """Get dataset manager"""
    if dataset_manager is None:
        raise HTTPException(status_code=500, detail="Dataset manager not initialized")
    return dataset_manager

# API endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

@app.post("/datasets", response_model=Dict[str, str])
async def create_dataset(
    file: UploadFile = File(...),
    request: DatasetCreateRequest = Depends(),
    manager: DatasetVersionManager = Depends(get_dataset_manager)
):
    """Upload and create a new dataset version"""
    try:
        # Validate filename
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        # Create temporary directory for upload
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Convert parent datasets format
            parent_datasets_list = [(p["name"], p["version"]) for p in request.parent_datasets]
            
            # Create dataset version
            success = await manager.create_dataset_version(
                dataset_name=request.name,
                version=request.version,
                local_path=file_path,
                description=request.description,
                tags=request.tags,
                parent_datasets=parent_datasets_list if parent_datasets_list else []
            )
            
            if not success:
                raise HTTPException(status_code=400, detail="Failed to create dataset version")
            
        return {
            "message": "Dataset version created successfully",
            "dataset_name": request.name,
            "version": request.version,
            "upload_id": f"{request.name}-{request.version}"
        }
        
    except Exception as e:
        logger.error(f"Error creating dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/datasets", response_model=List[Dict[str, Any]])
async def list_datasets(
    manager: DatasetVersionManager = Depends(get_dataset_manager)
):
    """List all datasets with summary information"""
    try:
        datasets = await manager.list_datasets()
        return datasets
        
    except Exception as e:
        logger.error(f"Error listing datasets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/datasets/{dataset_name}/versions", response_model=List[DatasetResponse])
async def list_dataset_versions(
    dataset_name: str,
    db: asyncpg.Pool = Depends(get_db)
):
    """List all versions of a specific dataset"""
    try:
        async with db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT dataset_name, version, description, format, size_bytes,
                       file_count, created_at, created_by, tags, status,
                       validation_results
                FROM dataset_metadata
                WHERE dataset_name = $1
                ORDER BY created_at DESC
            """, dataset_name)
        
        if not rows:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        versions = []
        for row in rows:
            validation_results = json.loads(row['validation_results']) if row['validation_results'] else {}
            
            version_info = DatasetResponse(
                name=row['dataset_name'],
                version=row['version'],
                description=row['description'],
                format=row['format'],
                size_bytes=row['size_bytes'],
                size_mb=round(row['size_bytes'] / (1024**2), 2),
                file_count=row['file_count'],
                created_at=row['created_at'],
                created_by=row['created_by'],
                tags=json.loads(row['tags']) if row['tags'] else {},
                status=row['status'],
                validation_status=validation_results.get('status'),
                quality_score=validation_results.get('quality_score')
            )
            versions.append(version_info)
        
        return versions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing dataset versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/datasets/{dataset_name}/versions/{version}", response_model=DatasetResponse)
async def get_dataset_version(
    dataset_name: str,
    version: str,
    db: asyncpg.Pool = Depends(get_db)
):
    """Get detailed information about a specific dataset version"""
    try:
        if version == "latest":
            # Get latest version
            async with db.acquire() as conn:
                latest_row = await conn.fetchrow("""
                    SELECT version FROM dataset_metadata
                    WHERE dataset_name = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                """, dataset_name)
            
            if not latest_row:
                raise HTTPException(status_code=404, detail="Dataset not found")
            
            version = latest_row['version']
        
        async with db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT dataset_name, version, description, format, size_bytes,
                       file_count, created_at, created_by, tags, status,
                       validation_results
                FROM dataset_metadata
                WHERE dataset_name = $1 AND version = $2
            """, dataset_name, version)
        
        if not row:
            raise HTTPException(status_code=404, detail="Dataset version not found")
        
        validation_results = json.loads(row['validation_results']) if row['validation_results'] else {}
        
        return DatasetResponse(
            name=row['dataset_name'],
            version=row['version'],
            description=row['description'],
            format=row['format'],
            size_bytes=row['size_bytes'],
            size_mb=round(row['size_bytes'] / (1024**2), 2),
            file_count=row['file_count'],
            created_at=row['created_at'],
            created_by=row['created_by'],
            tags=json.loads(row['tags']) if row['tags'] else {},
            status=row['status'],
            validation_status=validation_results.get('status'),
            quality_score=validation_results.get('quality_score')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset version: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/datasets/{dataset_name}/versions/{version}/download")
async def download_dataset(
    dataset_name: str,
    version: str,
    manager: DatasetVersionManager = Depends(get_dataset_manager)
):
    """Download a specific dataset version"""
    try:
        # Create temporary download directory
        temp_dir = tempfile.mkdtemp()
        download_path = os.path.join(temp_dir, f"{dataset_name}-{version}")
        
        # Get dataset from DVC
        result_path = await manager.get_dataset(dataset_name, version, download_path)
        
        if not result_path:
            raise HTTPException(status_code=404, detail="Dataset version not found")
        
        # If it's a single file, return it directly
        if os.path.isfile(result_path):
            return FileResponse(
                path=result_path,
                filename=f"{dataset_name}-{version}.{os.path.splitext(result_path)[1][1:]}",
                media_type='application/octet-stream'
            )
        else:
            # For directories, create a zip archive
            import zipfile
            zip_path = f"{result_path}.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(result_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, result_path)
                        zipf.write(file_path, arcname)
            
            return FileResponse(
                path=zip_path,
                filename=f"{dataset_name}-{version}.zip",
                media_type='application/zip'
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/datasets/{dataset_name}/versions/{version}/validation", response_model=ValidationResultResponse)
async def get_validation_results(
    dataset_name: str,
    version: str,
    db: asyncpg.Pool = Depends(get_db)
):
    """Get validation results for a dataset version"""
    try:
        async with db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT validation_results FROM dataset_metadata
                WHERE dataset_name = $1 AND version = $2
            """, dataset_name, version)
        
        if not row:
            raise HTTPException(status_code=404, detail="Dataset version not found")
        
        if not row['validation_results']:
            raise HTTPException(status_code=404, detail="Validation results not available")
        
        validation_data = json.loads(row['validation_results'])
        
        return ValidationResultResponse(**validation_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/datasets/{dataset_name}/drift-analysis", response_model=DriftAnalysisResponse)
async def analyze_drift(
    dataset_name: str,
    baseline_version: str = Query(..., description="Baseline version for comparison"),
    current_version: str = Query(..., description="Current version to compare against baseline"),
    manager: DatasetVersionManager = Depends(get_dataset_manager)
):
    """Analyze data drift between two dataset versions"""
    try:
        drift_results = await manager.detect_data_drift(
            dataset_name, baseline_version, current_version
        )
        
        if not drift_results:
            raise HTTPException(status_code=400, detail="Failed to analyze drift")
        
        return DriftAnalysisResponse(
            overall_drift_score=drift_results['overall_drift_score'],
            drift_status=drift_results['drift_status'],
            baseline_version=baseline_version,
            current_version=current_version,
            column_drifts=drift_results['column_drifts'],
            summary=drift_results['summary'],
            analysis_timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing drift: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/datasets/{dataset_name}/versions/{version}/lineage", response_model=LineageResponse)
async def get_dataset_lineage(
    dataset_name: str,
    version: str,
    manager: DatasetVersionManager = Depends(get_dataset_manager)
):
    """Get lineage information for a dataset version"""
    try:
        lineage_data = await manager.get_dataset_lineage(dataset_name, version)
        
        if not lineage_data:
            raise HTTPException(status_code=404, detail="Lineage information not found")
        
        return LineageResponse(
            dataset_name=lineage_data['dataset_name'],
            version=lineage_data['version'],
            parent_datasets=[
                {"name": parent[0], "version": parent[1]} 
                for parent in lineage_data['parent_datasets']
            ],
            transformation_info={
                "script": lineage_data.get('transformation_script'),
                "params": lineage_data.get('transformation_params', {})
            },
            created_at=datetime.fromisoformat(lineage_data['created_at'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lineage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/datasets/{dataset_name}/drift-history")
async def get_drift_history(
    dataset_name: str,
    days: int = Query(30, description="Number of days to look back"),
    db: asyncpg.Pool = Depends(get_db)
):
    """Get drift analysis history for a dataset"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        async with db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT baseline_version, current_version, drift_score, drift_status,
                       analysis_results, created_at
                FROM dataset_drift_analysis
                WHERE dataset_name = $1 AND created_at >= $2
                ORDER BY created_at DESC
            """, dataset_name, start_date)
        
        drift_history = []
        for row in rows:
            drift_history.append({
                "baseline_version": row['baseline_version'],
                "current_version": row['current_version'],
                "drift_score": row['drift_score'],
                "drift_status": row['drift_status'],
                "created_at": row['created_at'],
                "analysis_summary": json.loads(row['analysis_results'])['summary']
            })
        
        return {"dataset_name": dataset_name, "drift_history": drift_history}
        
    except Exception as e:
        logger.error(f"Error getting drift history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/datasets/{dataset_name}/usage")
async def get_dataset_usage(
    dataset_name: str,
    days: int = Query(30, description="Number of days to look back"),
    db: asyncpg.Pool = Depends(get_db)
):
    """Get dataset usage statistics"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        async with db.acquire() as conn:
            # Get usage by version
            version_usage = await conn.fetch("""
                SELECT version, usage_type, COUNT(*) as usage_count,
                       MAX(used_at) as last_used
                FROM dataset_usage
                WHERE dataset_name = $1 AND used_at >= $2
                GROUP BY version, usage_type
                ORDER BY last_used DESC
            """, dataset_name, start_date)
            
            # Get total usage
            total_usage = await conn.fetchrow("""
                SELECT COUNT(*) as total_uses,
                       COUNT(DISTINCT version) as versions_used,
                       MAX(used_at) as last_used
                FROM dataset_usage
                WHERE dataset_name = $1 AND used_at >= $2
            """, dataset_name, start_date)
        
        usage_data = {
            "dataset_name": dataset_name,
            "period_days": days,
            "total_uses": total_usage['total_uses'],
            "versions_used": total_usage['versions_used'],
            "last_used": total_usage['last_used'],
            "usage_by_version": []
        }
        
        for row in version_usage:
            usage_data["usage_by_version"].append({
                "version": row['version'],
                "usage_type": row['usage_type'],
                "usage_count": row['usage_count'],
                "last_used": row['last_used']
            })
        
        return usage_data
        
    except Exception as e:
        logger.error(f"Error getting dataset usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/datasets/{dataset_name}/versions/{version}")
async def delete_dataset_version(
    dataset_name: str,
    version: str,
    db: asyncpg.Pool = Depends(get_db)
):
    """Mark a dataset version as deprecated/archived"""
    try:
        async with db.acquire() as conn:
            result = await conn.execute("""
                UPDATE dataset_metadata 
                SET status = 'deprecated', updated_at = CURRENT_TIMESTAMP
                WHERE dataset_name = $1 AND version = $2
            """, dataset_name, version)
        
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Dataset version not found")
        
        return {"message": f"Dataset version {dataset_name}:{version} marked as deprecated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dataset version: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    global db_pool, redis_client, dataset_manager
    
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
        redis_client = redis.from_url("redis://mlflow-redis:6379/3")
        
        # Initialize dataset manager
        dataset_manager = DatasetVersionManager(
            db_pool, redis_client, "gameforge-datasets"
        )
        
        logger.info("GameForge Dataset Versioning API started successfully")
        
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
    
    logger.info("GameForge Dataset Versioning API shutdown complete")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)