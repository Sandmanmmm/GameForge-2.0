#!/usr/bin/env python3
"""
GameForge AI Production Model Download System
Downloads and caches models from MinIO at runtime
"""

import os
import sys
import json
import hashlib
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

import aiohttp
import aiofiles
from minio import Minio
from minio.error import S3Error
import torch
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "model_downloader", "message": "%(message)s", "correlation_id": "%(correlation_id)s"}',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/model_download.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

class ModelDownloader:
    """Production-grade model download and caching system"""
    
    def __init__(self):
        self.minio_endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
        self.minio_access_key = os.getenv('MINIO_ACCESS_KEY')
        self.minio_secret_key = os.getenv('MINIO_SECRET_KEY')
        self.model_bucket = os.getenv('MODEL_BUCKET', 'gameforge-models')
        self.cache_dir = Path(os.getenv('MODEL_CACHE_DIR', '/app/models'))
        self.manifest_file = self.cache_dir / 'manifest.json'
        self.correlation_id = os.getenv('REQUEST_ID', f"download-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        
        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize MinIO client
        self.minio_client = Minio(
            self.minio_endpoint,
            access_key=self.minio_access_key,
            secret_key=self.minio_secret_key,
            secure=False  # Set to True for HTTPS
        )
        
        # Model configuration
        self.model_config = {
            'stable-diffusion-xl': {
                'files': [
                    'sd_xl_base_1.0.safetensors',
                    'sd_xl_refiner_1.0.safetensors',
                    'tokenizer/tokenizer.json',
                    'scheduler/scheduler_config.json'
                ],
                'total_size_gb': 6.9,
                'priority': 1,
                'required': True
            },
            'clip-vision': {
                'files': [
                    'pytorch_model.bin',
                    'config.json'
                ],
                'total_size_gb': 1.7,
                'priority': 2,
                'required': True
            },
            'controlnet': {
                'files': [
                    'controlnet_canny.safetensors',
                    'controlnet_depth.safetensors'
                ],
                'total_size_gb': 2.8,
                'priority': 3,
                'required': False
            }
        }
        
        # Add correlation ID to logger context
        old_factory = logging.getLogRecordFactory()
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.correlation_id = self.correlation_id
            return record
        logging.setLogRecordFactory(record_factory)
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check available system resources before download"""
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        resources = {
            'memory_available_gb': round(memory.available / (1024**3), 2),
            'disk_free_gb': round(disk.free / (1024**3), 2),
            'cpu_count': psutil.cpu_count(),
            'gpu_available': torch.cuda.is_available(),
            'gpu_count': torch.cuda.device_count() if torch.cuda.is_available() else 0
        }
        
        logger.info(f"System resources check completed: {json.dumps(resources)}")
        return resources
    
    async def validate_model_integrity(self, file_path: Path, expected_checksum: Optional[str] = None) -> bool:
        """Validate downloaded model file integrity"""
        if not file_path.exists():
            return False
        
        # Check file size is reasonable (not empty, not too small)
        file_size = file_path.stat().st_size
        if file_size < 1024:  # Less than 1KB is suspicious
            logger.warning(f"Model file {file_path} is suspiciously small: {file_size} bytes")
            return False
        
        # If we have a checksum, validate it
        if expected_checksum:
            sha256_hash = hashlib.sha256()
            async with aiofiles.open(file_path, 'rb') as f:
                async for chunk in f:
                    sha256_hash.update(chunk)
            
            calculated_checksum = sha256_hash.hexdigest()
            if calculated_checksum != expected_checksum:
                logger.error(f"Checksum mismatch for {file_path}: expected {expected_checksum}, got {calculated_checksum}")
                return False
        
        # For torch models, try to load metadata
        if file_path.suffix in ['.safetensors', '.bin', '.pt', '.pth']:
            try:
                if file_path.suffix == '.safetensors':
                    # Basic safetensors validation
                    with open(file_path, 'rb') as f:
                        header_size = int.from_bytes(f.read(8), 'little')
                        if header_size > 0 and header_size < file_size:
                            logger.info(f"Safetensors file {file_path} appears valid")
                            return True
                else:
                    # Try loading as torch tensor
                    torch.load(file_path, map_location='cpu', weights_only=True)
                    logger.info(f"Torch model file {file_path} validated successfully")
                    return True
            except Exception as e:
                logger.error(f"Model validation failed for {file_path}: {e}")
                return False
        
        return True
    
    async def download_file(self, object_name: str, local_path: Path, progress_callback=None) -> bool:
        """Download a single file from MinIO with progress tracking"""
        try:
            # Get object info for progress tracking
            stat = self.minio_client.stat_object(self.model_bucket, object_name)
            total_size = stat.size
            
            logger.info(f"Starting download: {object_name} ({total_size / (1024**2):.2f} MB)")
            
            # Download with progress tracking
            downloaded = 0
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(local_path, 'wb') as f:
                try:
                    data = self.minio_client.get_object(self.model_bucket, object_name)
                    for chunk in data.stream(chunk_size=8192):
                        await f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback:
                            progress = (downloaded / total_size) * 100
                            await progress_callback(object_name, progress, downloaded, total_size)
                finally:
                    data.close()
                    data.release_conn()
            
            # Validate downloaded file
            if await self.validate_model_integrity(local_path):
                logger.info(f"Successfully downloaded and validated: {object_name}")
                return True
            else:
                logger.error(f"Downloaded file failed validation: {object_name}")
                local_path.unlink(missing_ok=True)
                return False
                
        except S3Error as e:
            logger.error(f"MinIO error downloading {object_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading {object_name}: {e}")
            return False
    
    async def progress_callback(self, object_name: str, progress: float, downloaded: int, total: int):
        """Progress callback for download tracking"""
        if int(progress) % 10 == 0 or progress >= 100:  # Log every 10%
            logger.info(f"Download progress for {object_name}: {progress:.1f}% ({downloaded}/{total} bytes)")
    
    async def download_model(self, model_name: str) -> bool:
        """Download a complete model with all its files"""
        if model_name not in self.model_config:
            logger.error(f"Unknown model: {model_name}")
            return False
        
        config = self.model_config[model_name]
        model_dir = self.cache_dir / model_name
        
        logger.info(f"Starting download for model: {model_name}")
        
        # Check if model already exists and is valid
        if await self.is_model_cached(model_name):
            logger.info(f"Model {model_name} already cached and valid")
            return True
        
        # Create model directory
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Download all files for this model
        success_count = 0
        for file_name in config['files']:
            object_name = f"{model_name}/{file_name}"
            local_path = model_dir / file_name
            
            if await self.download_file(object_name, local_path, self.progress_callback):
                success_count += 1
            else:
                logger.error(f"Failed to download {file_name} for model {model_name}")
        
        # Check if all required files downloaded successfully
        if success_count == len(config['files']):
            # Update manifest
            await self.update_manifest(model_name)
            logger.info(f"Successfully downloaded model: {model_name}")
            return True
        else:
            logger.error(f"Model download incomplete: {model_name} ({success_count}/{len(config['files'])} files)")
            # Clean up partial download
            if model_dir.exists():
                import shutil
                shutil.rmtree(model_dir)
            return False
    
    async def is_model_cached(self, model_name: str) -> bool:
        """Check if model is already cached and valid"""
        model_dir = self.cache_dir / model_name
        if not model_dir.exists():
            return False
        
        config = self.model_config[model_name]
        
        # Check all files exist and are valid
        for file_name in config['files']:
            file_path = model_dir / file_name
            if not file_path.exists():
                logger.info(f"Missing file for {model_name}: {file_name}")
                return False
            
            if not await self.validate_model_integrity(file_path):
                logger.info(f"Invalid file for {model_name}: {file_name}")
                return False
        
        return True
    
    async def update_manifest(self, model_name: str):
        """Update the model manifest with download info"""
        manifest = {}
        if self.manifest_file.exists():
            async with aiofiles.open(self.manifest_file, 'r') as f:
                content = await f.read()
                manifest = json.loads(content)
        
        manifest[model_name] = {
            'downloaded_at': datetime.now().isoformat(),
            'version': '1.0',
            'files': self.model_config[model_name]['files'],
            'correlation_id': self.correlation_id
        }
        
        async with aiofiles.open(self.manifest_file, 'w') as f:
            await f.write(json.dumps(manifest, indent=2))
    
    async def download_required_models(self) -> bool:
        """Download all required models for production startup"""
        logger.info("Starting required model download for production startup")
        
        # Check system resources
        resources = await self.check_system_resources()
        
        # Calculate total download size
        total_size_gb = sum(
            config['total_size_gb'] 
            for config in self.model_config.values() 
            if config['required']
        )
        
        if resources['disk_free_gb'] < total_size_gb * 1.2:  # 20% buffer
            logger.error(f"Insufficient disk space: need {total_size_gb:.1f}GB, have {resources['disk_free_gb']:.1f}GB")
            return False
        
        # Download models in priority order
        required_models = [
            (name, config) for name, config in self.model_config.items() 
            if config['required']
        ]
        required_models.sort(key=lambda x: x[1]['priority'])
        
        success_count = 0
        for model_name, config in required_models:
            if await self.download_model(model_name):
                success_count += 1
            else:
                logger.error(f"Failed to download required model: {model_name}")
                if config['priority'] == 1:  # Critical model
                    return False
        
        logger.info(f"Model download completed: {success_count}/{len(required_models)} models successfully downloaded")
        return success_count == len(required_models)
    
    async def cleanup_old_models(self, max_age_days: int = 30):
        """Clean up old model versions to save disk space"""
        logger.info(f"Starting model cleanup (older than {max_age_days} days)")
        
        if not self.manifest_file.exists():
            return
        
        async with aiofiles.open(self.manifest_file, 'r') as f:
            content = await f.read()
            manifest = json.loads(content)
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for model_name, info in manifest.items():
            download_date = datetime.fromisoformat(info['downloaded_at'])
            if download_date < cutoff_date:
                model_dir = self.cache_dir / model_name
                if model_dir.exists():
                    import shutil
                    shutil.rmtree(model_dir)
                    logger.info(f"Cleaned up old model: {model_name}")
                    del manifest[model_name]
        
        # Update manifest
        async with aiofiles.open(self.manifest_file, 'w') as f:
            await f.write(json.dumps(manifest, indent=2))

async def main():
    """Main function for standalone model download"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GameForge Model Downloader')
    parser.add_argument('--model', help='Specific model to download')
    parser.add_argument('--required-only', action='store_true', help='Download only required models')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old models')
    parser.add_argument('--validate', action='store_true', help='Validate existing models')
    
    args = parser.parse_args()
    
    downloader = ModelDownloader()
    
    try:
        if args.cleanup:
            await downloader.cleanup_old_models()
        elif args.validate:
            # Validate all cached models
            for model_name in downloader.model_config.keys():
                is_valid = await downloader.is_model_cached(model_name)
                print(f"Model {model_name}: {'✅ Valid' if is_valid else '❌ Invalid/Missing'}")
        elif args.model:
            success = await downloader.download_model(args.model)
            sys.exit(0 if success else 1)
        else:
            # Download required models (default behavior)
            success = await downloader.download_required_models()
            sys.exit(0 if success else 1)
            
    except Exception as e:
        logger.error(f"Model download failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())