#!/usr/bin/env python3
"""
GameForge Experiment Tracking Integration

Provides unified interface for MLflow, Weights & Biases, and internal logging.
Tracks hyperparameters, metrics, and artifacts across training runs.

Usage:
    from experiment_tracker import ExperimentTracker
    
    tracker = ExperimentTracker("mlflow")  # or "wandb", "internal"
    tracker.start_run("llama2-lora-experiment")
    tracker.log_params({"learning_rate": 0.0002, "batch_size": 16})
    tracker.log_metrics({"loss": 1.5, "perplexity": 4.2}, step=100)
    tracker.log_artifact("model.safetensors")
    tracker.end_run()
"""

import os
import json
import yaml
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
import hashlib


logger = logging.getLogger(__name__)


class ExperimentBackend(ABC):
    """Abstract base class for experiment tracking backends"""
    
    @abstractmethod
    def start_run(self, run_name: str, experiment_name: str, tags: Dict[str, str] = None):
        pass
    
    @abstractmethod
    def log_params(self, params: Dict[str, Any]):
        pass
    
    @abstractmethod
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        pass
    
    @abstractmethod
    def log_artifact(self, artifact_path: str, artifact_type: str = "model"):
        pass
    
    @abstractmethod
    def log_text(self, text: str, artifact_name: str):
        pass
    
    @abstractmethod
    def end_run(self, status: str = "FINISHED"):
        pass
    
    @abstractmethod
    def get_run_id(self) -> str:
        pass


class MLflowBackend(ExperimentBackend):
    """MLflow tracking backend"""
    
    def __init__(self):
        try:
            import mlflow
            import mlflow.tracking
            self.mlflow = mlflow
            
            # Configure MLflow
            tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
            self.mlflow.set_tracking_uri(tracking_uri)
            
            self.current_run = None
            logger.info(f"MLflow backend initialized with URI: {tracking_uri}")
            
        except ImportError:
            raise ImportError("MLflow not installed. Run: pip install mlflow")
    
    def start_run(self, run_name: str, experiment_name: str, tags: Dict[str, str] = None):
        # Set or create experiment
        try:
            experiment_id = self.mlflow.get_experiment_by_name(experiment_name).experiment_id
        except AttributeError:
            experiment_id = self.mlflow.create_experiment(experiment_name)
        
        self.current_run = self.mlflow.start_run(
            experiment_id=experiment_id,
            run_name=run_name,
            tags=tags or {}
        )
        
        logger.info(f"Started MLflow run: {run_name} in experiment: {experiment_name}")
    
    def log_params(self, params: Dict[str, Any]):
        if not self.current_run:
            raise RuntimeError("No active run. Call start_run() first.")
        
        # MLflow has limitations on param value types
        str_params = {k: str(v) for k, v in params.items()}
        self.mlflow.log_params(str_params)
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        if not self.current_run:
            raise RuntimeError("No active run. Call start_run() first.")
        
        for name, value in metrics.items():
            self.mlflow.log_metric(name, value, step=step)
    
    def log_artifact(self, artifact_path: str, artifact_type: str = "model"):
        if not self.current_run:
            raise RuntimeError("No active run. Call start_run() first.")
        
        if os.path.isfile(artifact_path):
            self.mlflow.log_artifact(artifact_path)
        elif os.path.isdir(artifact_path):
            self.mlflow.log_artifacts(artifact_path)
        
        # Log artifact metadata
        self.mlflow.set_tag(f"artifact_{Path(artifact_path).name}_type", artifact_type)
    
    def log_text(self, text: str, artifact_name: str):
        if not self.current_run:
            raise RuntimeError("No active run. Call start_run() first.")
        
        self.mlflow.log_text(text, artifact_name)
    
    def end_run(self, status: str = "FINISHED"):
        if self.current_run:
            self.mlflow.end_run(status=status)
            self.current_run = None
    
    def get_run_id(self) -> str:
        if not self.current_run:
            raise RuntimeError("No active run")
        return self.current_run.info.run_id


class WandBBackend(ExperimentBackend):
    """Weights & Biases tracking backend"""
    
    def __init__(self):
        try:
            import wandb
            self.wandb = wandb
            
            # Configure W&B
            api_key = os.getenv('WANDB_API_KEY')
            if api_key:
                self.wandb.login(key=api_key)
            
            self.current_run = None
            logger.info("W&B backend initialized")
            
        except ImportError:
            raise ImportError("Weights & Biases not installed. Run: pip install wandb")
    
    def start_run(self, run_name: str, experiment_name: str, tags: Dict[str, str] = None):
        self.current_run = self.wandb.init(
            project=experiment_name,
            name=run_name,
            tags=list(tags.values()) if tags else None,
            config={}
        )
        
        logger.info(f"Started W&B run: {run_name} in project: {experiment_name}")
    
    def log_params(self, params: Dict[str, Any]):
        if not self.current_run:
            raise RuntimeError("No active run. Call start_run() first.")
        
        self.wandb.config.update(params)
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        if not self.current_run:
            raise RuntimeError("No active run. Call start_run() first.")
        
        log_dict = metrics.copy()
        if step is not None:
            log_dict['step'] = step
        
        self.wandb.log(log_dict)
    
    def log_artifact(self, artifact_path: str, artifact_type: str = "model"):
        if not self.current_run:
            raise RuntimeError("No active run. Call start_run() first.")
        
        artifact = self.wandb.Artifact(
            name=Path(artifact_path).name,
            type=artifact_type
        )
        
        if os.path.isfile(artifact_path):
            artifact.add_file(artifact_path)
        elif os.path.isdir(artifact_path):
            artifact.add_dir(artifact_path)
        
        self.wandb.log_artifact(artifact)
    
    def log_text(self, text: str, artifact_name: str):
        if not self.current_run:
            raise RuntimeError("No active run. Call start_run() first.")
        
        # W&B doesn't have direct text logging, use artifact
        temp_file = f"/tmp/{artifact_name}.txt"
        with open(temp_file, 'w') as f:
            f.write(text)
        
        artifact = self.wandb.Artifact(artifact_name, type="text")
        artifact.add_file(temp_file)
        self.wandb.log_artifact(artifact)
        
        os.remove(temp_file)
    
    def end_run(self, status: str = "FINISHED"):
        if self.current_run:
            self.wandb.finish()
            self.current_run = None
    
    def get_run_id(self) -> str:
        if not self.current_run:
            raise RuntimeError("No active run")
        return self.current_run.id


class InternalBackend(ExperimentBackend):
    """Internal JSON-based tracking backend"""
    
    def __init__(self, storage_path: str = "ml-platform/experiments"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.current_run = None
        self.run_data = {}
        
        logger.info(f"Internal backend initialized with storage: {self.storage_path}")
    
    def start_run(self, run_name: str, experiment_name: str, tags: Dict[str, str] = None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = f"{experiment_name}_{run_name}_{timestamp}"
        
        self.current_run = run_id
        self.run_data = {
            'run_id': run_id,
            'run_name': run_name,
            'experiment_name': experiment_name,
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'status': 'RUNNING',
            'tags': tags or {},
            'params': {},
            'metrics': [],
            'artifacts': [],
            'logs': []
        }
        
        logger.info(f"Started internal run: {run_name} (ID: {run_id})")
    
    def log_params(self, params: Dict[str, Any]):
        if not self.current_run:
            raise RuntimeError("No active run. Call start_run() first.")
        
        self.run_data['params'].update(params)
        self._save_run_data()
    
    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        if not self.current_run:
            raise RuntimeError("No active run. Call start_run() first.")
        
        metric_entry = {
            'timestamp': datetime.now().isoformat(),
            'step': step,
            'metrics': metrics
        }
        
        self.run_data['metrics'].append(metric_entry)
        self._save_run_data()
    
    def log_artifact(self, artifact_path: str, artifact_type: str = "model"):
        if not self.current_run:
            raise RuntimeError("No active run. Call start_run() first.")
        
        # Calculate file hash for integrity
        if os.path.exists(artifact_path):
            with open(artifact_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            artifact_info = {
                'path': str(artifact_path),
                'type': artifact_type,
                'size_bytes': os.path.getsize(artifact_path),
                'sha256': file_hash,
                'logged_at': datetime.now().isoformat()
            }
            
            self.run_data['artifacts'].append(artifact_info)
            self._save_run_data()
    
    def log_text(self, text: str, artifact_name: str):
        if not self.current_run:
            raise RuntimeError("No active run. Call start_run() first.")
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'name': artifact_name,
            'content': text
        }
        
        self.run_data['logs'].append(log_entry)
        self._save_run_data()
    
    def end_run(self, status: str = "FINISHED"):
        if self.current_run:
            self.run_data['end_time'] = datetime.now().isoformat()
            self.run_data['status'] = status
            self._save_run_data()
            
            logger.info(f"Ended run {self.current_run} with status: {status}")
            self.current_run = None
    
    def get_run_id(self) -> str:
        if not self.current_run:
            raise RuntimeError("No active run")
        return self.current_run
    
    def _save_run_data(self):
        """Save run data to JSON file"""
        if self.current_run:
            run_file = self.storage_path / f"{self.current_run}.json"
            with open(run_file, 'w') as f:
                json.dump(self.run_data, f, indent=2)


class ExperimentTracker:
    """Main experiment tracking interface"""
    
    def __init__(self, backend: str = "internal", **kwargs):
        self.backend_name = backend
        
        if backend == "mlflow":
            self.backend = MLflowBackend()
        elif backend == "wandb":
            self.backend = WandBBackend()
        elif backend == "internal":
            self.backend = InternalBackend(**kwargs)
        else:
            raise ValueError(f"Unsupported backend: {backend}")
        
        self.training_config = {}
        self.dataset_info = {}
    
    def start_experiment(self, job_config: Dict[str, Any]):
        """Start experiment from training job config"""
        experiment_config = job_config.get('experiment', {})
        
        run_name = experiment_config.get('run_name', job_config['job_id'])
        experiment_name = experiment_config.get('experiment_name', 'gameforge-training')
        tags = experiment_config.get('tags', [])
        
        # Convert tags list to dict
        tag_dict = {f"tag_{i}": tag for i, tag in enumerate(tags)}
        tag_dict.update({
            'job_id': job_config['job_id'],
            'platform': job_config['environment']['platform'],
            'model_base': job_config['model']['base_model'],
            'dataset': job_config['dataset']['primary']
        })
        
        self.backend.start_run(run_name, experiment_name, tag_dict)
        
        # Log all training parameters
        self._log_training_config(job_config)
    
    def _log_training_config(self, job_config: Dict[str, Any]):
        """Log comprehensive training configuration"""
        # Flatten nested config for logging
        params = {}
        
        # Training parameters
        training = job_config.get('training', {})
        for key, value in training.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    params[f"training.{key}.{sub_key}"] = sub_value
            else:
                params[f"training.{key}"] = value
        
        # Model parameters
        model = job_config.get('model', {})
        for key, value in model.items():
            params[f"model.{key}"] = value
        
        # Dataset parameters
        dataset = job_config.get('dataset', {})
        for key, value in dataset.items():
            if not isinstance(value, (dict, list)):
                params[f"dataset.{key}"] = value
        
        # Environment parameters
        env = job_config.get('environment', {})
        for key, value in env.items():
            params[f"environment.{key}"] = value
        
        self.backend.log_params(params)
    
    def log_training_metrics(self, metrics: Dict[str, float], step: int):
        """Log training metrics with step"""
        self.backend.log_metrics(metrics, step=step)
    
    def log_evaluation_results(self, eval_results: Dict[str, Any], step: Optional[int] = None):
        """Log evaluation results"""
        # Separate numeric metrics from other data
        numeric_metrics = {}
        text_data = {}
        
        for key, value in eval_results.items():
            if isinstance(value, (int, float)):
                numeric_metrics[f"eval_{key}"] = float(value)
            else:
                text_data[key] = str(value)
        
        if numeric_metrics:
            self.backend.log_metrics(numeric_metrics, step=step)
        
        # Log text data as artifacts
        for key, value in text_data.items():
            self.backend.log_text(value, f"eval_{key}")
    
    def log_model_artifact(self, model_path: str, model_type: str = "lora_weights"):
        """Log model artifacts"""
        self.backend.log_artifact(model_path, artifact_type=model_type)
    
    def log_training_logs(self, log_content: str):
        """Log training logs"""
        self.backend.log_text(log_content, "training_logs")
    
    def log_dataset_info(self, dataset_manifest: Dict[str, Any]):
        """Log dataset information"""
        self.dataset_info = dataset_manifest
        
        # Log dataset metadata as parameters
        dataset_params = {}
        for dataset_name, dataset_info in dataset_manifest.get('datasets', {}).items():
            dataset_params[f"dataset_{dataset_name}_version"] = dataset_info.get('version')
            dataset_params[f"dataset_{dataset_name}_size_shards"] = len(dataset_info.get('shards', []))
            dataset_params[f"dataset_{dataset_name}_license"] = dataset_info.get('license', {}).get('type')
        
        self.backend.log_params(dataset_params)
    
    def end_experiment(self, status: str = "FINISHED"):
        """End experiment tracking"""
        self.backend.end_run(status)
    
    def get_current_run_id(self) -> str:
        """Get current run ID"""
        return self.backend.get_run_id()
    
    def create_model_card(self, model_info: Dict[str, Any]) -> str:
        """Create model card from experiment data"""
        model_card = f"""# Model Card: {model_info.get('name', 'Unknown Model')}

## Model Information
- **Model ID**: {model_info.get('model_id', 'N/A')}
- **Version**: {model_info.get('version', '1.0.0')}
- **Created**: {datetime.now().strftime('%Y-%m-%d')}
- **Training Run**: {self.get_current_run_id()}

## Training Configuration
- **Base Model**: {self.training_config.get('model.base_model', 'N/A')}
- **Learning Rate**: {self.training_config.get('training.learning_rate', 'N/A')}
- **Batch Size**: {self.training_config.get('training.batch_size', 'N/A')}
- **Training Method**: {self.training_config.get('training.method', 'N/A')}

## Dataset Information
- **Primary Dataset**: {self.training_config.get('dataset.primary', 'N/A')}
- **Validation Split**: {self.training_config.get('dataset.validation_split', 'N/A')}

## Performance Metrics
*Metrics will be populated during training*

## Usage Guidelines
- **Intended Use**: {model_info.get('intended_use', 'Game content generation')}
- **Limitations**: {model_info.get('limitations', 'See model documentation')}
- **License**: {model_info.get('license', 'Custom GameForge License')}

## Compliance
- **Data Governance**: Reviewed
- **Ethical Considerations**: Evaluated
- **Bias Assessment**: Pending

Generated by GameForge ML Platform - Experiment Tracker
"""
        
        # Log model card as artifact
        self.backend.log_text(model_card, "model_card.md")
        
        return model_card


# Convenience functions for easy integration
def get_tracker(backend: str = None) -> ExperimentTracker:
    """Get experiment tracker instance"""
    if backend is None:
        backend = os.getenv('GAMEFORGE_EXPERIMENT_BACKEND', 'internal')
    
    return ExperimentTracker(backend)


def track_training_job(job_config_path: str, backend: str = None):
    """Decorator/context manager for tracking training jobs"""
    with open(job_config_path, 'r') as f:
        job_config = yaml.safe_load(f)
    
    tracker = get_tracker(backend)
    tracker.start_experiment(job_config)
    
    return tracker


# Example usage
if __name__ == "__main__":
    # Example training integration
    tracker = ExperimentTracker("internal")
    
    # Start experiment
    job_config = {
        'job_id': 'test-experiment',
        'experiment': {
            'experiment_name': 'test-gameforge',
            'run_name': 'llama2-test',
            'tags': ['test', 'llama2']
        },
        'training': {
            'learning_rate': 0.0002,
            'batch_size': 16,
            'method': 'lora'
        },
        'model': {
            'base_model': 'llama2-7b'
        },
        'dataset': {
            'primary': 'gameforge-rpg-v1'
        },
        'environment': {
            'platform': 'local'
        }
    }
    
    tracker.start_experiment(job_config)
    
    # Log training metrics
    for step in range(1, 101):
        metrics = {
            'loss': 2.0 - (step * 0.01),
            'perplexity': 7.0 - (step * 0.03),
            'learning_rate': 0.0002
        }
        tracker.log_training_metrics(metrics, step)
    
    # Log evaluation results
    eval_results = {
        'bleu_score': 0.75,
        'rouge_l': 0.68,
        'human_eval': 'Good quality generations'
    }
    tracker.log_evaluation_results(eval_results)
    
    # Create model card
    model_info = {
        'name': 'LLaMA 2 7B GameForge',
        'model_id': 'llama2-7b-gameforge-v1',
        'version': '1.0.0',
        'intended_use': 'RPG content generation',
        'license': 'GameForge Internal'
    }
    
    model_card = tracker.create_model_card(model_info)
    print("Generated Model Card:")
    print(model_card)
    
    # End experiment
    tracker.end_experiment("FINISHED")
    
    print(f"Experiment completed with run ID: {tracker.get_current_run_id()}")