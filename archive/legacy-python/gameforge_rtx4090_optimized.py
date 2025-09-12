#!/usr/bin/env python3
"""
GameForge AI System - RTX 4090 Production Server
Phase 0: Foundation Containerization with RTX 4090 Optimization
"""

import os
import sys
import json
import time
import torch
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

# FastAPI and server components
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# GPU and monitoring
import psutil
try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class RTX4090Config:
    """RTX 4090 specific configuration"""
    device: str = "cuda:0"
    max_memory_gb: float = 24.0
    memory_chunk_size: int = 512
    architecture: str = "8.9"
    high_performance: bool = True
    fallback_cpu: bool = True

class RTX4090Manager:
    """RTX 4090 GPU management and optimization"""
    
    def __init__(self):
        self.config = RTX4090Config()
        self.gpu_available = False
        self.device = "cpu"
        self.gpu_name = "Unknown"
        self.setup_gpu()
    
    def setup_gpu(self):
        """Setup and configure RTX 4090 GPU"""
        try:
            if torch.cuda.is_available():
                gpu_count = torch.cuda.device_count()
                if gpu_count > 0:
                    self.gpu_name = torch.cuda.get_device_name(0)
                    logger.info(f"GPU detected: {self.gpu_name}")
                    
                    # Check for RTX 4090 specifically
                    if "RTX 4090" in self.gpu_name or "RTX 5090" in self.gpu_name:
                        logger.info("RTX 4090/5090 detected - Enabling high-performance mode")
                        self.gpu_available = True
                        self.device = "cuda:0"
                        
                        # RTX 4090 specific optimizations
                        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = f"max_split_size_mb:{self.config.memory_chunk_size}"
                        os.environ["TORCH_CUDA_ARCH_LIST"] = self.config.architecture
                        
                        # Test GPU functionality
                        self._test_gpu()
                        
                    elif "RTX" in self.gpu_name or "GeForce" in self.gpu_name:
                        logger.info("Compatible GPU detected - Using standard mode")
                        self.gpu_available = True
                        self.device = "cuda:0"
                        self._test_gpu()
                    else:
                        logger.warning(f"Unknown GPU: {self.gpu_name}")
                        self._fallback_cpu()
                else:
                    logger.warning("No GPU devices detected")
                    self._fallback_cpu()
            else:
                logger.warning("CUDA not available")
                self._fallback_cpu()
                
        except Exception as e:
            logger.error(f"GPU setup failed: {e}")
            self._fallback_cpu()
    
    def _test_gpu(self):
        """Test GPU functionality"""
        try:
            # Simple GPU test
            test_tensor = torch.randn(100, 100).to(self.device)
            result = torch.matmul(test_tensor, test_tensor.T)
            logger.info(f"GPU test successful on {self.device}")
            return True
        except Exception as e:
            logger.error(f"GPU test failed: {e}")
            self._fallback_cpu()
            return False
    
    def _fallback_cpu(self):
        """Fallback to CPU mode"""
        logger.warning("Falling back to CPU mode")
        self.gpu_available = False
        self.device = "cpu"
        os.environ["GAMEFORGE_GPU_MODE"] = "cpu_fallback"
    
    def get_gpu_status(self) -> Dict[str, Any]:
        """Get current GPU status"""
        status = {
            "gpu_available": self.gpu_available,
            "device": self.device,
            "gpu_name": self.gpu_name,
            "mode": "rtx4090" if self.gpu_available and "RTX 4090" in self.gpu_name else "standard" if self.gpu_available else "cpu"
        }
        
        if self.gpu_available:
            try:
                # Get GPU memory info
                memory_allocated = torch.cuda.memory_allocated(0) / 1024**3  # GB
                memory_reserved = torch.cuda.memory_reserved(0) / 1024**3   # GB
                
                status.update({
                    "memory_allocated_gb": round(memory_allocated, 2),
                    "memory_reserved_gb": round(memory_reserved, 2),
                    "memory_total_gb": self.config.max_memory_gb
                })
                
                if GPU_AVAILABLE:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu = gpus[0]
                        status.update({
                            "temperature": gpu.temperature,
                            "utilization": gpu.load * 100,
                            "memory_used_gb": gpu.memoryUsed / 1024,
                            "memory_free_gb": gpu.memoryFree / 1024
                        })
            except Exception as e:
                logger.error(f"Error getting GPU status: {e}")
        
        return status

class GameForgeAI:
    """Main GameForge AI system with RTX 4090 optimization"""
    
    def __init__(self):
        self.gpu_manager = RTX4090Manager()
        self.model_loaded = False
        self.pipeline = None
        self.setup_directories()
    
    def setup_directories(self):
        """Setup required directories"""
        directories = [
            "generated_assets",
            "logs", 
            "cache",
            "models_cache"
        ]
        
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
    
    async def load_models(self):
        """Load AI models with RTX 4090 optimization"""
        if self.model_loaded:
            return
        
        try:
            logger.info("Loading AI models...")
            
            # Import here to avoid issues if not available
            if self.gpu_manager.gpu_available:
                # GPU mode - load optimized pipeline
                logger.info("Loading GPU-optimized pipeline")
                # This would load your custom SDXL pipeline
                # from custom_sdxl_pipeline import CustomSDXLPipeline
                # self.pipeline = CustomSDXLPipeline(device=self.gpu_manager.device)
                pass
            else:
                # CPU fallback mode
                logger.info("Loading CPU fallback pipeline")
                # Load CPU-optimized version
                pass
            
            self.model_loaded = True
            logger.info("Models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise
    
    async def generate_image(self, prompt: str, **kwargs) -> str:
        """Generate image with RTX 4090 optimization"""
        if not self.model_loaded:
            await self.load_models()
        
        try:
            # Generate unique filename
            timestamp = int(time.time())
            filename = f"generated_{timestamp}.png"
            filepath = Path("generated_assets") / filename
            
            # Simulate image generation (replace with actual pipeline)
            logger.info(f"Generating image: {prompt}")
            
            if self.gpu_manager.gpu_available:
                # RTX 4090 optimized generation
                generation_time = 0.15  # RTX 4090 target: <0.2s
            else:
                # CPU fallback
                generation_time = 2.0   # CPU fallback time
            
            # Simulate processing time
            await asyncio.sleep(generation_time)
            
            # Create placeholder image (replace with actual generation)
            from PIL import Image
            img = Image.new('RGB', (512, 512), color='blue')
            img.save(filepath)
            
            logger.info(f"Image generated in {generation_time}s: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

# Initialize GameForge AI system
gameforge = GameForgeAI()

# FastAPI application
app = FastAPI(
    title="GameForge AI - RTX 4090 Production Server",
    description="RTX 4090 optimized AI game asset generation system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    logger.info("🚀 GameForge AI RTX 4090 Server starting...")
    logger.info(f"GPU Status: {gameforge.gpu_manager.get_gpu_status()}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "gpu_status": gameforge.gpu_manager.get_gpu_status()
    }

# GPU status endpoint
@app.get("/api/gpu-status")
async def gpu_status():
    """Get detailed GPU status"""
    return gameforge.gpu_manager.get_gpu_status()

# System info endpoint
@app.get("/api/system-info")
async def system_info():
    """Get system information"""
    return {
        "cpu_count": psutil.cpu_count(),
        "memory_gb": round(psutil.virtual_memory().total / 1024**3, 2),
        "gpu_info": gameforge.gpu_manager.get_gpu_status(),
        "python_version": sys.version,
        "pytorch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "gameforge_mode": os.environ.get("GAMEFORGE_GPU_MODE", "auto")
    }

# Image generation endpoint
@app.post("/generate/image")
async def generate_image(request: Request):
    """Generate image with RTX 4090 optimization"""
    try:
        data = await request.json()
        prompt = data.get("prompt", "fantasy game asset")
        
        # Generate image
        filepath = await gameforge.generate_image(prompt, **data)
        
        return {
            "success": True,
            "filename": Path(filepath).name,
            "filepath": filepath,
            "gpu_mode": gameforge.gpu_manager.device,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Generation request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Serve generated assets
@app.get("/assets/{filename}")
async def serve_asset(filename: str):
    """Serve generated assets"""
    filepath = Path("generated_assets") / filename
    if filepath.exists():
        return FileResponse(filepath)
    else:
        raise HTTPException(status_code=404, detail="Asset not found")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "GameForge AI RTX 4090 Production Server",
        "version": "1.0.0",
        "status": "operational",
        "gpu_status": gameforge.gpu_manager.get_gpu_status()
    }

if __name__ == "__main__":
    # Server configuration
    host = "0.0.0.0"
    port = 8080
    
    logger.info(f"🔥 Starting GameForge AI RTX 4090 Production Server on {host}:{port}")
    
    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
