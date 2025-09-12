#!/usr/bin/env python3
"""
GameForge AI External Storage Management System
Handles cloud storage integration and migration from Docker volumes
"""

import os
import sys
import json
import logging
import asyncio
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

import boto3
from azure.storage.blob import BlobServiceClient
from google.cloud import storage as gcs
import psycopg2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "external_storage", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class ExternalStorageManager:
    """Manages external storage backends and migration from Docker volumes"""
    
    def __init__(self):
        self.cloud_provider = os.getenv('CLOUD_PROVIDER', 'azure').lower()
        self.storage_config = self._load_storage_config()
    
    def _load_storage_config(self) -> Dict[str, Any]:
        """Load storage configuration from environment and config files"""
        config = {
            'database': {
                'url': os.getenv('EXTERNAL_DATABASE_URL'),
                'ssl_mode': os.getenv('DATABASE_SSL_MODE', 'require')
            },
            'redis': {
                'url': os.getenv('EXTERNAL_REDIS_URL'),
                'ssl': os.getenv('REDIS_SSL', 'true').lower() == 'true'
            },
            'object_storage': {
                'provider': self.cloud_provider,
                'endpoint': os.getenv('EXTERNAL_STORAGE_ENDPOINT'),
                'access_key': os.getenv('EXTERNAL_STORAGE_ACCESS_KEY'),
                'secret_key': os.getenv('EXTERNAL_STORAGE_SECRET_KEY'),
                'region': os.getenv('EXTERNAL_STORAGE_REGION', 'us-east-1')
            },
            'buckets': {
                'models': os.getenv('STORAGE_BUCKET_MODELS', 'gameforge-models'),
                'content': os.getenv('STORAGE_BUCKET_CONTENT', 'gameforge-content'),
                'backups': os.getenv('STORAGE_BUCKET_BACKUPS', 'gameforge-backups'),
                'logs': os.getenv('STORAGE_BUCKET_LOGS', 'gameforge-logs')
            },
            'local_paths': {
                'models': os.getenv('LOCAL_MODEL_PATH', '/app/models'),
                'content': os.getenv('LOCAL_CONTENT_PATH', '/app/content'),
                'logs': os.getenv('LOCAL_LOG_PATH', '/app/logs'),
                'temp': os.getenv('LOCAL_TEMP_PATH', '/tmp/gameforge')
            }
        }
        return config
    
    def get_object_storage_client(self):
        """Get cloud storage client based on provider"""
        provider = self.storage_config['object_storage']['provider']
        
        if provider == 'aws':
            return boto3.client(
                's3',
                aws_access_key_id=self.storage_config['object_storage']['access_key'],
                aws_secret_access_key=self.storage_config['object_storage']['secret_key'],
                region_name=self.storage_config['object_storage']['region']
            )
        elif provider == 'azure':
            connection_string = f"DefaultEndpointsProtocol=https;AccountName={self.storage_config['object_storage']['access_key']};AccountKey={self.storage_config['object_storage']['secret_key']};EndpointSuffix=core.windows.net"
            return BlobServiceClient.from_connection_string(connection_string)
        elif provider == 'gcp':
            return gcs.Client.from_service_account_json(
                self.storage_config['object_storage']['service_account_path']
            )
        elif provider == 'minio':
            from minio import Minio
            return Minio(
                self.storage_config['object_storage']['endpoint'],
                access_key=self.storage_config['object_storage']['access_key'],
                secret_key=self.storage_config['object_storage']['secret_key'],
                secure=True
            )
        else:
            raise ValueError(f"Unsupported storage provider: {provider}")
    
    async def test_database_connection(self) -> bool:
        """Test external database connectivity"""
        try:
            import asyncpg
            conn = await asyncpg.connect(self.storage_config['database']['url'])
            await conn.execute('SELECT 1')
            await conn.close()
            logger.info("✅ External database connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ External database connection failed: {e}")
            return False
    
    async def test_redis_connection(self) -> bool:
        """Test external Redis connectivity"""
        try:
            import redis.asyncio as redis
            client = redis.from_url(self.storage_config['redis']['url'])
            await client.ping()
            await client.close()
            logger.info("✅ External Redis connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ External Redis connection failed: {e}")
            return False
    
    def test_object_storage_connection(self) -> bool:
        """Test object storage connectivity"""
        try:
            client = self.get_object_storage_client()
            provider = self.storage_config['object_storage']['provider']
            
            if provider == 'aws':
                client.head_bucket(Bucket=self.storage_config['buckets']['models'])
            elif provider == 'azure':
                container_client = client.get_container_client(self.storage_config['buckets']['models'])
                container_client.get_container_properties()
            elif provider == 'gcp':
                bucket = client.bucket(self.storage_config['buckets']['models'])
                bucket.reload()
            elif provider == 'minio':
                client.bucket_exists(self.storage_config['buckets']['models'])
            
            logger.info("✅ Object storage connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Object storage connection failed: {e}")
            return False
    
    def ensure_buckets_exist(self) -> bool:
        """Ensure all required storage buckets exist"""
        try:
            client = self.get_object_storage_client()
            provider = self.storage_config['object_storage']['provider']
            buckets = self.storage_config['buckets']
            
            for bucket_name in buckets.values():
                logger.info(f"Checking bucket: {bucket_name}")
                
                if provider == 'aws':
                    try:
                        client.head_bucket(Bucket=bucket_name)
                    except client.exceptions.NoSuchBucket:
                        client.create_bucket(Bucket=bucket_name)
                        logger.info(f"Created S3 bucket: {bucket_name}")
                
                elif provider == 'azure':
                    try:
                        container_client = client.get_container_client(bucket_name)
                        container_client.get_container_properties()
                    except Exception:
                        container_client.create_container()
                        logger.info(f"Created Azure container: {bucket_name}")
                
                elif provider == 'gcp':
                    try:
                        bucket = client.bucket(bucket_name)
                        bucket.reload()
                    except Exception:
                        bucket = client.create_bucket(bucket_name)
                        logger.info(f"Created GCS bucket: {bucket_name}")
                
                elif provider == 'minio':
                    if not client.bucket_exists(bucket_name):
                        client.make_bucket(bucket_name)
                        logger.info(f"Created MinIO bucket: {bucket_name}")
            
            logger.info("✅ All storage buckets verified/created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to ensure buckets exist: {e}")
            return False
    
    def migrate_docker_volumes(self, docker_volume_path: str = "/var/lib/docker/volumes") -> bool:
        """Migrate data from Docker volumes to external storage"""
        try:
            volume_path = Path(docker_volume_path)
            if not volume_path.exists():
                logger.warning(f"Docker volume path not found: {docker_volume_path}")
                return True  # Not an error in containerized environments
            
            # Map Docker volumes to external storage
            volume_mappings = {
                'gameforge_model_cache': 'models',
                'gameforge_generated_content': 'content',
                'gameforge_logs': 'logs',
                'gameforge_postgres_data': 'database_backup',
                'gameforge_redis_data': 'redis_backup'
            }
            
            client = self.get_object_storage_client()
            provider = self.storage_config['object_storage']['provider']
            
            for volume_name, storage_type in volume_mappings.items():
                volume_data_path = volume_path / volume_name / "_data"
                
                if not volume_data_path.exists():
                    logger.info(f"Volume not found, skipping: {volume_name}")
                    continue
                
                logger.info(f"Migrating volume: {volume_name} -> {storage_type}")
                
                # Upload files to appropriate bucket
                bucket_name = self.storage_config['buckets'].get(storage_type.split('_')[0], 
                                                               self.storage_config['buckets']['content'])
                
                for file_path in volume_data_path.rglob('*'):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(volume_data_path)
                        object_key = f"{storage_type}/{relative_path}"
                        
                        if provider == 'aws':
                            client.upload_file(str(file_path), bucket_name, object_key)
                        elif provider == 'azure':
                            blob_client = client.get_blob_client(container=bucket_name, blob=object_key)
                            with open(file_path, 'rb') as data:
                                blob_client.upload_blob(data, overwrite=True)
                        # Add other providers as needed
                        
                        logger.info(f"Uploaded: {relative_path}")
            
            logger.info("✅ Docker volume migration completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Docker volume migration failed: {e}")
            return False
    
    def setup_local_cache_directories(self) -> bool:
        """Set up local cache directories for external storage"""
        try:
            local_paths = self.storage_config['local_paths']
            
            for path_type, path in local_paths.items():
                path_obj = Path(path)
                path_obj.mkdir(parents=True, exist_ok=True)
                
                # Set appropriate permissions
                if path_type in ['models', 'content']:
                    os.chmod(path, 0o755)  # Read/write for owner, read for others
                elif path_type == 'logs':
                    os.chmod(path, 0o755)  # Read/write for owner, read for others
                elif path_type == 'temp':
                    os.chmod(path, 0o777)  # Full access for temporary files
                
                logger.info(f"✅ Created local cache directory: {path}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup local cache directories: {e}")
            return False
    
    def generate_storage_config_file(self) -> bool:
        """Generate configuration files for external storage"""
        try:
            config_dir = Path("/app/config")
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate storage configuration
            storage_config = {
                "external_storage": {
                    "enabled": True,
                    "provider": self.storage_config['object_storage']['provider'],
                    "database": {
                        "url": self.storage_config['database']['url'],
                        "ssl_mode": self.storage_config['database']['ssl_mode']
                    },
                    "redis": {
                        "url": self.storage_config['redis']['url'],
                        "ssl": self.storage_config['redis']['ssl']
                    },
                    "object_storage": {
                        "endpoint": self.storage_config['object_storage']['endpoint'],
                        "region": self.storage_config['object_storage']['region'],
                        "buckets": self.storage_config['buckets']
                    },
                    "local_cache": self.storage_config['local_paths']
                }
            }
            
            config_file = config_dir / "external-storage.json"
            with open(config_file, 'w') as f:
                json.dump(storage_config, f, indent=2)
            
            logger.info(f"✅ Generated storage config: {config_file}")
            
            # Generate Docker Compose override
            self._generate_docker_compose_override()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to generate storage config: {e}")
            return False
    
    def _generate_docker_compose_override(self):
        """Generate Docker Compose override for external storage"""
        override_content = f"""version: '3.8'

# External Storage Override
# This file configures GameForge to use external storage backends

services:
  gameforge-app:
    environment:
      # External Database
      DATABASE_URL: "{self.storage_config['database']['url']}"
      DATABASE_SSL_MODE: "{self.storage_config['database']['ssl_mode']}"
      
      # External Redis
      REDIS_URL: "{self.storage_config['redis']['url']}"
      REDIS_SSL: "{str(self.storage_config['redis']['ssl']).lower()}"
      
      # External Object Storage
      EXTERNAL_STORAGE_PROVIDER: "{self.storage_config['object_storage']['provider']}"
      EXTERNAL_STORAGE_ENDPOINT: "{self.storage_config['object_storage']['endpoint']}"
      EXTERNAL_STORAGE_REGION: "{self.storage_config['object_storage']['region']}"
      
      # Storage Buckets
      STORAGE_BUCKET_MODELS: "{self.storage_config['buckets']['models']}"
      STORAGE_BUCKET_CONTENT: "{self.storage_config['buckets']['content']}"
      STORAGE_BUCKET_BACKUPS: "{self.storage_config['buckets']['backups']}"
      STORAGE_BUCKET_LOGS: "{self.storage_config['buckets']['logs']}"
      
      # Local Cache Paths
      LOCAL_MODEL_PATH: "{self.storage_config['local_paths']['models']}"
      LOCAL_CONTENT_PATH: "{self.storage_config['local_paths']['content']}"
      LOCAL_LOG_PATH: "{self.storage_config['local_paths']['logs']}"
      LOCAL_TEMP_PATH: "{self.storage_config['local_paths']['temp']}"
      
      # External Storage Enabled
      EXTERNAL_STORAGE_ENABLED: "true"
    
    volumes:
      # External storage mount points
      - type: bind
        source: {self.storage_config['local_paths']['models']}
        target: /app/models
      - type: bind
        source: {self.storage_config['local_paths']['content']}
        target: /app/content
      - type: bind
        source: {self.storage_config['local_paths']['logs']}
        target: /app/logs
      - type: bind
        source: {self.storage_config['local_paths']['temp']}
        target: /tmp/gameforge

  # Disable internal services in favor of external
  postgres:
    deploy:
      replicas: 0  # Use external database

  redis:
    deploy:
      replicas: 0  # Use external Redis

# Remove internal volumes
volumes: {{}}
"""
        
        override_file = Path("docker-compose.external-storage.yml")
        with open(override_file, 'w') as f:
            f.write(override_content)
        
        logger.info(f"✅ Generated Docker Compose override: {override_file}")
    
    async def validate_external_storage_setup(self) -> Dict[str, bool]:
        """Validate complete external storage setup"""
        logger.info("🔍 Validating external storage setup...")
        
        results = {
            'database_connection': await self.test_database_connection(),
            'redis_connection': await self.test_redis_connection(),
            'object_storage_connection': self.test_object_storage_connection(),
            'buckets_exist': self.ensure_buckets_exist(),
            'local_directories': self.setup_local_cache_directories(),
            'config_files': self.generate_storage_config_file()
        }
        
        all_passed = all(results.values())
        
        logger.info("📊 External Storage Validation Results:")
        for check, passed in results.items():
            status = "✅" if passed else "❌"
            logger.info(f"  {status} {check.replace('_', ' ').title()}")
        
        if all_passed:
            logger.info("🎉 All external storage validations passed!")
        else:
            logger.error("❌ Some external storage validations failed")
        
        return results

async def main():
    """Main function for external storage management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GameForge External Storage Manager')
    parser.add_argument('--validate', action='store_true', help='Validate external storage setup')
    parser.add_argument('--migrate-volumes', help='Migrate from Docker volumes (path to volumes)')
    parser.add_argument('--setup-cache', action='store_true', help='Setup local cache directories')
    parser.add_argument('--generate-config', action='store_true', help='Generate configuration files')
    
    args = parser.parse_args()
    
    manager = ExternalStorageManager()
    
    try:
        if args.validate:
            results = await manager.validate_external_storage_setup()
            sys.exit(0 if all(results.values()) else 1)
        elif args.migrate_volumes:
            success = manager.migrate_docker_volumes(args.migrate_volumes)
            sys.exit(0 if success else 1)
        elif args.setup_cache:
            success = manager.setup_local_cache_directories()
            sys.exit(0 if success else 1)
        elif args.generate_config:
            success = manager.generate_storage_config_file()
            sys.exit(0 if success else 1)
        else:
            # Default: full validation
            results = await manager.validate_external_storage_setup()
            sys.exit(0 if all(results.values()) else 1)
            
    except Exception as e:
        logger.error(f"External storage operation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())