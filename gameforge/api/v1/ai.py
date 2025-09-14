"""
AI generation endpoints with production-ready job management.
"""
import uuid
import asyncio
import json
import time
import sys
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Literal
from fastapi import (
    APIRouter, HTTPException, BackgroundTasks,
    File, UploadFile, Depends, Request, Query
)
from pydantic import BaseModel, Field, validator, root_validator
import logging

from .project_storage import project_storage

# Import metrics system, structured logging, and auth validation
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
from src.metrics.gameforge_metrics import metrics
from gameforge.core.logging_config import (
    get_structured_logger, log_ai_job_event
)
from gameforge.core.security import (
    SecurityValidator, rate_limit,
    validate_input_security, enhanced_prompt_validator,
    secure_model_path_validator
)
from gameforge.core.auth_validation import require_ai_access

logger = get_structured_logger(__name__)
standard_logger = logging.getLogger(__name__)

router = APIRouter()

# Global job storage (in production, use Redis or database)
_job_storage: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# Pydantic Models with Production Validation
# ============================================================================

class JobMetadata(BaseModel):
    """Standard job metadata structure."""
    id: str = Field(..., description="Unique job identifier")
    user_id: str = Field(..., description="User ID who created the job")
    status: Literal[
        "pending", "processing", "completed", "failed", "cancelled"
    ] = Field(..., description="Current job status")
    progress: float = Field(
        ge=0.0, le=100.0, description="Progress percentage (0-100)"
    )
    asset_url: Optional[str] = Field(
        None, description="URL to generated asset"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AIGenerateRequest(BaseModel):
    """Request model for AI asset generation with payload size validation."""
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Text prompt for asset generation"
    )
    style: str = Field(
        default="fantasy",
        max_length=100,
        description="Art style for generation"
    )
    category: str = Field(
        default="weapons",
        max_length=50,
        description="Asset category"
    )
    width: int = Field(
        default=512,
        ge=256,
        le=2048,
        description="Image width in pixels"
    )
    height: int = Field(
        default=512,
        ge=256,
        le=2048,
        description="Image height in pixels"
    )
    quality: Literal["draft", "standard", "high", "ultra"] = Field(
        default="standard",
        description="Generation quality level"
    )
    count: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of variations to generate"
    )
    negative_prompt: Optional[str] = Field(
        None,
        max_length=1000,
        description="What to avoid in generation"
    )
    seed: Optional[int] = Field(
        None,
        ge=0,
        description="Random seed for reproducible generation"
    )
    model: Optional[str] = Field(
        default="stable-diffusion-xl",
        max_length=100,
        description="AI model to use"
    )

    @validator('prompt')
    def validate_prompt_content(cls, v):
        """Enhanced prompt validation with comprehensive security checks."""
        return enhanced_prompt_validator(cls, v)

    @validator('model')
    def validate_model_path(cls, v):
        """Validate model path is secure."""
        return secure_model_path_validator(cls, v)

    @root_validator(skip_on_failure=True)
    def validate_dimensions(cls, values):
        """Validate image dimensions are reasonable."""
        width = values.get('width', 512)
        height = values.get('height', 512)
        
        # Check total pixel count (max 4MP for performance)
        total_pixels = width * height
        if total_pixels > 4_000_000:
            raise ValueError("Image dimensions too large (max 4MP)")
        
        return values

    class Config:
        schema_extra = {
            "example": {
                "prompt": "A mystical elven sword with glowing runes",
                "style": "fantasy",
                "category": "weapons",
                "width": 512,
                "height": 512,
                "quality": "high",
                "count": 1,
                "model": "stable-diffusion-xl"
            }
        }


class SuperResRequest(BaseModel):
    """Request model for AI super-resolution with file size validation."""
    scale_factor: int = Field(
        default=2,
        ge=2,
        le=8,
        description="Upscaling factor (2x, 4x, 8x)"
    )
    enhance_details: bool = Field(
        default=True,
        description="Enable detail enhancement"
    )
    preserve_style: bool = Field(
        default=True,
        description="Preserve original art style"
    )
    noise_reduction: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Noise reduction strength"
    )
    model: Optional[str] = Field(
        default="real-esrgan",
        max_length=100,
        description="Super-resolution model"
    )

    class Config:
        schema_extra = {
            "example": {
                "scale_factor": 4,
                "enhance_details": True,
                "preserve_style": True,
                "noise_reduction": 0.3,
                "model": "real-esrgan"
            }
        }


class AIGenerateResponse(BaseModel):
    """Response model for AI generation requests."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")
    estimated_duration: Optional[int] = Field(
        None, description="Estimated completion time in seconds"
    )
    tracking_url: str = Field(..., description="URL to track job progress")

    class Config:
        schema_extra = {
            "example": {
                "job_id": "job_123e4567-e89b-12d3-a456-426614174000",
                "status": "pending",
                "message": "Asset generation job queued successfully",
                "estimated_duration": 45,
                "tracking_url": "/api/ai/job/job_123e4567-e89b-12d3-a456"
            }
        }


class JobStatusResponse(BaseModel):
    """Response model for job status queries."""
    success: bool = Field(..., description="Request success status")
    data: JobMetadata = Field(..., description="Job metadata")

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "id": "job_123e4567-e89b-12d3-a456-426614174000",
                    "status": "completed",
                    "progress": 100.0,
                    "asset_url": "https://cdn.gameforge.ai/assets/sword.png",
                    "created_at": "2025-09-13T10:30:00Z",
                    "updated_at": "2025-09-13T10:31:23Z",
                    "metadata": {
                        "prompt": "A mystical elven sword with glowing runes",
                        "style": "fantasy",
                        "model": "stable-diffusion-xl"
                    }
                }
            }
        }


# ============================================================================
# Utility Functions
# ============================================================================

def validate_file_size(file: UploadFile, max_size_mb: int = 50) -> None:
    """Validate uploaded file size."""
    if hasattr(file.file, 'seek'):
        file.file.seek(0, 2)  # Seek to end
        size = file.file.tell()
        file.file.seek(0)  # Reset to beginning
        
        max_size_bytes = max_size_mb * 1024 * 1024
        if size > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {max_size_mb}MB"
            )


def estimate_generation_time(request: AIGenerateRequest) -> int:
    """Estimate generation time based on request parameters."""
    base_time = 30  # Base 30 seconds
    
    # Adjust for quality
    quality_multipliers = {
        "draft": 0.5,
        "standard": 1.0,
        "high": 1.5,
        "ultra": 2.0
    }
    base_time *= quality_multipliers.get(request.quality, 1.0)
    
    # Adjust for dimensions
    pixel_count = request.width * request.height
    if pixel_count > 512 * 512:
        base_time *= 1.5
    
    # Adjust for count
    base_time *= request.count
    
    return int(base_time)


async def process_ai_generation(
    job_id: str, request: AIGenerateRequest
) -> None:
    """Background task to process AI generation."""
    start_time = time.time()
    model_name = request.model
    
    try:
        # Update job status to processing
        _job_storage[job_id]["status"] = "processing"
        _job_storage[job_id]["progress"] = 10.0
        _job_storage[job_id]["updated_at"] = datetime.utcnow()
        
        # Log job processing start
        user_id = _job_storage[job_id].get("user_id")
        log_ai_job_event(
            event_type="processing_started",
            job_id=job_id,
            user_id=user_id or "unknown",
            model=model_name or "default"
        )
        
        # Create ML platform experiment tracking for this generation
        experiment_id = None
        try:
            from ml_platform.training.scripts.experiment_tracker import ExperimentTracker
            tracker = ExperimentTracker()
            experiment_id = tracker.start_experiment(
                name=f"ai_generation_{job_id}",
                parameters={
                    "model": model_name,
                    "prompt": request.prompt[:200],  # Truncate for storage
                    "style": request.style,
                    "category": request.category,
                    "width": request.width,
                    "height": request.height,
                    "quality": request.quality,
                    "count": request.count,
                    "user_id": user_id
                },
                tags=["ai_generation", "production", request.category]
            )
            _job_storage[job_id]["experiment_id"] = experiment_id
            logger.info(f"Created experiment {experiment_id} for job {job_id}")
        except Exception as e:
            logger.warning(f"Failed to create experiment tracking: {e}")
        
        # Simulate processing stages
        stages = [
            ("Initializing AI model", 20.0),
            ("Processing prompt", 40.0),
            ("Generating image", 70.0),
            ("Post-processing", 90.0),
            ("Finalizing", 100.0)
        ]
        
        for stage_name, progress in stages:
            await asyncio.sleep(2)  # Simulate processing time
            _job_storage[job_id]["progress"] = progress
            _job_storage[job_id]["updated_at"] = datetime.utcnow()
            _job_storage[job_id]["metadata"]["current_stage"] = stage_name
            
            # Log metrics to experiment tracker
            if experiment_id:
                try:
                    tracker.log_metrics({
                        "progress": progress,
                        "stage": stage_name,
                        "processing_time": time.time() - start_time
                    })
                except Exception as e:
                    logger.warning(f"Failed to log metrics: {e}")
            
            log_ai_job_event(
                event_type="stage_completed",
                job_id=job_id,
                user_id=user_id or "unknown",
                model=model_name or "default",
                stage=stage_name,
                progress=progress
            )
        
        # Mark as completed with mock asset URL
        asset_url = f"https://cdn.gameforge.ai/assets/{job_id}.png"
        _job_storage[job_id]["status"] = "completed"
        _job_storage[job_id]["asset_url"] = asset_url
        _job_storage[job_id]["updated_at"] = datetime.utcnow()
        
        # Record successful completion metrics
        duration = time.time() - start_time
        metrics.inference_duration.labels(model=model_name).observe(duration)
        metrics.inference_requests_total.labels(
            model=model_name, status='success'
        ).inc()
        
        # Log final metrics and artifacts to experiment tracker
        if experiment_id:
            try:
                tracker.log_metrics({
                    "total_duration": duration,
                    "success": True,
                    "asset_url": asset_url,
                    "final_progress": 100.0
                })
                tracker.log_artifact(asset_url, "generated_assets/")
                tracker.end_experiment()
                logger.info(f"Completed experiment {experiment_id}")
            except Exception as e:
                logger.warning(f"Failed to complete experiment: {e}")
        
        # Create ML platform traceability record
        try:
            import requests
            requests.post(
                f"http://localhost:8080/api/v1/ml-platform/ai-jobs/{job_id}/trace",
                json={
                    "model_info": {
                        "model": model_name,
                        "version": "1.0.0",
                        "framework": "diffusion"
                    },
                    "generation_params": {
                        "prompt": request.prompt,
                        "style": request.style,
                        "dimensions": f"{request.width}x{request.height}",
                        "quality": request.quality,
                        "duration": duration
                    }
                },
                timeout=5
            )
        except Exception as e:
            logger.warning(f"Failed to create traceability record: {e}")
        
        # Save asset to project storage
        try:
            if user_id:
                asset_record = project_storage.save_asset_to_project(
                    user_id=user_id,
                    asset_url=asset_url,
                    job_data=_job_storage[job_id]
                )
                
                log_ai_job_event(
                    event_type="asset_saved",
                    job_id=job_id,
                    user_id=user_id or "unknown",
                    model=model_name or "default",
                    asset_id=asset_record.id,
                    asset_url=asset_url,
                    duration=duration
                )
        except Exception as e:
            log_ai_job_event(
                event_type="asset_save_failed",
                job_id=job_id,
                user_id=user_id or "unknown",
                model=model_name or "default",
                error=str(e)
            )
        
        log_ai_job_event(
            event_type="job_completed",
            job_id=job_id,
            user_id=user_id or "unknown",
            model=model_name or "default",
            duration=duration
        )
        
    except Exception as e:
        # Record failure metrics
        duration = time.time() - start_time
        metrics.inference_requests_total.labels(
            model=model_name, status='error'
        ).inc()
        metrics.inference_duration.labels(model=model_name).observe(duration)
        
        log_ai_job_event(
            event_type="job_failed",
            job_id=job_id,
            user_id=_job_storage[job_id].get("user_id") or "unknown",
            model=model_name or "default",
            error=str(e),
            duration=duration
        )
        
        _job_storage[job_id]["status"] = "failed"
        _job_storage[job_id]["error_message"] = str(e)
        _job_storage[job_id]["updated_at"] = datetime.utcnow()


async def process_super_resolution(
    job_id: str, request: SuperResRequest, file_path: str
) -> None:
    """Background task to process super-resolution."""
    try:
        # Update job status to processing
        _job_storage[job_id]["status"] = "processing"
        _job_storage[job_id]["progress"] = 15.0
        _job_storage[job_id]["updated_at"] = datetime.utcnow()
        
        # Simulate super-resolution stages
        stages = [
            ("Loading image", 25.0),
            ("Analyzing image quality", 40.0),
            ("Upscaling with AI", 70.0),
            ("Enhancing details", 85.0),
            ("Saving result", 100.0)
        ]
        
        for stage_name, progress in stages:
            await asyncio.sleep(3)  # Super-res takes longer
            _job_storage[job_id]["progress"] = progress
            _job_storage[job_id]["updated_at"] = datetime.utcnow()
            _job_storage[job_id]["metadata"]["current_stage"] = stage_name
            logger.info(f"Job {job_id}: {stage_name} ({progress}%)")
        
        # Mark as completed
        asset_url = f"https://cdn.gameforge.ai/assets/{job_id}_upscaled.png"
        _job_storage[job_id]["status"] = "completed"
        _job_storage[job_id]["asset_url"] = asset_url
        _job_storage[job_id]["updated_at"] = datetime.utcnow()
        
        # Save asset to project storage
        try:
            user_id = _job_storage[job_id].get("user_id")
            if user_id:
                asset_record = project_storage.save_asset_to_project(
                    user_id=user_id,
                    asset_url=asset_url,
                    job_data=_job_storage[job_id]
                )
                logger.info(
                    f"Super-res asset saved to project: {asset_record.id}"
                )
        except Exception as e:
            logger.error(
                f"Failed to save super-res asset to project: {str(e)}"
            )
        
        logger.info(f"Super-resolution job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Super-resolution job {job_id} failed: {str(e)}")
        _job_storage[job_id]["status"] = "failed"
        _job_storage[job_id]["error_message"] = str(e)
        _job_storage[job_id]["updated_at"] = datetime.utcnow()


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/generate", response_model=AIGenerateResponse, status_code=202)
@rate_limit(max_requests=50, window_seconds=3600)  # 50 requests per hour
@validate_input_security
async def generate_asset(
    request: AIGenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_ai_access)
):
    """
    Generate AI assets with structured job tracking.
    
    Requires authentication. Returns a job ID for tracking generation progress.
    """
    start_time = time.time()
    job_id = f"job_{uuid.uuid4()}"
    
    # Record HTTP request metrics
    metrics.record_http_request("POST", "/ai/generate", 202)
    
    # Structured logging for job start
    log_ai_job_event(
        event_type="job_started",
        job_id=job_id,
        user_id=current_user.get("user_id", "unknown"),
        model=request.model,
        prompt=request.prompt[:100],  # Truncate for security
        style=request.style,
        category=request.category,
        dimensions=f"{request.width}x{request.height}"
    )
    
    try:
        # Generate unique job ID
        
        # Estimate completion time
        estimated_duration = estimate_generation_time(request)
        estimated_completion = (
            datetime.utcnow() + timedelta(seconds=estimated_duration)
        )
        
        # Create job metadata with security sanitization
        raw_metadata = {
            "prompt": request.prompt,
            "style": request.style,
            "category": request.category,
            "dimensions": f"{request.width}x{request.height}",
            "quality": request.quality,
            "count": request.count,
            "model": request.model,
            "current_stage": "Queued"
        }
        
        # Sanitize metadata to prevent information leaks
        sanitized_metadata = SecurityValidator.sanitize_job_metadata(
            raw_metadata
        )
        
        job_data = {
            "id": job_id,
            "user_id": current_user.get("user_id", "unknown"),
            "status": "pending",
            "progress": 0.0,
            "asset_url": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "estimated_completion": estimated_completion,
            "error_message": None,
            "metadata": sanitized_metadata
        }
        
        # Store job data
        _job_storage[job_id] = job_data
        
        # Start background processing
        background_tasks.add_task(process_ai_generation, job_id, request)
        
        log_ai_job_event(
            event_type="job_queued",
            job_id=job_id,
            user_id=current_user.get("user_id", "unknown"),
            model=request.model or "default",
            estimated_duration=estimated_duration
        )
        
        return AIGenerateResponse(
            job_id=job_id,
            status="pending",
            message="Asset generation job queued successfully",
            estimated_duration=estimated_duration,
            tracking_url=f"/api/ai/job/{job_id}"
        )
        
    except Exception as e:
        # Record error metrics
        metrics.inference_requests_total.labels(
            model=request.model, status='error'
        ).inc()
        
        log_ai_job_event(
            event_type="job_creation_failed",
            job_id=job_id,
            user_id=current_user.get("user_id", "unknown"),
            model=request.model or "default",
            error=str(e)
        )
        
        metrics.record_http_request("POST", "/ai/generate", 500)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue asset generation: {str(e)}"
        )


@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: Dict[str, Any] = Depends(require_ai_access)
):
    """
    Get structured job metadata including status, progress, and asset URL.
    Only returns jobs owned by the authenticated user.
    """
    try:
        job_data = _job_storage.get(job_id)
        
        if not job_data:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Verify job ownership
        if job_data.get("user_id") != current_user.get("user_id", "unknown"):
            raise HTTPException(
                status_code=403,
                detail="Access denied: Job belongs to another user"
            )
        
        # Convert to JobMetadata model
        metadata = JobMetadata(**job_data)
        
        return JobStatusResponse(
            success=True,
            data=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve job status: {str(e)}"
        )


@router.post("/superres", response_model=AIGenerateResponse, status_code=202)
@rate_limit(max_requests=30, window_seconds=3600)  # 30 requests per hour
@validate_input_security
async def super_resolution(
    background_tasks: BackgroundTasks,
    request: SuperResRequest,
    file: UploadFile = File(..., description="Image file to upscale"),
    current_user: Dict[str, Any] = Depends(require_ai_access)
):
    """
    Perform AI-powered super-resolution on uploaded images.
    
    Requires authentication. Returns job ID for tracking progress.
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=400,
                detail="File must be an image"
            )
        
        # Validate file size (max 50MB)
        validate_file_size(file, max_size_mb=50)
        
        # Generate unique job ID
        job_id = f"superres_{uuid.uuid4()}"
        
        # Estimate processing time
        base_time = 60  # Base 60 seconds for super-res
        estimated_duration = int(base_time * request.scale_factor * 0.5)
        estimated_completion = (
            datetime.utcnow() + timedelta(seconds=estimated_duration)
        )
        
        # Create job metadata
        job_data = {
            "id": job_id,
            "user_id": current_user.get("user_id", "unknown"),
            "status": "pending",
            "progress": 0.0,
            "asset_url": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "estimated_completion": estimated_completion,
            "error_message": None,
            "metadata": {
                "operation": "super_resolution",
                "scale_factor": request.scale_factor,
                "original_filename": file.filename,
                "file_size": file.size if hasattr(file, 'size') else 0,
                "enhance_details": request.enhance_details,
                "preserve_style": request.preserve_style,
                "model": request.model,
                "current_stage": "Queued"
            }
        }
        
        # Store job data
        _job_storage[job_id] = job_data
        
        # In production, save file to temporary storage
        file_path = f"/tmp/{job_id}_{file.filename}"
        
        # Start background processing
        background_tasks.add_task(
            process_super_resolution, job_id, request, file_path
        )
        
        logger.info(f"Created super-resolution job {job_id}")
        
        return AIGenerateResponse(
            job_id=job_id,
            status="pending",
            message="Super-resolution job queued successfully",
            estimated_duration=estimated_duration,
            tracking_url=f"/api/ai/job/{job_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create super-resolution job: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue super-resolution: {str(e)}"
        )


@router.delete("/job/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: Dict[str, Any] = Depends(require_ai_access)
):
    """Cancel a running job. Only job owner can cancel their jobs."""
    try:
        job_data = _job_storage.get(job_id)
        
        if not job_data:
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        # Verify job ownership
        if job_data.get("user_id") != current_user.get("user_id", "unknown"):
            raise HTTPException(
                status_code=403,
                detail="Access denied: Job belongs to another user"
            )
            raise HTTPException(
                status_code=404,
                detail=f"Job {job_id} not found"
            )
        
        if job_data["status"] in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job in {job_data['status']} state"
            )
        
        # Update job status
        job_data["status"] = "cancelled"
        job_data["updated_at"] = datetime.utcnow()
        job_data["error_message"] = "Job cancelled by user"
        
        logger.info(f"Cancelled job {job_id}")
        
        return {"message": f"Job {job_id} cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.get("/jobs", response_model=List[JobMetadata])
async def list_jobs(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_ai_access)
):
    """List jobs with optional filtering. Only returns user's own jobs."""
    try:
        jobs = list(_job_storage.values())
        
        # Filter by user ID (only show current user's jobs)
        user_id = current_user.get("user_id", "unknown")
        jobs = [job for job in jobs if job.get("user_id") == user_id]
        
        # Filter by status if provided
        if status:
            jobs = [job for job in jobs if job["status"] == status]
        
        # Sort by created_at (newest first)
        jobs.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        paginated_jobs = jobs[offset:offset + limit]
        
        # Convert to JobMetadata models
        return [JobMetadata(**job) for job in paginated_jobs]
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve jobs: {str(e)}"
        )