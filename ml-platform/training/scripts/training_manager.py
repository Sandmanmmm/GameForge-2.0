#!/usr/bin/env python3
"""
GameForge Training Job Manager

Orchestrates ML training jobs across different platforms (Vast.ai, local GPU, K8s).
Ensures consistency between dataset manifests and training runs.

Usage:
    python training_manager.py --job-manifest path/to/job.yaml
    python training_manager.py --list-jobs
    python training_manager.py --monitor-job <job_id>
"""

import os
import sys
import yaml
import json
import subprocess
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import requests
from dataclasses import dataclass


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TrainingJobStatus:
    """Training job status tracking"""
    job_id: str
    status: str  # pending, running, completed, failed, cancelled
    platform: str
    instance_id: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    cost: float
    metrics: Dict[str, Any]
    artifacts: List[str]


class DatasetValidator:
    """Validates dataset consistency before training"""
    
    def __init__(self, dataset_manifest_path: str):
        with open(dataset_manifest_path, 'r') as f:
            self.manifest = yaml.safe_load(f)
    
    def validate_dataset(self, dataset_name: str) -> Dict[str, Any]:
        """Validate dataset exists and is accessible"""
        if dataset_name not in self.manifest['datasets']:
            raise ValueError(f"Dataset {dataset_name} not found in manifest")
        
        dataset = self.manifest['datasets'][dataset_name]
        results = {
            'dataset_name': dataset_name,
            'valid': True,
            'errors': [],
            'warnings': [],
            'shard_checks': []
        }
        
        # Check each shard
        for shard in dataset['shards']:
            shard_result = self._validate_shard(shard)
            results['shard_checks'].append(shard_result)
            
            if not shard_result['accessible']:
                results['valid'] = False
                results['errors'].append(f"Shard {shard['shard_id']} not accessible")
        
        # Check license compliance
        if not self._validate_license(dataset['license']):
            results['warnings'].append("License compliance check failed")
        
        # Check consent metadata
        if not self._validate_consent(dataset['consent']):
            results['warnings'].append("Consent metadata incomplete")
        
        return results
    
    def _validate_shard(self, shard: Dict) -> Dict[str, Any]:
        """Validate individual data shard"""
        shard_id = shard['shard_id']
        location = shard['location']
        expected_sha256 = shard['sha256']
        
        result = {
            'shard_id': shard_id,
            'location': location,
            'accessible': False,
            'size_match': False,
            'hash_match': False
        }
        
        try:
            # Check if S3 object exists (simplified check)
            if location.startswith('s3://'):
                # In production, use boto3 to check S3 objects
                result['accessible'] = True  # Placeholder
                result['size_match'] = True  # Placeholder
                result['hash_match'] = True  # Placeholder
            else:
                # Local file check
                if os.path.exists(location):
                    result['accessible'] = True
                    # Check file size and hash
                    file_size = os.path.getsize(location)
                    result['size_match'] = file_size == shard['size_bytes']
                    
                    # Calculate SHA256
                    with open(location, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    result['hash_match'] = file_hash == expected_sha256
                    
        except Exception as e:
            logger.error(f"Error validating shard {shard_id}: {e}")
        
        return result
    
    def _validate_license(self, license_info: Dict) -> bool:
        """Validate license compliance"""
        required_fields = ['type', 'commercial_use']
        return all(field in license_info for field in required_fields)
    
    def _validate_consent(self, consent_info: Dict) -> bool:
        """Validate consent metadata"""
        required_fields = ['user_consent_obtained', 'gdpr_compliant']
        return all(field in consent_info for field in required_fields)


class VastAIManager:
    """Manages training jobs on Vast.ai"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('VAST_API_KEY')
        self.base_url = "https://console.vast.ai/api/v0"
    
    def search_instances(self, search_params: Dict) -> List[Dict]:
        """Search for available Vast.ai instances"""
        if not self.api_key:
            logger.warning("Vast.ai API key not configured")
            return []
        
        # Convert search params to Vast.ai format
        query = self._build_search_query(search_params)
        
        try:
            response = requests.get(
                f"{self.base_url}/bundles",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params=query
            )
            response.raise_for_status()
            return response.json()['offers']
        except requests.RequestException as e:
            logger.error(f"Failed to search Vast.ai instances: {e}")
            return []
    
    def _build_search_query(self, search_params: Dict) -> Dict:
        """Build Vast.ai search query"""
        query = {
            'q': json.dumps({
                'gpu_name': search_params.get('gpu_name'),
                'num_gpus': search_params.get('num_gpus', 1),
                'gpu_ram': search_params.get('gpu_ram'),
                'cpu_cores': search_params.get('cpu_cores'),
                'ram': search_params.get('ram'),
            }),
            'order': [['dpph', 'asc']]  # Order by price per hour
        }
        return query
    
    def launch_instance(self, offer_id: str, job_config: Dict) -> Dict:
        """Launch training instance on Vast.ai"""
        if not self.api_key:
            raise ValueError("Vast.ai API key required")
        
        launch_config = {
            'client_id': 'gameforge-training',
            'image': job_config['vast_ai']['image'],
            'disk': job_config['vast_ai']['disk_space'],
            'label': job_config['job_id'],
            'onstart': self._generate_onstart_script(job_config),
            'env': self._generate_environment_vars(job_config)
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/asks/{offer_id}/",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=launch_config
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to launch Vast.ai instance: {e}")
            raise
    
    def _generate_onstart_script(self, job_config: Dict) -> str:
        """Generate startup script for Vast.ai instance"""
        script = f"""#!/bin/bash
set -e

echo "Starting GameForge training job: {job_config['job_id']}"

# Clone repository
git clone https://github.com/Sandmanmmm/GameForge.git /workspace/gameforge
cd /workspace/gameforge

# Setup environment
pip install -r requirements.txt

# Download datasets
python ml-platform/training/scripts/download_datasets.py \\
    --manifest datasets/dataset-manifest.yaml \\
    --dataset {job_config['dataset']['primary']}

# Start training
python ml-platform/training/scripts/train_model.py \\
    --job-manifest {job_config['job_id']}.yaml \\
    --output-dir /workspace/outputs

# Upload results
python ml-platform/training/scripts/upload_results.py \\
    --job-id {job_config['job_id']} \\
    --output-dir /workspace/outputs
"""
        return script
    
    def _generate_environment_vars(self, job_config: Dict) -> Dict[str, str]:
        """Generate environment variables for training"""
        return {
            'GAMEFORGE_JOB_ID': job_config['job_id'],
            'MLFLOW_TRACKING_URI': os.getenv('MLFLOW_TRACKING_URI', ''),
            'WANDB_API_KEY': os.getenv('WANDB_API_KEY', ''),
            'AWS_ACCESS_KEY_ID': os.getenv('AWS_ACCESS_KEY_ID', ''),
            'AWS_SECRET_ACCESS_KEY': os.getenv('AWS_SECRET_ACCESS_KEY', ''),
            'GAMEFORGE_S3_BUCKET': 'gameforge-models'
        }


class LocalGPUManager:
    """Manages training jobs on local GPU"""
    
    def __init__(self):
        self.check_gpu_availability()
    
    def check_gpu_availability(self) -> Dict[str, Any]:
        """Check local GPU availability"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,memory.free', 
                 '--format=csv,noheader,nounits'],
                capture_output=True,
                text=True,
                check=True
            )
            
            gpus = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    name, total_mem, free_mem = line.split(', ')
                    gpus.append({
                        'name': name,
                        'total_memory_mb': int(total_mem),
                        'free_memory_mb': int(free_mem),
                        'utilization_percent': 100 - (int(free_mem) / int(total_mem) * 100)
                    })
            
            return {'available': True, 'gpus': gpus}
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            return {'available': False, 'gpus': []}
    
    def launch_training(self, job_config: Dict) -> subprocess.Popen:
        """Launch local training job"""
        cmd = [
            'python', 'ml-platform/training/scripts/train_model.py',
            '--job-manifest', f"{job_config['job_id']}.yaml",
            '--platform', 'local'
        ]
        
        env = os.environ.copy()
        env.update({
            'CUDA_VISIBLE_DEVICES': ','.join(map(str, job_config['local_gpu']['gpu_devices'])),
            'GAMEFORGE_JOB_ID': job_config['job_id']
        })
        
        return subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class TrainingManager:
    """Main training job orchestrator"""
    
    def __init__(self):
        self.vast_manager = VastAIManager()
        self.local_manager = LocalGPUManager()
        self.jobs_db_path = Path("ml-platform/training/jobs_database.json")
        self.dataset_validator = DatasetValidator("datasets/dataset-manifest.yaml")
    
    def submit_job(self, job_manifest_path: str) -> str:
        """Submit training job"""
        with open(job_manifest_path, 'r') as f:
            job_config = yaml.safe_load(f)
        
        job_id = job_config['job_id']
        logger.info(f"Submitting training job: {job_id}")
        
        # Validate dataset consistency
        dataset_validation = self.dataset_validator.validate_dataset(
            job_config['dataset']['primary']
        )
        
        if not dataset_validation['valid']:
            raise ValueError(f"Dataset validation failed: {dataset_validation['errors']}")
        
        # Create job status
        job_status = TrainingJobStatus(
            job_id=job_id,
            status='pending',
            platform=job_config['environment']['platform'],
            instance_id=None,
            start_time=None,
            end_time=None,
            cost=0.0,
            metrics={},
            artifacts=[]
        )
        
        # Launch based on platform
        if job_config['environment']['platform'] == 'vast.ai':
            self._launch_vast_job(job_config, job_status)
        elif job_config['environment']['platform'] == 'local':
            self._launch_local_job(job_config, job_status)
        else:
            raise ValueError(f"Unsupported platform: {job_config['environment']['platform']}")
        
        # Save job status
        self._save_job_status(job_status)
        
        return job_id
    
    def _launch_vast_job(self, job_config: Dict, job_status: TrainingJobStatus):
        """Launch job on Vast.ai"""
        # Search for suitable instances
        instances = self.vast_manager.search_instances(job_config['vast_ai']['search_params'])
        
        if not instances:
            raise RuntimeError("No suitable Vast.ai instances found")
        
        # Select best instance (lowest cost)
        best_instance = min(instances, key=lambda x: x['dpph'])
        
        # Launch instance
        launch_result = self.vast_manager.launch_instance(best_instance['id'], job_config)
        
        job_status.instance_id = str(launch_result['new_contract'])
        job_status.status = 'running'
        job_status.start_time = datetime.now()
        
        logger.info(f"Launched Vast.ai instance {job_status.instance_id} for job {job_status.job_id}")
    
    def _launch_local_job(self, job_config: Dict, job_status: TrainingJobStatus):
        """Launch job locally"""
        gpu_status = self.local_manager.check_gpu_availability()
        
        if not gpu_status['available']:
            raise RuntimeError("No GPUs available for local training")
        
        # Launch training process
        process = self.local_manager.launch_training(job_config)
        
        job_status.instance_id = str(process.pid)
        job_status.status = 'running'
        job_status.start_time = datetime.now()
        
        logger.info(f"Started local training process {process.pid} for job {job_status.job_id}")
    
    def _save_job_status(self, job_status: TrainingJobStatus):
        """Save job status to database"""
        jobs_db = self._load_jobs_database()
        
        jobs_db[job_status.job_id] = {
            'job_id': job_status.job_id,
            'status': job_status.status,
            'platform': job_status.platform,
            'instance_id': job_status.instance_id,
            'start_time': job_status.start_time.isoformat() if job_status.start_time else None,
            'end_time': job_status.end_time.isoformat() if job_status.end_time else None,
            'cost': job_status.cost,
            'metrics': job_status.metrics,
            'artifacts': job_status.artifacts
        }
        
        with open(self.jobs_db_path, 'w') as f:
            json.dump(jobs_db, f, indent=2)
    
    def _load_jobs_database(self) -> Dict:
        """Load jobs database"""
        if self.jobs_db_path.exists():
            with open(self.jobs_db_path, 'r') as f:
                return json.load(f)
        return {}
    
    def list_jobs(self) -> List[Dict]:
        """List all training jobs"""
        return list(self._load_jobs_database().values())
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get specific job status"""
        jobs_db = self._load_jobs_database()
        return jobs_db.get(job_id)
    
    def monitor_job(self, job_id: str) -> Dict:
        """Monitor job progress"""
        job_status = self.get_job_status(job_id)
        
        if not job_status:
            raise ValueError(f"Job {job_id} not found")
        
        # Platform-specific monitoring
        if job_status['platform'] == 'vast.ai':
            return self._monitor_vast_job(job_status)
        elif job_status['platform'] == 'local':
            return self._monitor_local_job(job_status)
        
        return job_status
    
    def _monitor_vast_job(self, job_status: Dict) -> Dict:
        """Monitor Vast.ai job"""
        # Query Vast.ai API for instance status
        # Update metrics from MLflow/W&B
        # Check for completion
        return job_status
    
    def _monitor_local_job(self, job_status: Dict) -> Dict:
        """Monitor local job"""
        # Check if process is still running
        # Update metrics from logs
        return job_status


def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GameForge Training Job Manager')
    parser.add_argument('--job-manifest', help='Path to training job manifest')
    parser.add_argument('--list-jobs', action='store_true', help='List all jobs')
    parser.add_argument('--monitor-job', help='Monitor specific job')
    parser.add_argument('--job-id', help='Job ID for operations')
    
    args = parser.parse_args()
    
    manager = TrainingManager()
    
    if args.job_manifest:
        job_id = manager.submit_job(args.job_manifest)
        print(f"Submitted job: {job_id}")
    
    elif args.list_jobs:
        jobs = manager.list_jobs()
        print(f"Found {len(jobs)} jobs:")
        for job in jobs:
            print(f"  {job['job_id']}: {job['status']} ({job['platform']})")
    
    elif args.monitor_job:
        status = manager.monitor_job(args.monitor_job)
        print(f"Job {args.monitor_job} status: {status['status']}")
        if status.get('metrics'):
            print("Metrics:", status['metrics'])
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()