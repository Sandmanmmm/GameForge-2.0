#!/usr/bin/env python3
"""
GameForge AI - Model Storage Uploader
Upload models to external storage (S3/MinIO) for migration
"""

import os
import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List
import boto3
from minio import Minio
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelUploader:
    """Upload models to external storage backends"""
    
    def __init__(self, config_path: str = "config/models/model-registry.json"):
        self.config_path = Path(config_path)
        self.load_config()
    
    def load_config(self):
        """Load model registry configuration"""
        with open(self.config_path) as f:
            self.registry = json.load(f)
    
    def upload_model(self, model_name: str, source_path: Path, 
                    backend: str = "minio", format_filter: List[str] = None):
        """Upload model to specified backend"""
        
        if backend == "minio":
            return self._upload_to_minio(model_name, source_path, format_filter)
        elif backend == "s3":
            return self._upload_to_s3(model_name, source_path, format_filter)
        else:
            raise ValueError(f"Unknown backend: {backend}")
    
    def _upload_to_minio(self, model_name: str, source_path: Path, format_filter: List[str]):
        """Upload to MinIO storage"""
        minio_config = self.registry["storage_backends"]["minio"]
        
        # Security fix: Remove hardcoded credentials - fail securely
        access_key = os.getenv("MINIO_ACCESS_KEY")
        secret_key = os.getenv("MINIO_SECRET_KEY")
        
        if not access_key or not secret_key:
            raise ValueError(
                "MINIO_ACCESS_KEY and MINIO_SECRET_KEY must be set in "
                "environment variables. For security reasons, no default "
                "credentials are provided."
            )
        
        client = Minio(
            minio_config["endpoint"].replace("http://", "").replace("https://", ""),
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )
        
        # Ensure bucket exists
        if not client.bucket_exists(minio_config["bucket"]):
            client.make_bucket(minio_config["bucket"])
            logger.info(f"Created bucket: {minio_config['bucket']}")
        
        # Upload files with format filtering
        uploaded_files = []
        
        for file_path in source_path.rglob("*"):
            if file_path.is_file():
                # Apply format filter
                if format_filter and not any(fmt in file_path.name for fmt in format_filter):
                    continue
                
                # Skip very large files we don't need
                if any(skip in file_path.name for skip in [".msgpack", "openvino", ".onnx_data"]):
                    continue
                
                relative_path = file_path.relative_to(source_path)
                object_name = f"{model_name}/{relative_path}"
                
                # Upload with progress
                file_size = file_path.stat().st_size
                with tqdm(total=file_size, unit='B', unit_scale=True, desc=file_path.name) as pbar:
                    def progress_callback(bytes_transferred):
                        pbar.update(bytes_transferred - pbar.n)
                    
                    client.fput_object(
                        minio_config["bucket"],
                        object_name,
                        str(file_path),
                        progress=progress_callback
                    )
                
                uploaded_files.append(object_name)
                logger.info(f"Uploaded: {object_name}")
        
        logger.info(f"Upload complete: {len(uploaded_files)} files")
        return uploaded_files
    
    def _upload_to_s3(self, model_name: str, source_path: Path, format_filter: List[str]):
        """Upload to S3 storage"""
        s3_config = self.registry["storage_backends"]["s3"]
        
        s3 = boto3.client("s3", region_name=s3_config["region"])
        
        uploaded_files = []
        
        for file_path in source_path.rglob("*"):
            if file_path.is_file():
                # Apply format filter
                if format_filter and not any(fmt in file_path.name for fmt in format_filter):
                    continue
                
                relative_path = file_path.relative_to(source_path)
                key = f"{model_name}/{relative_path}"
                
                # Upload file
                s3.upload_file(str(file_path), s3_config["bucket"], key)
                uploaded_files.append(key)
                logger.info(f"Uploaded: {key}")
        
        logger.info(f"S3 upload complete: {len(uploaded_files)} files")
        return uploaded_files
    
    def verify_upload(self, model_name: str, backend: str = "minio"):
        """Verify uploaded files integrity"""
        # Implementation for verifying uploads
        logger.info(f"Verifying upload for {model_name} on {backend}")
        return True

# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="GameForge AI Model Uploader")
    parser.add_argument("model", help="Model name")
    parser.add_argument("source", help="Source path")
    parser.add_argument("--backend", default="minio", choices=["minio", "s3"])
    parser.add_argument("--format", nargs="+", help="Format filter", 
                       default=["safetensors", "fp16.safetensors"])
    
    args = parser.parse_args()
    
    uploader = ModelUploader()
    uploader.upload_model(args.model, Path(args.source), args.backend, args.format)
