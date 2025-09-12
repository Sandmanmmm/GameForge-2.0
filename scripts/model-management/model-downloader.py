#!/usr/bin/env python3
"""
GameForge AI - Smart Model Downloader
On-demand model downloading with caching and format optimization
"""

import os
import json
import requests
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional
import boto3
from minio import Minio
import huggingface_hub as hf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SmartModelDownloader:
    """Smart model downloader with multiple backends"""
    
    def __init__(self, config_path: str = "config/models/model-registry.json"):
        self.config_path = Path(config_path)
        self.load_config()
        self.setup_cache()
    
    def load_config(self):
        """Load model registry configuration"""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self.registry = json.load(f)
        else:
            raise FileNotFoundError(f"Model registry not found: {self.config_path}")
        
        self.cache_dir = Path(self.registry.get("download_cache", "/tmp/model-cache"))
        self.production_formats = self.registry.get("production_formats", ["safetensors", "fp16.safetensors"])
    
    def setup_cache(self):
        """Setup local model cache directory"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("HF_HOME", str(self.cache_dir / "huggingface"))
        
    def download_model(self, model_name: str, format_filter: Optional[List[str]] = None, 
                      force_download: bool = False) -> Path:
        """Download model with smart caching and format filtering"""
        
        if model_name not in self.registry["models"]:
            raise ValueError(f"Model {model_name} not found in registry")
        
        model_info = self.registry["models"][model_name]
        cache_path = self.cache_dir / model_name
        
        # Check if already cached
        if cache_path.exists() and not force_download:
            logger.info(f"Model {model_name} already cached at {cache_path}")
            return cache_path
        
        logger.info(f"Downloading model: {model_name}")
        
        # Use format filter or default to production formats
        allowed_formats = format_filter or self.production_formats
        
        # Try different download methods
        if self._try_external_storage(model_name, cache_path):
            logger.info("Downloaded from external storage")
        elif self._try_huggingface_download(model_info, cache_path, allowed_formats):
            logger.info("Downloaded from Hugging Face")
        else:
            raise RuntimeError(f"Failed to download model {model_name}")
        
        return cache_path
    
    def _try_external_storage(self, model_name: str, cache_path: Path) -> bool:
        """Try downloading from S3/MinIO storage"""
        try:
            # Try MinIO first (local/self-hosted)
            if self._download_from_minio(model_name, cache_path):
                return True
            
            # Try S3 as fallback
            if self._download_from_s3(model_name, cache_path):
                return True
                
        except Exception as e:
            logger.warning(f"External storage download failed: {e}")
        
        return False
    
    def _download_from_minio(self, model_name: str, cache_path: Path) -> bool:
        """Download from MinIO storage"""
        minio_config = self.registry["storage_backends"]["minio"]
        
        try:
            client = Minio(
                minio_config["endpoint"].replace("http://", "").replace("https://", ""),
                access_key=os.getenv("MINIO_ACCESS_KEY", minio_config["access_key"]),
                secret_key=os.getenv("MINIO_SECRET_KEY", minio_config["secret_key"]),
                secure=False
            )
            
            # List and download model files
            objects = client.list_objects(minio_config["bucket"], prefix=f"{model_name}/", recursive=True)
            
            for obj in objects:
                local_path = cache_path / obj.object_name.replace(f"{model_name}/", "")
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                client.fget_object(minio_config["bucket"], obj.object_name, str(local_path))
                logger.debug(f"Downloaded: {obj.object_name}")
            
            return True
            
        except Exception as e:
            logger.warning(f"MinIO download failed: {e}")
            return False
    
    def _download_from_s3(self, model_name: str, cache_path: Path) -> bool:
        """Download from S3 storage"""
        s3_config = self.registry["storage_backends"]["s3"]
        
        try:
            s3 = boto3.client("s3", region_name=s3_config["region"])
            
            # List and download model files
            response = s3.list_objects_v2(Bucket=s3_config["bucket"], Prefix=f"{model_name}/")
            
            if "Contents" not in response:
                return False
            
            for obj in response["Contents"]:
                key = obj["Key"]
                local_path = cache_path / key.replace(f"{model_name}/", "")
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                s3.download_file(s3_config["bucket"], key, str(local_path))
                logger.debug(f"Downloaded: {key}")
            
            return True
            
        except Exception as e:
            logger.warning(f"S3 download failed: {e}")
            return False
    
    def _try_huggingface_download(self, model_info: Dict, cache_path: Path, 
                                 allowed_formats: List[str]) -> bool:
        """Download from Hugging Face Hub with format filtering"""
        try:
            repo_id = self._extract_repo_id(model_info["download_url"])
            
            # Download with format filtering
            hf.snapshot_download(
                repo_id=repo_id,
                cache_dir=str(cache_path.parent),
                local_dir=str(cache_path),
                ignore_patterns=self._get_ignore_patterns(allowed_formats)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Hugging Face download failed: {e}")
            return False
    
    def _extract_repo_id(self, url: str) -> str:
        """Extract repo ID from Hugging Face URL"""
        # Extract from URL like https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
        parts = url.replace("https://huggingface.co/", "").split("/")
        return "/".join(parts[:2])
    
    def _get_ignore_patterns(self, allowed_formats: List[str]) -> List[str]:
        """Generate ignore patterns for unwanted formats"""
        # Default patterns to ignore large files we don't need
        ignore = [
            "*.msgpack",  # Flax format
            "*openvino*",  # OpenVINO format
            "*.onnx_data", # Large ONNX data files
        ]
        
        # If we only want safetensors, ignore pytorch
        if "safetensors" in allowed_formats and "pytorch" not in str(allowed_formats):
            ignore.extend(["*pytorch_model*", "*.bin"])
        
        # If we only want fp16, ignore full precision
        if "fp16" in str(allowed_formats):
            ignore.extend(["diffusion_pytorch_model.safetensors"])
        
        return ignore
    
    def get_model_path(self, model_name: str) -> Optional[Path]:
        """Get cached model path if available"""
        cache_path = self.cache_dir / model_name
        return cache_path if cache_path.exists() else None
    
    def cleanup_cache(self, keep_days: int = 7):
        """Clean up old cached models"""
        import time
        cutoff = time.time() - (keep_days * 24 * 60 * 60)
        
        for model_dir in self.cache_dir.iterdir():
            if model_dir.is_dir() and model_dir.stat().st_mtime < cutoff:
                logger.info(f"Cleaning up old cache: {model_dir}")
                shutil.rmtree(model_dir)

# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="GameForge AI Model Downloader")
    parser.add_argument("model", help="Model name to download")
    parser.add_argument("--force", action="store_true", help="Force re-download")
    parser.add_argument("--format", nargs="+", help="Allowed formats", 
                       default=["safetensors", "fp16.safetensors"])
    parser.add_argument("--cleanup", type=int, help="Cleanup cache older than N days")
    
    args = parser.parse_args()
    
    downloader = SmartModelDownloader()
    
    if args.cleanup:
        downloader.cleanup_cache(args.cleanup)
    else:
        model_path = downloader.download_model(args.model, args.format, args.force)
        print(f"Model available at: {model_path}")
