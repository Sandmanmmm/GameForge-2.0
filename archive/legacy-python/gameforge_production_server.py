# gameforge_production_server.py
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
import asyncio
import torch
from pathlib import Path
import logging
import json
from datetime import datetime
import uuid
import os
import aiohttp
import base64
import io
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RTX 5090 Ultimate GPU Server Configuration (🔥 LIVE & READY!)
GPU_ENDPOINT = "https://referring-visitors-billing-economics.trycloudflare.com"  # RTX 5090 Ultimate
# Instance Details:
# Instance ID: 25632987
# GPU: RTX 5090 (33.7GB VRAM, 170 CUDA cores)
# Status: 🚀 LIVE - SDXL Ultimate Pipeline Active - XFormers Enabled!
# Local Port: 8081 (Cloudflare tunnel handles routing)
# Capabilities: SDXL Ultimate, High-res (up to 2048x2048), Batch processing, RTX 5090 optimization

# Backup endpoints (previous RTX 4090 instances)
GPU_ENDPOINT_ALT = "http://localhost:8081"  # Local testing
# Legacy: "http://172.97.240.138:41392"  # Previous RTX 4090 instance

# Use the working endpoint
GPU_ENDPOINT = GPU_ENDPOINT  # Keep original for now

app = FastAPI(
    title="GameForge SDXL API",
    description="Professional game asset generation using SDXL on RTX 4090",
    version="1.0.0"
)

# CORS middleware for web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class AssetRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    category: str = Field(..., pattern="^(weapons|items|environments|characters)$")
    style: str = Field(default="fantasy", pattern="^(fantasy|sci_fi|medieval|modern|steampunk)$")
    rarity: str = Field(default="common", pattern="^(common|uncommon|rare|epic|legendary)$")
    width: int = Field(default=512, ge=256, le=2048)
    height: int = Field(default=512, ge=256, le=2048)
    steps: int = Field(default=20, ge=10, le=50)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)
    negative_prompt: str = Field(default="blurry, low quality, distorted")
    batch_size: int = Field(default=1, ge=1, le=4)
    tags: List[str] = Field(default_factory=list)

class JobResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    estimated_completion: Optional[str]
    asset_urls: List[str] = Field(default_factory=list)

class AssetResponse(BaseModel):
    id: str
    url: str
    thumbnail_url: str
    metadata: Dict[str, Any]
    download_url: str

# Global storage for demo
jobs_storage = {}
assets_storage = {}


class VastGPUClient:
    """Client for communicating with Vast GPU server"""
    
    def __init__(self, gpu_endpoint: str):
        self.gpu_endpoint = gpu_endpoint.rstrip('/')
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> dict:
        """Check GPU server health"""
        try:
            async with self.session.get(f"{self.gpu_endpoint}/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"status": "unhealthy", "error": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def generate_image(self, prompt: str, **kwargs) -> dict:
        """Generate image via GPU server"""
        try:
            payload = {
                "prompt": prompt,
                "negative_prompt": kwargs.get("negative_prompt", ""),
                "width": kwargs.get("width", 1024),
                "height": kwargs.get("height", 1024),
                "num_inference_steps": kwargs.get("steps", 20),
                "guidance_scale": kwargs.get("guidance_scale", 7.5),
                "seed": kwargs.get("seed")
            }
            
            async with self.session.post(
                f"{self.gpu_endpoint}/generate",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}


class GameForgeProductionAPI:
    def __init__(self):
        self.initialize_services()
        
    def initialize_services(self):
        """Initialize all production services"""
        logger.info("Initializing GameForge Production API...")
        
        # Check local GPU availability
        if torch.cuda.is_available():
            logger.info(f"Local GPU detected: {torch.cuda.get_device_name(0)}")
        else:
            logger.info("No local GPU - using remote Vast GPU")
        
        logger.info(f"Vast GPU endpoint configured: {GPU_ENDPOINT}")
        logger.info("GameForge API initialized successfully")

# API Endpoints
@app.post("/api/v1/assets")
async def create_asset(request: AssetRequest, background_tasks: BackgroundTasks):
    """Create new asset generation job"""
    try:
        job_id = str(uuid.uuid4())
        
        # Store job data
        job_data = {
            "job_id": job_id,
            "request": request.dict(),
            "status": "queued",
            "progress": 0.0,
            "created_at": datetime.now().isoformat()
        }
        
        jobs_storage[job_id] = job_data
        
        # Start background processing
        background_tasks.add_task(process_generation_job, job_id)
        
        return {
            "status": "success",
            "job_id": job_id,
            "message": "Asset generation started"
        }
        
    except Exception as e:
        logger.error(f"Asset creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status and progress"""
    try:
        job_data = jobs_storage.get(job_id)
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "status": "success",
            "job": {
                "id": job_id,
                "status": job_data.get("status", "unknown"),
                "progress": job_data.get("progress", 0.0),
                "created_at": job_data.get("created_at"),
                "completed_at": job_data.get("completed_at"),
                "asset_id": job_data.get("asset_id")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/assets/{asset_id}")
async def get_asset(asset_id: str):
    """Get asset details and download URL"""
    try:
        asset = assets_storage.get(asset_id)
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        return {
            "status": "success",
            "asset": asset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Asset retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/assets")
async def list_assets(
    category: Optional[str] = None,
    style: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List assets with filtering"""
    try:
        assets = list(assets_storage.values())
        
        if category:
            assets = [a for a in assets if a.get("category") == category]
        if style:
            assets = [a for a in assets if a.get("style") == style]
            
        # Apply pagination
        paginated_assets = assets[offset:offset + limit]
        
        return {
            "status": "success",
            "assets": paginated_assets,
            "count": len(paginated_assets),
            "total": len(assets),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Asset listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/health")
async def health_check():
    """API health check"""
    try:
        # Check local GPU
        local_gpu_available = torch.cuda.is_available()
        local_gpu_memory = torch.cuda.memory_allocated() / 1024**3 if local_gpu_available else 0
        
        # Check remote GPU server
        gpu_server_status = {"status": "unknown"}
        try:
            async with VastGPUClient(GPU_ENDPOINT) as client:
                gpu_server_status = await client.health_check()
        except Exception as e:
            gpu_server_status = {"status": "error", "error": str(e)}
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "local_gpu": {
                    "available": local_gpu_available,
                    "memory_gb": round(local_gpu_memory, 2),
                    "device": torch.cuda.get_device_name(0) if local_gpu_available else None
                },
                "vast_gpu_server": gpu_server_status,
                "api": {"running": True},
                "jobs": {"active": len(jobs_storage)},
                "assets": {"total": len(assets_storage)}
            }
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

async def process_generation_job(job_id: str):
    """Background task to process generation job using Vast GPU"""
    job_data = None
    try:
        # Get job data
        job_data = jobs_storage[job_id]
        request_data = job_data["request"]
        
        # Update status
        job_data["status"] = "processing"
        job_data["progress"] = 0.1
        
        logger.info(f"Processing job {job_id} on Vast GPU server")
        
        # Generate image using Vast GPU server
        async with VastGPUClient(GPU_ENDPOINT) as client:
            # Update progress
            job_data["progress"] = 0.3
            
            # Create enhanced prompt based on category and style
            enhanced_prompt = enhance_prompt(
                request_data["prompt"],
                request_data["category"],
                request_data["style"],
                request_data["rarity"]
            )
            
            logger.info(f"Enhanced prompt: {enhanced_prompt}")
            
            # Call GPU server
            job_data["progress"] = 0.5
            result = await client.generate_image(
                prompt=enhanced_prompt,
                negative_prompt=request_data["negative_prompt"],
                width=request_data["width"],
                height=request_data["height"],
                steps=request_data["steps"],
                guidance_scale=request_data["guidance_scale"]
            )
            
            if result.get("success", False):
                # Save generated image
                job_data["progress"] = 0.8
                asset_id = str(uuid.uuid4())
                
                # Save image data (in production, save to file storage)
                image_data = result.get("image_base64", "")
                save_image_file(asset_id, image_data)
                
                # Create asset metadata
                asset_data = {
                    "id": asset_id,
                    "prompt": enhanced_prompt,
                    "original_prompt": request_data["prompt"],
                    "category": request_data["category"],
                    "style": request_data["style"],
                    "rarity": request_data["rarity"],
                    "resolution": f"{request_data['width']}x{request_data['height']}",
                    "file_url": f"/api/v1/assets/{asset_id}/download",
                    "thumbnail_url": f"/api/v1/assets/{asset_id}/thumbnail",
                    "tags": request_data["tags"],
                    "created_at": datetime.now().isoformat(),
                    "generation_time": result.get("processing_time", 0),
                    "generation_id": result.get("generation_id", ""),
                    "status": "completed"
                }
                
                # Store asset
                assets_storage[asset_id] = asset_data
                
                # Update job
                job_data["status"] = "completed"
                job_data["progress"] = 1.0
                job_data["completed_at"] = datetime.now().isoformat()
                job_data["asset_id"] = asset_id
                
                logger.info(f"Job {job_id} completed successfully with asset {asset_id}")
            else:
                # Generation failed
                error_msg = result.get("error", "Unknown GPU server error")
                logger.error(f"GPU generation failed for job {job_id}: {error_msg}")
                job_data["status"] = "failed"
                job_data["error"] = error_msg
        
    except Exception as e:
        logger.error(f"Job processing failed: {e}")
        if job_data:
            job_data["status"] = "failed"
            job_data["error"] = str(e)


def enhance_prompt(base_prompt: str, category: str, style: str, rarity: str) -> str:
    """Enhance the prompt based on game asset parameters"""
    
    # Style modifiers
    style_modifiers = {
        "fantasy": "magical, enchanted, mystical",
        "sci_fi": "futuristic, high-tech, cyberpunk",
        "medieval": "ancient, classical, historical",
        "modern": "contemporary, realistic, urban",
        "steampunk": "mechanical, brass, Victorian era"
    }
    
    # Rarity modifiers
    rarity_modifiers = {
        "common": "simple, basic",
        "uncommon": "detailed, refined",
        "rare": "ornate, elaborate, impressive",
        "epic": "magnificent, powerful, legendary",
        "legendary": "divine, otherworldly, ultimate power"
    }
    
    # Category specific enhancements
    category_modifiers = {
        "weapons": "sharp, deadly, masterwork",
        "items": "useful, crafted, valuable",
        "environments": "atmospheric, immersive, detailed",
        "characters": "heroic, detailed, expressive"
    }
    
    # Build enhanced prompt
    enhanced = f"{base_prompt}"
    
    if category in category_modifiers:
        enhanced += f", {category_modifiers[category]}"
    
    if style in style_modifiers:
        enhanced += f", {style_modifiers[style]}"
    
    if rarity in rarity_modifiers:
        enhanced += f", {rarity_modifiers[rarity]}"
    
    # Add quality modifiers
    enhanced += ", high quality, professional game art, 4k, detailed"
    
    return enhanced


def save_image_file(asset_id: str, image_base64: str):
    """Save image file to storage (placeholder implementation)"""
    try:
        # Create assets directory if it doesn't exist
        assets_dir = Path("assets")
        assets_dir.mkdir(exist_ok=True)
        
        # Decode and save image
        if image_base64:
            image_data = base64.b64decode(image_base64)
            image_path = assets_dir / f"{asset_id}.png"
            
            with open(image_path, "wb") as f:
                f.write(image_data)
                
            logger.info(f"Saved asset image: {image_path}")
        
    except Exception as e:
        logger.error(f"Failed to save asset image {asset_id}: {e}")

# Initialize services
production_api = GameForgeProductionAPI()

if __name__ == "__main__":
    uvicorn.run(
        "gameforge_production_server:app",
        host="0.0.0.0",
        port=8000,
        workers=1,  # Single worker for GPU
        reload=False
    )
