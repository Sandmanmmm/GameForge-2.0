#!/usr/bin/env python3
"""
GameForge AI Model Externalization and Caching System
Removes model weights from Docker images and implements intelligent caching
"""

import os
import hashlib
import json
import logging
import asyncio
import aiofiles
import boto3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import redis
from botocore.exceptions import ClientError
import torch
from transformers import AutoModel, AutoTokenizer
from diffusers import StableDiffusionPipeline

# ========================================================================
# Configuration
# ========================================================================

class ModelConfig:
    """Model externalization configuration"""
    
    # Model registry configuration
    MODEL_REGISTRY_URL = os.getenv("MODEL_REGISTRY_URL", "s3://gameforge-models")
    MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "/tmp/model_cache")
    
    # Redis configuration for metadata caching
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/2")
    REDIS_TTL = int(os.getenv("REDIS_TTL", "3600"))  # 1 hour
    
    # AWS/MinIO configuration
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://minio:9000")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    
    # Model specifications
    MODELS = {
        "sdxl-base": {
            "source": "stabilityai/stable-diffusion-xl-base-1.0",
            "type": "diffusion",
            "size": "6.9GB",
            "priority": "high"
        },
        "sdxl-refiner": {
            "source": "stabilityai/stable-diffusion-xl-refiner-1.0", 
            "type": "diffusion",
            "size": "6.1GB",
            "priority": "medium"
        },
        "clip-vit": {
            "source": "openai/clip-vit-large-patch14",
            "type": "vision",
            "size": "1.7GB",
            "priority": "high"
        },
        "bert-base": {
            "source": "bert-base-uncased",
            "type": "language",
            "size": "440MB",
            "priority": "medium"
        }
    }

# ========================================================================
# Model Cache Manager
# ========================================================================

class ModelCacheManager:
    """Intelligent model caching and retrieval system"""
    
    def __init__(self):
        self.cache_dir = Path(ModelConfig.MODEL_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Redis for metadata
        self.redis_client = redis.from_url(ModelConfig.REDIS_URL)
        
        # Initialize S3/MinIO client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=ModelConfig.AWS_ENDPOINT_URL,
            aws_access_key_id=ModelConfig.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=ModelConfig.AWS_SECRET_ACCESS_KEY,
            region_name=ModelConfig.AWS_REGION
        )
        
        self.logger = logging.getLogger(__name__)
    
    def _get_model_hash(self, model_name: str, version: str = "latest") -> str:
        """Generate hash for model caching"""
        content = f"{model_name}:{version}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _get_cache_path(self, model_name: str, version: str = "latest") -> Path:
        """Get local cache path for model"""
        model_hash = self._get_model_hash(model_name, version)
        return self.cache_dir / f"{model_name}_{model_hash}"
    
    async def _check_local_cache(self, model_name: str, version: str = "latest") -> bool:
        """Check if model exists in local cache"""
        cache_path = self._get_cache_path(model_name, version)
        return cache_path.exists()
    
    async def _check_remote_cache(self, model_name: str, version: str = "latest") -> bool:
        """Check if model exists in remote storage"""
        try:
            model_hash = self._get_model_hash(model_name, version)
            key = f"models/{model_name}/{model_hash}/model.tar.gz"
            
            parsed_url = urlparse(ModelConfig.MODEL_REGISTRY_URL)
            bucket = parsed_url.netloc.split('.')[0] if '.' in parsed_url.netloc else parsed_url.path.strip('/')
            
            self.s3_client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    async def _download_from_remote(self, model_name: str, version: str = "latest") -> Path:
        """Download model from remote storage"""
        cache_path = self._get_cache_path(model_name, version)
        model_hash = self._get_model_hash(model_name, version)
        
        try:
            parsed_url = urlparse(ModelConfig.MODEL_REGISTRY_URL)
            bucket = parsed_url.netloc.split('.')[0] if '.' in parsed_url.netloc else parsed_url.path.strip('/')
            key = f"models/{model_name}/{model_hash}/model.tar.gz"
            
            self.logger.info(f"Downloading model {model_name} from remote storage...")
            
            # Download to temporary file first
            temp_path = cache_path.with_suffix('.tmp')
            self.s3_client.download_file(bucket, key, str(temp_path))
            
            # Extract and move to final location
            import tarfile
            cache_path.mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(temp_path, 'r:gz') as tar:
                tar.extractall(cache_path)
            
            temp_path.unlink()  # Remove temporary file
            
            self.logger.info(f"Model {model_name} downloaded and cached successfully")
            return cache_path
            
        except Exception as e:
            self.logger.error(f"Failed to download model {model_name}: {e}")
            raise
    
    async def _download_from_huggingface(self, model_name: str) -> Path:
        """Download model from HuggingFace Hub"""
        config = ModelConfig.MODELS.get(model_name)
        if not config:
            raise ValueError(f"Unknown model: {model_name}")
        
        cache_path = self._get_cache_path(model_name)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        source = config["source"]
        model_type = config["type"]
        
        try:
            self.logger.info(f"Downloading {model_name} from HuggingFace Hub...")
            
            if model_type == "diffusion":
                # Download diffusion model
                pipeline = StableDiffusionPipeline.from_pretrained(
                    source,
                    cache_dir=str(cache_path),
                    torch_dtype=torch.float16
                )
                pipeline.save_pretrained(str(cache_path / "model"))
                
            elif model_type in ["vision", "language"]:
                # Download transformer model
                model = AutoModel.from_pretrained(
                    source,
                    cache_dir=str(cache_path)
                )
                tokenizer = AutoTokenizer.from_pretrained(
                    source,
                    cache_dir=str(cache_path)
                )
                
                model.save_pretrained(str(cache_path / "model"))
                tokenizer.save_pretrained(str(cache_path / "tokenizer"))
            
            self.logger.info(f"Model {model_name} downloaded successfully")
            return cache_path
            
        except Exception as e:
            self.logger.error(f"Failed to download model {model_name} from HuggingFace: {e}")
            raise
    
    async def _upload_to_remote(self, model_name: str, cache_path: Path, version: str = "latest"):
        """Upload model to remote storage"""
        model_hash = self._get_model_hash(model_name, version)
        
        try:
            parsed_url = urlparse(ModelConfig.MODEL_REGISTRY_URL)
            bucket = parsed_url.netloc.split('.')[0] if '.' in parsed_url.netloc else parsed_url.path.strip('/')
            
            # Create tar.gz archive
            import tarfile
            archive_path = cache_path.with_suffix('.tar.gz')
            
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(cache_path, arcname='model')
            
            # Upload to S3/MinIO
            key = f"models/{model_name}/{model_hash}/model.tar.gz"
            self.s3_client.upload_file(str(archive_path), bucket, key)
            
            # Upload metadata
            metadata = {
                "model_name": model_name,
                "version": version,
                "hash": model_hash,
                "size": archive_path.stat().st_size,
                "uploaded_at": str(asyncio.get_event_loop().time())
            }
            
            metadata_key = f"models/{model_name}/{model_hash}/metadata.json"
            self.s3_client.put_object(
                Bucket=bucket,
                Key=metadata_key,
                Body=json.dumps(metadata),
                ContentType='application/json'
            )
            
            # Cache metadata in Redis
            self.redis_client.setex(
                f"model_metadata:{model_name}:{version}",
                ModelConfig.REDIS_TTL,
                json.dumps(metadata)
            )
            
            archive_path.unlink()  # Remove temporary archive
            
            self.logger.info(f"Model {model_name} uploaded to remote storage")
            
        except Exception as e:
            self.logger.error(f"Failed to upload model {model_name}: {e}")
            raise
    
    async def get_model(self, model_name: str, version: str = "latest") -> Path:
        """
        Get model from cache or download if necessary
        Returns path to cached model
        """
        self.logger.info(f"Requesting model: {model_name}:{version}")
        
        # Check local cache first
        if await self._check_local_cache(model_name, version):
            self.logger.info(f"Model {model_name} found in local cache")
            return self._get_cache_path(model_name, version)
        
        # Check remote cache
        if await self._check_remote_cache(model_name, version):
            self.logger.info(f"Model {model_name} found in remote cache")
            return await self._download_from_remote(model_name, version)
        
        # Download from HuggingFace and cache
        self.logger.info(f"Model {model_name} not cached, downloading from source...")
        cache_path = await self._download_from_huggingface(model_name)
        
        # Upload to remote cache for future use
        await self._upload_to_remote(model_name, cache_path, version)
        
        return cache_path
    
    async def preload_models(self, model_names: List[str], version: str = "latest"):
        """Preload multiple models concurrently"""
        self.logger.info(f"Preloading models: {model_names}")
        
        tasks = [self.get_model(name, version) for name in model_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Failed to preload model {model_names[i]}: {result}")
            else:
                self.logger.info(f"Successfully preloaded model {model_names[i]}")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        try:
            cache_size = sum(
                f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file()
            )
            
            cached_models = [
                d.name for d in self.cache_dir.iterdir() if d.is_dir()
            ]
            
            return {
                "cache_directory": str(self.cache_dir),
                "total_size_bytes": cache_size,
                "total_size_gb": round(cache_size / (1024**3), 2),
                "cached_models": cached_models,
                "model_count": len(cached_models)
            }
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {}
    
    async def cleanup_cache(self, max_size_gb: float = 50.0):
        """Clean up cache if it exceeds size limit"""
        stats = self.get_cache_stats()
        current_size_gb = stats.get("total_size_gb", 0)
        
        if current_size_gb > max_size_gb:
            self.logger.info(f"Cache size ({current_size_gb}GB) exceeds limit ({max_size_gb}GB), cleaning up...")
            
            # Get models sorted by access time (oldest first)
            models = []
            for model_dir in self.cache_dir.iterdir():
                if model_dir.is_dir():
                    access_time = model_dir.stat().st_atime
                    size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
                    models.append((access_time, size, model_dir))
            
            models.sort(key=lambda x: x[0])  # Sort by access time
            
            # Remove oldest models until under limit
            for access_time, size, model_dir in models:
                if current_size_gb <= max_size_gb:
                    break
                
                self.logger.info(f"Removing cached model: {model_dir.name}")
                import shutil
                shutil.rmtree(model_dir)
                current_size_gb -= size / (1024**3)

# ========================================================================
# Model Loader with Externalization
# ========================================================================

class ExternalizedModelLoader:
    """Model loader that uses externalized models"""
    
    def __init__(self):
        self.cache_manager = ModelCacheManager()
        self.loaded_models = {}
        self.logger = logging.getLogger(__name__)
    
    async def load_model(self, model_name: str, version: str = "latest", device: str = "cuda"):
        """Load model from external cache"""
        if f"{model_name}:{version}" in self.loaded_models:
            return self.loaded_models[f"{model_name}:{version}"]
        
        try:
            # Get model from cache
            model_path = await self.cache_manager.get_model(model_name, version)
            
            # Load based on model type
            config = ModelConfig.MODELS.get(model_name)
            if not config:
                raise ValueError(f"Unknown model: {model_name}")
            
            model_type = config["type"]
            
            if model_type == "diffusion":
                model = StableDiffusionPipeline.from_pretrained(
                    str(model_path / "model"),
                    torch_dtype=torch.float16
                ).to(device)
                
            elif model_type in ["vision", "language"]:
                model = AutoModel.from_pretrained(str(model_path / "model")).to(device)
            
            self.loaded_models[f"{model_name}:{version}"] = model
            self.logger.info(f"Model {model_name} loaded successfully")
            
            return model
            
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {e}")
            raise
    
    async def unload_model(self, model_name: str, version: str = "latest"):
        """Unload model to free memory"""
        key = f"{model_name}:{version}"
        if key in self.loaded_models:
            del self.loaded_models[key]
            torch.cuda.empty_cache()  # Clear GPU memory
            self.logger.info(f"Model {model_name} unloaded")
    
    def get_loaded_models(self) -> List[str]:
        """Get list of currently loaded models"""
        return list(self.loaded_models.keys())

# ========================================================================
# CLI Interface
# ========================================================================

async def main():
    """Command line interface for model management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GameForge Model Externalization")
    parser.add_argument("command", choices=["preload", "stats", "cleanup", "test"])
    parser.add_argument("--models", nargs="+", help="Model names to preload")
    parser.add_argument("--max-size", type=float, default=50.0, help="Max cache size in GB")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    cache_manager = ModelCacheManager()
    
    if args.command == "preload":
        if not args.models:
            args.models = list(ModelConfig.MODELS.keys())
        await cache_manager.preload_models(args.models)
    
    elif args.command == "stats":
        stats = cache_manager.get_cache_stats()
        print(json.dumps(stats, indent=2))
    
    elif args.command == "cleanup":
        await cache_manager.cleanup_cache(args.max_size)
    
    elif args.command == "test":
        loader = ExternalizedModelLoader()
        model = await loader.load_model("clip-vit")
        print(f"Successfully loaded model: {type(model)}")
        await loader.unload_model("clip-vit")

if __name__ == "__main__":
    asyncio.run(main())