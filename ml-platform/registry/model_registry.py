# MLflow Model Registry Configuration
# Production-ready setup with PostgreSQL backend and S3 artifact storage

import os
import mlflow
import mlflow.tracking
from mlflow.tracking import MlflowClient
from mlflow.models import infer_signature
import logging
from typing import Dict, List, Optional, Tuple
import psycopg2
from urllib.parse import urlparse
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class GameForgeModelRegistry:
    """
    Enterprise MLflow Model Registry for GameForge AI Platform
    
    Features:
    - PostgreSQL backend for metadata
    - S3 artifact storage with versioning
    - Model lifecycle management
    - Security integration with existing hardened infrastructure
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._load_config()
        self._setup_mlflow()
        self.client = MlflowClient(tracking_uri=self.config['tracking_uri'])
        self._validate_connections()
    
    def _load_config(self) -> Dict:
        """Load configuration from environment or defaults"""
        return {
            'tracking_uri': os.getenv(
                'MLFLOW_TRACKING_URI', 
                'postgresql://mlflow:mlflow@localhost:5432/mlflow'
            ),
            's3_bucket': os.getenv('MLFLOW_S3_BUCKET', 'gameforge-ml-artifacts'),
            's3_region': os.getenv('AWS_REGION', 'us-east-1'),
            'registry_name': os.getenv('ML_REGISTRY_NAME', 'gameforge-models'),
            'security_enabled': os.getenv('ML_SECURITY_ENABLED', 'true').lower() == 'true',
            'encryption_enabled': os.getenv('ML_ENCRYPTION_ENABLED', 'true').lower() == 'true'
        }
    
    def _setup_mlflow(self):
        """Configure MLflow with production settings"""
        # Set tracking URI
        mlflow.set_tracking_uri(self.config['tracking_uri'])
        
        # Configure S3 artifact store
        os.environ['MLFLOW_S3_ENDPOINT_URL'] = f"https://s3.{self.config['s3_region']}.amazonaws.com"
        os.environ['AWS_DEFAULT_REGION'] = self.config['s3_region']
        
        # Security configurations
        if self.config['security_enabled']:
            os.environ['MLFLOW_TRACKING_INSECURE_TLS'] = 'false'
            os.environ['MLFLOW_ENABLE_SYSTEM_METRICS_LOGGING'] = 'true'
    
    def _validate_connections(self):
        """Validate database and S3 connections"""
        try:
            # Test PostgreSQL connection
            parsed_uri = urlparse(self.config['tracking_uri'])
            conn = psycopg2.connect(
                host=parsed_uri.hostname,
                port=parsed_uri.port,
                database=parsed_uri.path[1:],
                user=parsed_uri.username,
                password=parsed_uri.password
            )
            conn.close()
            logger.info("✅ PostgreSQL connection validated")
            
            # Test S3 connection
            s3_client = boto3.client('s3', region_name=self.config['s3_region'])
            s3_client.head_bucket(Bucket=self.config['s3_bucket'])
            logger.info("✅ S3 bucket connection validated")
            
        except Exception as e:
            logger.error(f"❌ Connection validation failed: {e}")
            raise
    
    def register_model(
        self, 
        model_name: str,
        model_version: str,
        model_path: str,
        model_type: str = "pytorch",
        tags: Optional[Dict] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Register a new model in the registry
        
        Args:
            model_name: Name of the model
            model_version: Version string
            model_path: Path to model artifacts
            model_type: Type of model (pytorch, tensorflow, sklearn, etc.)
            tags: Additional metadata tags
            description: Model description
            
        Returns:
            Model version URI
        """
        try:
            # Create registered model if it doesn't exist
            try:
                self.client.get_registered_model(model_name)
            except mlflow.exceptions.RestException:
                self.client.create_registered_model(
                    model_name,
                    tags=tags or {},
                    description=description or f"GameForge {model_type} model"
                )
                logger.info(f"✅ Created new registered model: {model_name}")
            
            # Register model version
            model_version_info = self.client.create_model_version(
                name=model_name,
                source=model_path,
                tags={
                    'model_type': model_type,
                    'framework': model_type,
                    'version': model_version,
                    'environment': 'production',
                    **(tags or {})
                },
                description=description
            )
            
            logger.info(f"✅ Registered model version: {model_name} v{model_version_info.version}")
            return f"{model_name}/{model_version_info.version}"
            
        except Exception as e:
            logger.error(f"❌ Failed to register model {model_name}: {e}")
            raise
    
    def promote_model(
        self, 
        model_name: str, 
        version: str, 
        stage: str = "Production"
    ) -> bool:
        """
        Promote model to specified stage
        
        Args:
            model_name: Name of the model
            version: Model version to promote
            stage: Target stage (Staging, Production, Archived)
            
        Returns:
            Success status
        """
        try:
            # Validate stage
            valid_stages = ["Staging", "Production", "Archived"]
            if stage not in valid_stages:
                raise ValueError(f"Invalid stage. Must be one of: {valid_stages}")
            
            # Transition model version to new stage
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage,
                archive_existing_versions=True
            )
            
            logger.info(f"✅ Promoted {model_name} v{version} to {stage}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to promote model {model_name} v{version}: {e}")
            return False
    
    def get_model_versions(
        self, 
        model_name: str, 
        stages: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get model versions by stage
        
        Args:
            model_name: Name of the model
            stages: List of stages to filter by
            
        Returns:
            List of model version metadata
        """
        try:
            versions = self.client.search_model_versions(
                filter_string=f"name='{model_name}'"
            )
            
            if stages:
                versions = [v for v in versions if v.current_stage in stages]
            
            return [
                {
                    'name': v.name,
                    'version': v.version,
                    'stage': v.current_stage,
                    'source': v.source,
                    'run_id': v.run_id,
                    'creation_timestamp': v.creation_timestamp,
                    'tags': v.tags
                }
                for v in versions
            ]
            
        except Exception as e:
            logger.error(f"❌ Failed to get model versions for {model_name}: {e}")
            return []
    
    def download_model(
        self, 
        model_name: str, 
        version: str, 
        local_path: str
    ) -> bool:
        """
        Download model artifacts to local path
        
        Args:
            model_name: Name of the model
            version: Model version
            local_path: Local download path
            
        Returns:
            Success status
        """
        try:
            model_uri = f"models:/{model_name}/{version}"
            mlflow.artifacts.download_artifacts(
                artifact_uri=model_uri,
                dst_path=local_path
            )
            
            logger.info(f"✅ Downloaded {model_name} v{version} to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to download model {model_name} v{version}: {e}")
            return False
    
    def list_models(self, filter_string: Optional[str] = None) -> List[Dict]:
        """
        List all registered models
        
        Args:
            filter_string: Optional filter for model search
            
        Returns:
            List of model metadata
        """
        try:
            models = self.client.search_registered_models(filter_string)
            
            return [
                {
                    'name': model.name,
                    'creation_timestamp': model.creation_timestamp,
                    'last_updated_timestamp': model.last_updated_timestamp,
                    'description': model.description,
                    'tags': model.tags,
                    'latest_versions': [
                        {
                            'version': v.version,
                            'stage': v.current_stage,
                            'creation_timestamp': v.creation_timestamp
                        }
                        for v in model.latest_versions
                    ]
                }
                for model in models
            ]
            
        except Exception as e:
            logger.error(f"❌ Failed to list models: {e}")
            return []
    
    def create_model_alias(
        self, 
        model_name: str, 
        version: str, 
        alias: str
    ) -> bool:
        """
        Create alias for model version
        
        Args:
            model_name: Name of the model
            version: Model version
            alias: Alias name (e.g., 'champion', 'challenger')
            
        Returns:
            Success status
        """
        try:
            self.client.set_model_version_tag(
                name=model_name,
                version=version,
                key=f"alias_{alias}",
                value="true"
            )
            
            logger.info(f"✅ Created alias '{alias}' for {model_name} v{version}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create alias {alias} for {model_name} v{version}: {e}")
            return False
    
    def health_check(self) -> Dict:
        """
        Perform health check of the model registry
        
        Returns:
            Health status information
        """
        health_status = {
            'status': 'healthy',
            'checks': {},
            'timestamp': mlflow.utils.time_utils.get_current_time_millis()
        }
        
        try:
            # Check MLflow tracking server
            experiments = self.client.search_experiments()
            health_status['checks']['mlflow_server'] = {
                'status': 'healthy',
                'experiments_count': len(experiments)
            }
        except Exception as e:
            health_status['checks']['mlflow_server'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        try:
            # Check S3 connectivity
            s3_client = boto3.client('s3', region_name=self.config['s3_region'])
            response = s3_client.head_bucket(Bucket=self.config['s3_bucket'])
            health_status['checks']['s3_storage'] = {
                'status': 'healthy',
                'bucket': self.config['s3_bucket']
            }
        except Exception as e:
            health_status['checks']['s3_storage'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        return health_status


# Utility functions for common operations
def get_production_model(model_name: str) -> Optional[Dict]:
    """Get the current production model version"""
    registry = GameForgeModelRegistry()
    versions = registry.get_model_versions(model_name, stages=["Production"])
    return versions[0] if versions else None


def deploy_model_to_staging(model_name: str, version: str) -> bool:
    """Quick deployment to staging environment"""
    registry = GameForgeModelRegistry()
    return registry.promote_model(model_name, version, "Staging")


def rollback_model(model_name: str, target_version: str) -> bool:
    """Rollback to a previous model version"""
    registry = GameForgeModelRegistry()
    return registry.promote_model(model_name, target_version, "Production")