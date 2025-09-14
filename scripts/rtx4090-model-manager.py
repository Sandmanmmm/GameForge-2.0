#!/usr/bin/env python3
"""
GameForge RTX 4090 Model Manager for Vast.ai
Optimized model deployment and management for RTX 4090 with 24GB VRAM
"""

import os
import sys
import time
import requests
import subprocess
from pathlib import Path
from typing import List, Dict
import json
import logging
import torch

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RTX4090ModelManager:
    """Model manager optimized for RTX 4090 with 24GB VRAM"""
    
    def __init__(self, model_store_path="/models"):
        self.model_store_path = Path(model_store_path)
        self.model_store_path.mkdir(exist_ok=True)
        
        # RTX 4090 specifications
        self.gpu_memory = 24 * 1024  # 24GB in MB
        self.max_model_size = int(self.gpu_memory * 0.7)  # Use 70% for models
        
        # Model catalog optimized for RTX 4090
        self.model_catalog = {
            "stable-diffusion-xl": {
                "source": "stabilityai/stable-diffusion-xl-base-1.0",
                "type": "text-to-image",
                "vram_usage": 8000,  # ~8GB VRAM
                "batch_size": 4,
                "priority": "high"
            },
            "llama-7b-chat": {
                "source": "meta-llama/Llama-2-7b-chat-hf", 
                "type": "text-generation",
                "vram_usage": 14000,  # ~14GB VRAM
                "batch_size": 2,
                "priority": "high"
            },
            "whisper-large": {
                "source": "openai/whisper-large-v3",
                "type": "speech-to-text", 
                "vram_usage": 6000,  # ~6GB VRAM
                "batch_size": 8,
                "priority": "medium"
            },
            "clip-vit-large": {
                "source": "openai/clip-vit-large-patch14",
                "type": "multimodal",
                "vram_usage": 4000,  # ~4GB VRAM
                "batch_size": 16,
                "priority": "medium"
            },
            "resnet-50": {
                "source": "microsoft/resnet-50",
                "type": "image-classification",
                "vram_usage": 2000,  # ~2GB VRAM
                "batch_size": 32,
                "priority": "low"
            }
        }
    
    def check_rtx4090_availability(self) -> bool:
        """Check if RTX 4090 is available and properly configured"""
        try:
            # Check CUDA availability
            if not torch.cuda.is_available():
                logger.error("CUDA not available")
                return False
            
            # Check GPU memory
            gpu_memory = torch.cuda.get_device_properties(0).total_memory
            gpu_memory_gb = gpu_memory / (1024**3)
            
            logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
            logger.info(f"GPU memory: {gpu_memory_gb:.1f}GB")
            
            if gpu_memory_gb < 20:  # RTX 4090 should have ~24GB
                logger.warning(f"GPU memory ({gpu_memory_gb:.1f}GB) less than expected for RTX 4090")
            
            # Check nvidia-smi
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            if "RTX 4090" in result.stdout:
                logger.info("RTX 4090 confirmed via nvidia-smi")
            
            return True
            
        except Exception as e:
            logger.error(f"RTX 4090 check failed: {e}")
            return False
    
    def get_optimal_model_combination(self) -> List[str]:
        """Get optimal combination of models that fit in RTX 4090 VRAM"""
        sorted_models = sorted(
            self.model_catalog.items(),
            key=lambda x: (x[1]['priority'] == 'high', -x[1]['vram_usage'])
        )
        
        selected_models = []
        total_vram = 0
        
        for model_name, model_info in sorted_models:
            if total_vram + model_info['vram_usage'] <= self.max_model_size:
                selected_models.append(model_name)
                total_vram += model_info['vram_usage']
                logger.info(f"Selected {model_name}: {model_info['vram_usage']}MB (total: {total_vram}MB)")
        
        logger.info(f"Optimal model combination uses {total_vram}MB / {self.max_model_size}MB")
        return selected_models
    
    def download_huggingface_model(self, model_name: str) -> bool:
        """Download model from Hugging Face Hub"""
        model_info = self.model_catalog[model_name]
        model_path = self.model_store_path / model_name
        
        try:
            logger.info(f"Downloading {model_name} from {model_info['source']}")
            
            # Use huggingface_hub for efficient downloading
            from huggingface_hub import snapshot_download
            
            # Download model with optimizations
            snapshot_download(
                repo_id=model_info['source'],
                local_dir=str(model_path),
                local_dir_use_symlinks=False,  # For vast.ai compatibility
                resume_download=True,
                max_workers=4  # Parallel download
            )
            
            # Create TorchServe configuration
            self.create_torchserve_config(model_name, model_path)
            
            logger.info(f"Successfully downloaded {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {model_name}: {e}")
            return False
    
    def create_torchserve_config(self, model_name: str, model_path: Path):
        """Create TorchServe model configuration"""
        model_info = self.model_catalog[model_name]
        
        # Create model config
        config = {
            "modelName": model_name,
            "modelVersion": "1.0",
            "batchSize": model_info['batch_size'],
            "maxBatchDelay": 100,
            "responseTimeout": 120,
            "deviceType": "gpu",
            "deviceIds": "0",  # Use first GPU (RTX 4090)
            "parallelLevel": 1,
            "maxWorkers": 4,
            "minWorkers": 1
        }
        
        config_path = model_path / "model-config.yaml"
        with open(config_path, 'w') as f:
            import yaml
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"Created TorchServe config for {model_name}")
    
    def monitor_gpu_metrics(self) -> Dict:
        """Monitor RTX 4090 performance metrics"""
        try:
            # PyTorch GPU metrics
            gpu_memory_allocated = torch.cuda.memory_allocated() / (1024**3)
            gpu_memory_reserved = torch.cuda.memory_reserved() / (1024**3)
            gpu_utilization = torch.cuda.utilization() if hasattr(torch.cuda, 'utilization') else 0
            
            # nvidia-smi metrics
            result = subprocess.run([
                'nvidia-smi', 
                '--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu,power.draw',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                values = result.stdout.strip().split(', ')
                smi_metrics = {
                    'memory_used_mb': int(values[0]),
                    'memory_total_mb': int(values[1]),
                    'gpu_utilization': int(values[2]),
                    'temperature': int(values[3]),
                    'power_draw': float(values[4])
                }
            else:
                smi_metrics = {}
            
            return {
                'torch_memory_allocated_gb': gpu_memory_allocated,
                'torch_memory_reserved_gb': gpu_memory_reserved,
                'torch_utilization': gpu_utilization,
                **smi_metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to get GPU metrics: {e}")
            return {}
    
    def optimize_for_rtx4090(self):
        """Apply RTX 4090 specific optimizations"""
        try:
            # Set optimal GPU settings
            if torch.cuda.is_available():
                # Enable memory fraction optimization
                torch.cuda.set_per_process_memory_fraction(0.95)  # Use 95% of available memory
                
                # Enable CuDNN optimizations
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.deterministic = False
                
                # Set optimal tensor core usage
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                
                logger.info("Applied RTX 4090 optimizations")
                
                # Display GPU info
                device = torch.cuda.get_device_properties(0)
                logger.info(f"GPU: {device.name}")
                logger.info(f"Memory: {device.total_memory / (1024**3):.1f}GB")
                logger.info(f"SM Count: {device.multi_processor_count}")
                
        except Exception as e:
            logger.error(f"Failed to apply optimizations: {e}")
    
    def deploy_models(self, model_names: List[str] = None) -> bool:
        """Deploy models to RTX 4090"""
        if model_names is None:
            model_names = self.get_optimal_model_combination()
        
        success_count = 0
        for model_name in model_names:
            try:
                logger.info(f"Deploying {model_name}...")
                if self.download_huggingface_model(model_name):
                    success_count += 1
                    
                    # Verify deployment
                    metrics = self.monitor_gpu_metrics()
                    logger.info(f"GPU memory after {model_name}: {metrics.get('torch_memory_allocated_gb', 0):.1f}GB")
                    
            except Exception as e:
                logger.error(f"Failed to deploy {model_name}: {e}")
        
        logger.info(f"Successfully deployed {success_count}/{len(model_names)} models")
        return success_count == len(model_names)
    
    def health_check(self) -> Dict:
        """Comprehensive health check for RTX 4090 deployment"""
        health_status = {
            'rtx4090_available': False,
            'cuda_available': False,
            'models_deployed': 0,
            'gpu_memory_usage': 0,
            'gpu_utilization': 0,
            'temperature': 0,
            'power_draw': 0,
            'status': 'unhealthy'
        }
        
        try:
            # Check RTX 4090
            health_status['rtx4090_available'] = self.check_rtx4090_availability()
            health_status['cuda_available'] = torch.cuda.is_available()
            
            # Check deployed models
            if self.model_store_path.exists():
                deployed_models = [d for d in self.model_store_path.iterdir() if d.is_dir()]
                health_status['models_deployed'] = len(deployed_models)
            
            # Get GPU metrics
            metrics = self.monitor_gpu_metrics()
            health_status.update({
                'gpu_memory_usage': metrics.get('torch_memory_allocated_gb', 0),
                'gpu_utilization': metrics.get('gpu_utilization', 0),
                'temperature': metrics.get('temperature', 0),
                'power_draw': metrics.get('power_draw', 0)
            })
            
            # Determine overall status
            if (health_status['rtx4090_available'] and 
                health_status['cuda_available'] and 
                health_status['models_deployed'] > 0):
                health_status['status'] = 'healthy'
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
        
        return health_status

def main():
    """Main execution for RTX 4090 model manager"""
    logger.info("Starting GameForge RTX 4090 Model Manager")
    
    # Initialize manager
    manager = RTX4090ModelManager("/models")
    
    # Apply RTX 4090 optimizations
    manager.optimize_for_rtx4090()
    
    # Check RTX 4090 availability
    if not manager.check_rtx4090_availability():
        logger.error("RTX 4090 not available or not properly configured")
        sys.exit(1)
    
    # Deploy optimal model combination
    logger.info("Deploying optimal model combination for RTX 4090...")
    if manager.deploy_models():
        logger.info("All models deployed successfully")
    else:
        logger.warning("Some models failed to deploy")
    
    # Health check
    health = manager.health_check()
    logger.info(f"Health status: {health['status']}")
    logger.info(f"Models deployed: {health['models_deployed']}")
    logger.info(f"GPU utilization: {health['gpu_utilization']}%")
    logger.info(f"GPU memory: {health['gpu_memory_usage']:.1f}GB")
    logger.info(f"Temperature: {health['temperature']}°C")
    
    # Start monitoring loop
    logger.info("Starting RTX 4090 monitoring...")
    try:
        while True:
            metrics = manager.monitor_gpu_metrics()
            if metrics:
                logger.info(
                    f"RTX 4090 - Memory: {metrics.get('torch_memory_allocated_gb', 0):.1f}GB, "
                    f"Utilization: {metrics.get('gpu_utilization', 0)}%, "
                    f"Temp: {metrics.get('temperature', 0)}°C, "
                    f"Power: {metrics.get('power_draw', 0):.1f}W"
                )
            time.sleep(30)  # Monitor every 30 seconds
            
    except KeyboardInterrupt:
        logger.info("Shutting down RTX 4090 model manager...")

if __name__ == "__main__":
    main()
