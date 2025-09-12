"""
GameForge Dataset Versioning System with DVC
============================================

Implements comprehensive dataset versioning and management with:
- DVC integration with S3 backend
- Data pipeline orchestration
- Dataset lineage tracking
- Automated data validation
- Data drift detection
- Integration with MLflow experiments
"""

import os
import json
import logging
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import yaml

import dvc.api
import dvc.repo
from dvc.exceptions import DvcException
import boto3
from botocore.exceptions import ClientError
import pandas as pd
import numpy as np
from scipy import stats
import asyncpg
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge
import mlflow
import mlflow.tracking

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
dataset_versions_counter = Counter('gameforge_dataset_versions_total', 'Total dataset versions', ['dataset', 'status'])
data_validation_time = Histogram('gameforge_data_validation_duration_seconds', 'Data validation duration', ['dataset'])
dataset_size_gauge = Gauge('gameforge_dataset_size_bytes', 'Dataset size in bytes', ['dataset', 'version'])
data_drift_score = Gauge('gameforge_data_drift_score', 'Data drift score', ['dataset', 'baseline_version', 'current_version'])

class DatasetStatus(Enum):
    """Dataset status enumeration"""
    UPLOADING = "uploading"
    VALIDATING = "validating"
    AVAILABLE = "available"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    FAILED = "failed"

class ValidationStatus(Enum):
    """Validation status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"

class DriftStatus(Enum):
    """Data drift status enumeration"""
    NO_DRIFT = "no_drift"
    MINOR_DRIFT = "minor_drift"
    MODERATE_DRIFT = "moderate_drift"
    SEVERE_DRIFT = "severe_drift"

@dataclass
class DatasetMetadata:
    """Dataset metadata structure"""
    name: str
    version: str
    description: str
    format: str
    size_bytes: int
    file_count: int
    schema_hash: str
    created_at: datetime
    created_by: str
    tags: Dict[str, str]
    validation_results: Optional[Dict] = None
    lineage: Optional[Dict] = None

@dataclass
class ValidationRule:
    """Data validation rule"""
    rule_type: str
    column: Optional[str]
    condition: str
    threshold: Union[float, int, str]
    severity: str  # error, warning, info

@dataclass
class DataLineage:
    """Data lineage tracking"""
    dataset_name: str
    version: str
    parent_datasets: List[Tuple[str, str]]  # (dataset_name, version)
    transformation_script: Optional[str]
    transformation_params: Dict[str, Any]
    created_at: datetime

class S3DataStore:
    """S3 backend for DVC data storage"""
    
    def __init__(self, bucket_name: str, endpoint_url: Optional[str] = None,
                 access_key: Optional[str] = None, secret_key: Optional[str] = None):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
    async def upload_dataset(self, local_path: str, remote_path: str) -> bool:
        """Upload dataset to S3"""
        try:
            if os.path.isdir(local_path):
                # Upload directory recursively
                for root, dirs, files in os.walk(local_path):
                    for file in files:
                        local_file = os.path.join(root, file)
                        relative_path = os.path.relpath(local_file, local_path)
                        s3_key = f"{remote_path}/{relative_path}".replace('\\', '/')
                        
                        self.s3_client.upload_file(local_file, self.bucket_name, s3_key)
                        logger.info(f"Uploaded {local_file} to s3://{self.bucket_name}/{s3_key}")
            else:
                # Upload single file
                self.s3_client.upload_file(local_path, self.bucket_name, remote_path)
                logger.info(f"Uploaded {local_path} to s3://{self.bucket_name}/{remote_path}")
                
            return True
            
        except ClientError as e:
            logger.error(f"Error uploading to S3: {e}")
            return False
            
    async def download_dataset(self, remote_path: str, local_path: str) -> bool:
        """Download dataset from S3"""
        try:
            # Create local directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # List objects with the prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=remote_path
            )
            
            if 'Contents' not in response:
                logger.warning(f"No objects found with prefix {remote_path}")
                return False
                
            for obj in response['Contents']:
                s3_key = obj['Key']
                local_file_path = os.path.join(local_path, 
                                             os.path.relpath(s3_key, remote_path))
                
                # Create directory for file if needed
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                
                self.s3_client.download_file(self.bucket_name, s3_key, local_file_path)
                logger.info(f"Downloaded s3://{self.bucket_name}/{s3_key} to {local_file_path}")
                
            return True
            
        except ClientError as e:
            logger.error(f"Error downloading from S3: {e}")
            return False
            
    async def list_dataset_versions(self, dataset_name: str) -> List[str]:
        """List all versions of a dataset"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"datasets/{dataset_name}/",
                Delimiter='/'
            )
            
            versions = []
            if 'CommonPrefixes' in response:
                for prefix in response['CommonPrefixes']:
                    version = prefix['Prefix'].split('/')[-2]
                    versions.append(version)
                    
            return sorted(versions, reverse=True)  # Latest first
            
        except ClientError as e:
            logger.error(f"Error listing dataset versions: {e}")
            return []

class DataValidator:
    """Data validation and quality checks"""
    
    def __init__(self):
        self.validation_rules = {}
        
    def add_validation_rule(self, dataset_name: str, rule: ValidationRule) -> None:
        """Add validation rule for dataset"""
        if dataset_name not in self.validation_rules:
            self.validation_rules[dataset_name] = []
        self.validation_rules[dataset_name].append(rule)
        
    def load_validation_rules(self, config_path: str) -> None:
        """Load validation rules from YAML config"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            for dataset_name, rules_config in config.get('datasets', {}).items():
                for rule_config in rules_config.get('validation_rules', []):
                    rule = ValidationRule(**rule_config)
                    self.add_validation_rule(dataset_name, rule)
                    
            logger.info(f"Loaded validation rules from {config_path}")
            
        except Exception as e:
            logger.error(f"Error loading validation rules: {e}")
            
    async def validate_dataset(self, dataset_path: str, dataset_name: str) -> Dict[str, Any]:
        """Validate dataset against defined rules"""
        start_time = datetime.utcnow()
        validation_results = {
            'status': ValidationStatus.RUNNING.value,
            'timestamp': start_time.isoformat(),
            'errors': [],
            'warnings': [],
            'info': [],
            'summary': {}
        }
        
        try:
            # Get validation rules for dataset
            rules = self.validation_rules.get(dataset_name, [])
            
            # Load dataset for validation
            if dataset_path.endswith('.csv'):
                df = pd.read_csv(dataset_path)
            elif dataset_path.endswith('.parquet'):
                df = pd.read_parquet(dataset_path)
            elif dataset_path.endswith('.json'):
                df = pd.read_json(dataset_path)
            else:
                # For directories, validate all CSV files
                df = self._load_dataset_directory(dataset_path)
                
            # Basic dataset info
            validation_results['summary'] = {
                'rows': len(df),
                'columns': len(df.columns),
                'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024**2,
                'null_values': df.isnull().sum().to_dict(),
                'dtypes': df.dtypes.astype(str).to_dict()
            }
            
            # Apply validation rules
            for rule in rules:
                try:
                    result = self._apply_validation_rule(df, rule)
                    if result:
                        if rule.severity == 'error':
                            validation_results['errors'].append(result)
                        elif rule.severity == 'warning':
                            validation_results['warnings'].append(result)
                        else:
                            validation_results['info'].append(result)
                except Exception as e:
                    logger.error(f"Error applying validation rule: {e}")
                    validation_results['errors'].append(f"Rule validation error: {str(e)}")
                    
            # Determine overall status
            if validation_results['errors']:
                validation_results['status'] = ValidationStatus.FAILED.value
            elif validation_results['warnings']:
                validation_results['status'] = ValidationStatus.WARNING.value
            else:
                validation_results['status'] = ValidationStatus.PASSED.value
                
            # Record validation time
            duration = (datetime.utcnow() - start_time).total_seconds()
            data_validation_time.labels(dataset=dataset_name).observe(duration)
            
            logger.info(f"Dataset validation completed for {dataset_name}: {validation_results['status']}")
            
        except Exception as e:
            logger.error(f"Dataset validation failed: {e}")
            validation_results['status'] = ValidationStatus.FAILED.value
            validation_results['errors'].append(f"Validation process error: {str(e)}")
            
        return validation_results
        
    def _load_dataset_directory(self, directory_path: str) -> pd.DataFrame:
        """Load all CSV files from directory into single DataFrame"""
        dfs = []
        for file_path in Path(directory_path).glob('**/*.csv'):
            df = pd.read_csv(file_path)
            df['source_file'] = str(file_path)
            dfs.append(df)
            
        if not dfs:
            raise ValueError(f"No CSV files found in {directory_path}")
            
        return pd.concat(dfs, ignore_index=True)
        
    def _apply_validation_rule(self, df: pd.DataFrame, rule: ValidationRule) -> Optional[str]:
        """Apply single validation rule to DataFrame"""
        if rule.rule_type == 'not_null':
            if rule.column and df[rule.column].isnull().any():
                null_count = df[rule.column].isnull().sum()
                return f"Column '{rule.column}' has {null_count} null values"
                
        elif rule.rule_type == 'unique':
            if rule.column and df[rule.column].duplicated().any():
                dup_count = df[rule.column].duplicated().sum()
                return f"Column '{rule.column}' has {dup_count} duplicate values"
                
        elif rule.rule_type == 'range':
            if rule.column:
                if rule.condition == 'min' and df[rule.column].min() < rule.threshold:
                    return f"Column '{rule.column}' minimum value {df[rule.column].min()} below threshold {rule.threshold}"
                elif rule.condition == 'max' and df[rule.column].max() > rule.threshold:
                    return f"Column '{rule.column}' maximum value {df[rule.column].max()} above threshold {rule.threshold}"
                    
        elif rule.rule_type == 'row_count':
            if rule.condition == 'min' and len(df) < rule.threshold:
                return f"Dataset has {len(df)} rows, below minimum threshold {rule.threshold}"
            elif rule.condition == 'max' and len(df) > rule.threshold:
                return f"Dataset has {len(df)} rows, above maximum threshold {rule.threshold}"
                
        elif rule.rule_type == 'schema':
            expected_columns = rule.threshold
            if isinstance(expected_columns, list):
                missing_cols = set(expected_columns) - set(df.columns)
                if missing_cols:
                    return f"Missing required columns: {missing_cols}"
                    
        return None

class DriftDetector:
    """Data drift detection between dataset versions"""
    
    @staticmethod
    def detect_drift(baseline_df: pd.DataFrame, current_df: pd.DataFrame,
                    threshold: float = 0.05) -> Dict[str, Any]:
        """Detect statistical drift between two datasets"""
        drift_results = {
            'overall_drift_score': 0.0,
            'drift_status': DriftStatus.NO_DRIFT.value,
            'column_drifts': {},
            'summary': {
                'baseline_rows': len(baseline_df),
                'current_rows': len(current_df),
                'common_columns': [],
                'new_columns': [],
                'removed_columns': []
            }
        }
        
        # Column comparison
        baseline_cols = set(baseline_df.columns)
        current_cols = set(current_df.columns)
        
        drift_results['summary']['common_columns'] = list(baseline_cols & current_cols)
        drift_results['summary']['new_columns'] = list(current_cols - baseline_cols)
        drift_results['summary']['removed_columns'] = list(baseline_cols - current_cols)
        
        # Calculate drift for common numerical columns
        drift_scores = []
        
        for col in drift_results['summary']['common_columns']:
            if baseline_df[col].dtype in ['int64', 'float64'] and current_df[col].dtype in ['int64', 'float64']:
                # KS test for numerical columns
                try:
                    ks_stat, p_value = stats.ks_2samp(baseline_df[col].dropna(), current_df[col].dropna())
                    
                    drift_results['column_drifts'][col] = {
                        'drift_score': ks_stat,
                        'p_value': p_value,
                        'is_drifted': p_value < threshold,
                        'baseline_mean': float(baseline_df[col].mean()),
                        'current_mean': float(current_df[col].mean()),
                        'baseline_std': float(baseline_df[col].std()),
                        'current_std': float(current_df[col].std())
                    }
                    
                    drift_scores.append(ks_stat)
                    
                except Exception as e:
                    logger.warning(f"Error calculating drift for column {col}: {e}")
                    
            elif baseline_df[col].dtype == 'object' and current_df[col].dtype == 'object':
                # Chi-square test for categorical columns
                try:
                    baseline_counts = baseline_df[col].value_counts()
                    current_counts = current_df[col].value_counts()
                    
                    # Align categories
                    all_categories = set(baseline_counts.index) | set(current_counts.index)
                    baseline_aligned = [baseline_counts.get(cat, 0) for cat in all_categories]
                    current_aligned = [current_counts.get(cat, 0) for cat in all_categories]
                    
                    if sum(baseline_aligned) > 0 and sum(current_aligned) > 0:
                        chi2_stat, p_value = stats.chisquare(current_aligned, baseline_aligned)
                        
                        drift_results['column_drifts'][col] = {
                            'drift_score': chi2_stat,
                            'p_value': p_value,
                            'is_drifted': p_value < threshold,
                            'baseline_unique': len(baseline_counts),
                            'current_unique': len(current_counts)
                        }
                        
                        # Normalize chi2 stat to 0-1 range for overall score
                        normalized_score = min(chi2_stat / 100, 1.0)
                        drift_scores.append(normalized_score)
                        
                except Exception as e:
                    logger.warning(f"Error calculating drift for categorical column {col}: {e}")
                    
        # Calculate overall drift score
        if drift_scores:
            drift_results['overall_drift_score'] = np.mean(drift_scores)
            
            # Determine drift status
            if drift_results['overall_drift_score'] > 0.7:
                drift_results['drift_status'] = DriftStatus.SEVERE_DRIFT.value
            elif drift_results['overall_drift_score'] > 0.4:
                drift_results['drift_status'] = DriftStatus.MODERATE_DRIFT.value
            elif drift_results['overall_drift_score'] > 0.1:
                drift_results['drift_status'] = DriftStatus.MINOR_DRIFT.value
                
        return drift_results

class DatasetVersionManager:
    """Main dataset versioning and management system"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis,
                 s3_bucket: str, dvc_repo_path: str = "./dvc-repo"):
        self.db_pool = db_pool
        self.redis = redis_client
        self.s3_store = S3DataStore(s3_bucket)
        self.validator = DataValidator()
        self.dvc_repo_path = dvc_repo_path
        
        # Initialize DVC repo if it doesn't exist
        self._init_dvc_repo()
        
    def _init_dvc_repo(self) -> None:
        """Initialize DVC repository"""
        try:
            if not os.path.exists(os.path.join(self.dvc_repo_path, '.dvc')):
                os.makedirs(self.dvc_repo_path, exist_ok=True)
                
                # Initialize DVC repo
                repo = dvc.repo.Repo.init(self.dvc_repo_path)
                
                # Configure S3 remote
                with repo.config.edit() as conf:
                    conf["remote"]["s3"] = {
                        "url": f"s3://{self.s3_store.bucket_name}/dvc-cache"
                    }
                    conf["core"]["remote"] = "s3"
                    
                logger.info(f"Initialized DVC repository at {self.dvc_repo_path}")
            else:
                logger.info(f"DVC repository already exists at {self.dvc_repo_path}")
                
        except Exception as e:
            logger.error(f"Error initializing DVC repo: {e}")
            
    async def create_dataset_version(self, dataset_name: str, version: str,
                                   local_path: str, description: str = "",
                                   tags: Dict[str, str] = None,
                                   parent_datasets: List[Tuple[str, str]] = None) -> bool:
        """Create new dataset version"""
        try:
            logger.info(f"Creating dataset version {dataset_name}:{version}")
            
            # Generate metadata
            metadata = await self._generate_metadata(
                dataset_name, version, local_path, description, tags or {}
            )
            
            # Validate dataset
            validation_results = await self.validator.validate_dataset(local_path, dataset_name)
            metadata.validation_results = validation_results
            
            # Create lineage record
            if parent_datasets:
                lineage = DataLineage(
                    dataset_name=dataset_name,
                    version=version,
                    parent_datasets=parent_datasets,
                    transformation_script=None,  # Could be populated from metadata
                    transformation_params={},
                    created_at=datetime.utcnow()
                )
                metadata.lineage = asdict(lineage)
                
            # Add to DVC tracking
            dataset_dvc_path = os.path.join(self.dvc_repo_path, 'datasets', dataset_name, version)
            os.makedirs(dataset_dvc_path, exist_ok=True)
            
            repo = dvc.repo.Repo(self.dvc_repo_path)
            
            # Copy data to DVC path and add to tracking
            if os.path.isdir(local_path):
                import shutil
                shutil.copytree(local_path, dataset_dvc_path, dirs_exist_ok=True)
            else:
                import shutil
                shutil.copy2(local_path, dataset_dvc_path)
                
            # Add to DVC tracking
            repo.add(dataset_dvc_path)
            
            # Upload to S3 via DVC
            repo.push()
            
            # Store metadata in database
            await self._store_metadata(metadata)
            
            # Update Prometheus metrics
            dataset_versions_counter.labels(dataset=dataset_name, status="created").inc()
            dataset_size_gauge.labels(dataset=dataset_name, version=version).set(metadata.size_bytes)
            
            # Cache metadata in Redis
            await self._cache_metadata(metadata)
            
            logger.info(f"Successfully created dataset version {dataset_name}:{version}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating dataset version: {e}")
            dataset_versions_counter.labels(dataset=dataset_name, status="failed").inc()
            return False
            
    async def get_dataset(self, dataset_name: str, version: str = "latest",
                         local_path: str = None) -> Optional[str]:
        """Download dataset version to local path"""
        try:
            if version == "latest":
                version = await self._get_latest_version(dataset_name)
                
            if not version:
                logger.error(f"No versions found for dataset {dataset_name}")
                return None
                
            # Set default local path if not provided
            if local_path is None:
                local_path = f"./data/{dataset_name}/{version}"
                
            # Get from DVC
            dataset_dvc_path = f"datasets/{dataset_name}/{version}"
            
            repo = dvc.repo.Repo(self.dvc_repo_path)
            
            # Pull from remote storage
            repo.pull(targets=[dataset_dvc_path])
            
            # Copy to requested local path
            source_path = os.path.join(self.dvc_repo_path, dataset_dvc_path)
            if os.path.exists(source_path):
                if os.path.isdir(source_path):
                    import shutil
                    shutil.copytree(source_path, local_path, dirs_exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    import shutil
                    shutil.copy2(source_path, local_path)
                    
                logger.info(f"Downloaded dataset {dataset_name}:{version} to {local_path}")
                return local_path
            else:
                logger.error(f"Dataset path not found: {source_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading dataset: {e}")
            return None
            
    async def detect_data_drift(self, dataset_name: str, baseline_version: str,
                              current_version: str) -> Dict[str, Any]:
        """Detect drift between two dataset versions"""
        try:
            # Download both versions temporarily
            baseline_path = await self.get_dataset(dataset_name, baseline_version, 
                                                 f"./tmp/drift/{dataset_name}/{baseline_version}")
            current_path = await self.get_dataset(dataset_name, current_version,
                                                f"./tmp/drift/{dataset_name}/{current_version}")
            
            if not baseline_path or not current_path:
                raise ValueError("Failed to download datasets for drift detection")
                
            # Load datasets
            baseline_df = self._load_dataset_for_drift(baseline_path)
            current_df = self._load_dataset_for_drift(current_path)
            
            # Detect drift
            drift_results = DriftDetector.detect_drift(baseline_df, current_df)
            
            # Store drift results
            await self._store_drift_results(dataset_name, baseline_version, 
                                          current_version, drift_results)
            
            # Update Prometheus metrics
            data_drift_score.labels(
                dataset=dataset_name,
                baseline_version=baseline_version,
                current_version=current_version
            ).set(drift_results['overall_drift_score'])
            
            # Clean up temporary files
            import shutil
            shutil.rmtree(f"./tmp/drift/{dataset_name}", ignore_errors=True)
            
            return drift_results
            
        except Exception as e:
            logger.error(f"Error detecting drift: {e}")
            return {}
            
    def _load_dataset_for_drift(self, path: str) -> pd.DataFrame:
        """Load dataset for drift detection"""
        if os.path.isdir(path):
            # Load all CSV files from directory
            dfs = []
            for csv_file in Path(path).glob('**/*.csv'):
                df = pd.read_csv(csv_file)
                dfs.append(df)
            if dfs:
                return pd.concat(dfs, ignore_index=True)
            else:
                raise ValueError(f"No CSV files found in {path}")
        else:
            # Single file
            if path.endswith('.csv'):
                return pd.read_csv(path)
            elif path.endswith('.parquet'):
                return pd.read_parquet(path)
            else:
                raise ValueError(f"Unsupported file format: {path}")
                
    async def list_datasets(self) -> List[Dict[str, Any]]:
        """List all datasets with their versions"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT dataset_name, 
                           COUNT(*) as version_count,
                           MAX(created_at) as latest_created,
                           SUM(size_bytes) as total_size
                    FROM dataset_metadata
                    GROUP BY dataset_name
                    ORDER BY latest_created DESC
                """)
                
            datasets = []
            for row in rows:
                dataset_info = {
                    'name': row['dataset_name'],
                    'version_count': row['version_count'],
                    'latest_created': row['latest_created'],
                    'total_size_bytes': row['total_size'],
                    'total_size_mb': round(row['total_size'] / (1024**2), 2)
                }
                datasets.append(dataset_info)
                
            return datasets
            
        except Exception as e:
            logger.error(f"Error listing datasets: {e}")
            return []
            
    async def get_dataset_lineage(self, dataset_name: str, version: str) -> Dict[str, Any]:
        """Get lineage information for a dataset version"""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT lineage FROM dataset_metadata
                    WHERE dataset_name = $1 AND version = $2
                """, dataset_name, version)
                
            if row and row['lineage']:
                return json.loads(row['lineage'])
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting dataset lineage: {e}")
            return {}
            
    async def _generate_metadata(self, dataset_name: str, version: str,
                               local_path: str, description: str,
                               tags: Dict[str, str]) -> DatasetMetadata:
        """Generate metadata for dataset"""
        # Calculate size and file count
        size_bytes = 0
        file_count = 0
        
        if os.path.isdir(local_path):
            for root, dirs, files in os.walk(local_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    size_bytes += os.path.getsize(file_path)
                    file_count += 1
        else:
            size_bytes = os.path.getsize(local_path)
            file_count = 1
            
        # Generate schema hash
        schema_hash = self._generate_schema_hash(local_path)
        
        # Detect format
        if os.path.isdir(local_path):
            format_type = "directory"
        else:
            format_type = os.path.splitext(local_path)[1][1:]  # Remove dot
            
        return DatasetMetadata(
            name=dataset_name,
            version=version,
            description=description,
            format=format_type,
            size_bytes=size_bytes,
            file_count=file_count,
            schema_hash=schema_hash,
            created_at=datetime.utcnow(),
            created_by="gameforge-system",  # Could be dynamic
            tags=tags
        )
        
    def _generate_schema_hash(self, path: str) -> str:
        """Generate hash of dataset schema"""
        try:
            if os.path.isdir(path):
                # For directories, hash the structure and first CSV file schema
                structure = []
                for root, dirs, files in os.walk(path):
                    for file in sorted(files):
                        structure.append(f"{file}:{os.path.getsize(os.path.join(root, file))}")
                        
                # Also include schema of first CSV file if available
                for csv_file in Path(path).glob('**/*.csv'):
                    df = pd.read_csv(csv_file, nrows=0)  # Just headers
                    structure.extend([f"col:{col}:{dtype}" for col, dtype in df.dtypes.items()])
                    break
                    
                schema_str = '|'.join(structure)
            else:
                # For single files, hash based on content structure
                if path.endswith('.csv'):
                    df = pd.read_csv(path, nrows=0)  # Just headers
                    schema_str = '|'.join([f"{col}:{dtype}" for col, dtype in df.dtypes.items()])
                else:
                    # For other files, use basic file info
                    schema_str = f"file:{os.path.basename(path)}:{os.path.getsize(path)}"
                    
            return hashlib.md5(schema_str.encode()).hexdigest()
            
        except Exception as e:
            logger.warning(f"Error generating schema hash: {e}")
            return hashlib.md5(f"{path}:{datetime.utcnow()}".encode()).hexdigest()
            
    async def _store_metadata(self, metadata: DatasetMetadata) -> None:
        """Store metadata in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO dataset_metadata 
                (dataset_name, version, description, format, size_bytes, file_count,
                 schema_hash, created_at, created_by, tags, validation_results, lineage)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (dataset_name, version) 
                DO UPDATE SET 
                    description = $3,
                    validation_results = $11,
                    updated_at = CURRENT_TIMESTAMP
            """, metadata.name, metadata.version, metadata.description, metadata.format,
                metadata.size_bytes, metadata.file_count, metadata.schema_hash,
                metadata.created_at, metadata.created_by, json.dumps(metadata.tags),
                json.dumps(metadata.validation_results) if metadata.validation_results else None,
                json.dumps(metadata.lineage) if metadata.lineage else None)
                
    async def _cache_metadata(self, metadata: DatasetMetadata) -> None:
        """Cache metadata in Redis"""
        key = f"dataset:{metadata.name}:{metadata.version}"
        await self.redis.setex(key, 3600, json.dumps(asdict(metadata), default=str))
        
    async def _get_latest_version(self, dataset_name: str) -> Optional[str]:
        """Get latest version of dataset"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT version FROM dataset_metadata
                WHERE dataset_name = $1
                ORDER BY created_at DESC
                LIMIT 1
            """, dataset_name)
            
        return row['version'] if row else None
        
    async def _store_drift_results(self, dataset_name: str, baseline_version: str,
                                 current_version: str, drift_results: Dict[str, Any]) -> None:
        """Store drift detection results"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO dataset_drift_analysis 
                (dataset_name, baseline_version, current_version, drift_score,
                 drift_status, analysis_results, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, dataset_name, baseline_version, current_version,
                drift_results['overall_drift_score'], drift_results['drift_status'],
                json.dumps(drift_results), datetime.utcnow())

async def main():
    """Main application entry point"""
    # Database connection
    db_pool = await asyncpg.create_pool(
        host="mlflow-postgres",
        port=5432,
        user="mlflow",
        password="mlflow_password",
        database="mlflow",
        min_size=5,
        max_size=20
    )
    
    # Redis connection
    redis_client = redis.from_url("redis://mlflow-redis:6379/3")
    
    # Initialize dataset version manager
    manager = DatasetVersionManager(db_pool, redis_client, "gameforge-datasets")
    
    # Load validation rules
    manager.validator.load_validation_rules("./config/dataset-validation.yaml")
    
    logger.info("GameForge Dataset Versioning System started")
    
    # Keep the service running
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())