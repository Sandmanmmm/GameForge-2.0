# GameForge ML Platform - Complete Lifecycle Management

## Overview

The GameForge ML Platform provides comprehensive machine learning lifecycle management with automated **train → eval → deploy → monitor → archive** cycles. This system includes model registry, experiment tracking, monitoring, drift detection, and automated archival for production ML operations.

## 🚀 Quick Start

### 1. Initialize ML Platform

```bash
# Set up Python environment
python -m ml_platform.setup

# Initialize model registry
python -m ml_platform.registry.registry_manager register \
  --name "my-model" \
  --version "1.0.0" \
  --framework "pytorch" \
  --model-uri "s3://models/my-model.pth" \
  --description "My ML model" \
  --author "developer@gameforge.dev"

# Establish monitoring baseline
python -m ml_platform.monitoring.drift_detector baseline \
  --model-id "abc123" \
  --data-file "baseline_data.csv"
```

### 2. Train and Track Experiments

```bash
# Submit training job
python -m ml_platform.training.training_manager submit \
  --job-file "jobs/llama2-lora-training.yaml" \
  --platform "vastai"

# Track experiment
python -c "
from ml_platform.training.scripts.experiment_tracker import ExperimentTracker
tracker = ExperimentTracker()
tracker.start_experiment('my-experiment', {'lr': 0.001})
tracker.log_metrics({'loss': 0.5, 'accuracy': 0.9})
tracker.end_experiment()
"
```

### 3. Promote Model Through Environments

```bash
# Request promotion to staging
python -m ml_platform.registry.registry_manager promote \
  --model-id "abc123" \
  --to-stage "staging" \
  --requestor "ml-engineer@gameforge.dev" \
  --justification "Model passed all tests"

# Approve promotion (as authorized approver)
python -m ml_platform.registry.registry_manager approve \
  --request-id "promo-abc123-20241209" \
  --approver "ml-lead@gameforge.dev"
```

### 4. Monitor Production Model

```bash
# Monitor for drift
python -m ml_platform.monitoring.drift_detector drift \
  --model-id "abc123" \
  --data-file "production_data.csv"

# Generate monitoring report
python -m ml_platform.monitoring.drift_detector report \
  --model-id "abc123" \
  --days 7
```

### 5. Archive and Cleanup

```bash
# Scan for large files
python -m ml_platform.archival.archival_manager scan \
  --directory "." \
  --threshold 100

# Cleanup old artifacts
python -m ml_platform.archival.archival_manager cleanup \
  --directory "experiments/" \
  --dry-run

# Generate git cleanup script
python -m ml_platform.archival.archival_manager git-cleanup \
  --repo "." \
  --output "cleanup_git.sh"
```

## 📁 Directory Structure

```
ml-platform/
├── training/                    # Training orchestration
│   ├── jobs/                   # Training job manifests
│   │   └── llama2-lora-training.yaml
│   └── scripts/
│       ├── training_manager.py  # Multi-platform training manager
│       └── experiment_tracker.py # Unified experiment tracking
├── registry/                   # Model registry and promotion
│   ├── registry-config.yaml    # Registry configuration
│   └── registry_manager.py     # Model lifecycle management
├── monitoring/                 # Monitoring and drift detection
│   ├── monitoring-config.yaml  # Monitoring configuration
│   └── drift_detector.py       # Data/concept drift detection
└── archival/                   # Archival and cleanup
    ├── archival-config.yaml    # Archival policies
    └── archival_manager.py     # Automated cleanup system
```

## 🔄 ML Lifecycle Stages

### 1. **Train** - Training Job Management

**Features:**
- Multi-platform support (Vast.ai, local GPU, cloud)
- Dataset validation and consistency checking
- Automated hyperparameter tracking
- Resource optimization and cost management

**Example Training Job:**
```yaml
# jobs/my-training-job.yaml
job_name: "llama2-lora-finetuning"
model:
  base_model: "meta-llama/Llama-2-7b-hf"
  architecture: "transformer"
  framework: "pytorch"

training:
  method: "lora"
  epochs: 3
  batch_size: 4
  learning_rate: 0.0002

platform:
  provider: "vastai"
  instance_type: "RTX4090"
  max_cost_per_hour: 0.50
```

**Submit Training:**
```bash
python -m ml_platform.training.training_manager submit \
  --job-file "jobs/my-training-job.yaml" \
  --platform "vastai"
```

### 2. **Eval** - Experiment Tracking

**Features:**
- Multi-backend support (MLflow, Weights & Biases, Internal)
- Automatic parameter and metric logging
- Model card generation
- Performance benchmarking

**Track Experiment:**
```python
from ml_platform.training.scripts.experiment_tracker import ExperimentTracker

tracker = ExperimentTracker(backend="mlflow")
tracker.start_experiment("model-evaluation", {
    "model_type": "llama2-lora",
    "dataset": "alpaca-cleaned",
    "batch_size": 16
})

# Log metrics during training
tracker.log_metrics({
    "epoch": 1,
    "train_loss": 0.45,
    "val_loss": 0.52,
    "perplexity": 3.2
})

# Log artifacts
tracker.log_artifact("model.pth", "models/")
tracker.log_model_card({
    "model_name": "Llama2-Alpaca-LoRA",
    "performance": {"perplexity": 3.2},
    "intended_use": "Instruction following"
})

tracker.end_experiment()
```

### 3. **Deploy** - Model Registry & Promotion

**Features:**
- Multi-environment promotion pipeline (dev → staging → production)
- Approval workflows with role-based access
- Performance gates and quality checks
- Automated deployment and rollback

**Model Promotion Pipeline:**
```bash
# 1. Register model
MODEL_ID=$(python -m ml_platform.registry.registry_manager register \
  --name "llama2-alpaca" \
  --version "1.2.0" \
  --framework "pytorch" \
  --model-uri "s3://models/llama2-alpaca-v1.2.pth" \
  --description "Llama2 fine-tuned on Alpaca dataset" \
  --author "ml-team@gameforge.dev")

# 2. Request staging promotion
python -m ml_platform.registry.registry_manager promote \
  --model-id "$MODEL_ID" \
  --to-stage "staging" \
  --requestor "ml-engineer@gameforge.dev" \
  --justification "Passed all evaluation benchmarks"

# 3. Approve promotion (requires authorized approver)
python -m ml_platform.registry.registry_manager approve \
  --request-id "promo-$MODEL_ID-staging" \
  --approver "ml-lead@gameforge.dev"

# 4. Production promotion (requires multiple approvals)
python -m ml_platform.registry.registry_manager promote \
  --model-id "$MODEL_ID" \
  --to-stage "production" \
  --requestor "ml-lead@gameforge.dev" \
  --justification "Staging validation successful"
```

### 4. **Monitor** - Monitoring & Drift Detection

**Features:**
- Real-time performance monitoring
- Data drift detection (feature distribution changes)
- Concept drift detection (target distribution changes)
- Automated alerting and remediation

**Establish Baseline:**
```bash
# Create monitoring baseline from historical data
python -m ml_platform.monitoring.drift_detector baseline \
  --model-id "$MODEL_ID" \
  --data-file "historical_data.csv" \
  --target-column "target"
```

**Monitor Production Data:**
```python
from ml_platform.monitoring.drift_detector import MLMonitor
import pandas as pd

monitor = MLMonitor()

# Load production data
current_data = pd.read_csv("production_data.csv")

# Detect drift
drift_results = monitor.detect_data_drift(
    model_id="abc123",
    current_data=current_data
)

# Check for issues
for result in drift_results:
    if result.drift_detected:
        print(f"⚠️  Drift detected in {result.metric_name}")
        print(f"   Severity: {result.severity}")
        print(f"   Score: {result.drift_score:.3f}")
        print(f"   Actions: {result.recommended_actions}")
```

**Track Model Performance:**
```python
import numpy as np

# Track predictions and performance
predictions = np.array([1, 0, 1, 1, 0])
ground_truth = np.array([1, 0, 1, 0, 0])
inference_times = [0.12, 0.08, 0.15, 0.09, 0.11]

metrics = monitor.track_model_performance(
    model_id="abc123",
    predictions=predictions,
    ground_truth=ground_truth,
    inference_times=inference_times,
    custom_metrics={"toxicity_score": 0.02}
)

print(f"Accuracy: {metrics.accuracy:.3f}")
print(f"Latency P95: {metrics.latency_p95:.3f}s")
```

### 5. **Archive** - Automated Archival & Cleanup

**Features:**
- Automated archival based on configurable policies
- Large file detection and S3 migration
- Git repository cleanup and optimization
- Compliance and retention management

**Scan for Large Files:**
```bash
# Find large files that should be archived
python -m ml_platform.archival.archival_manager scan \
  --directory "." \
  --threshold 100  # Files > 100MB

# Example output:
# 🔍 Large Files Report:
#    Found: 5 files
#    Total size: 2.3 GB
#    models/llama2.pth: 1200.5 MB 📝 tracked → migrate_to_lfs_and_s3
#    data/train.parquet: 890.2 MB 📁 untracked → move_to_s3
```

**Migrate Large Files:**
```bash
# Migrate specific file to S3
python -m ml_platform.archival.archival_manager migrate \
  --file "models/large_model.pth" \
  --keep-local  # Optional: keep local copy

# Automatic cleanup based on policies
python -m ml_platform.archival.archival_manager cleanup \
  --directory "experiments/" \
  --dry-run  # Preview actions first
```

**Git Repository Cleanup:**
```bash
# Generate git cleanup script
python -m ml_platform.archival.archival_manager git-cleanup \
  --repo "." \
  --output "cleanup_git.sh"

# Review and execute the script
cat cleanup_git.sh
chmod +x cleanup_git.sh
./cleanup_git.sh
```

## ⚙️ Configuration

### Model Registry Configuration

```yaml
# ml-platform/registry/registry-config.yaml
environments:
  staging:
    approval_required: true
    approvers:
      - "ml-lead@gameforge.dev"
    performance_gates:
      - metric: "perplexity"
        operator: "<"
        threshold: 4.0
        required: true

  production:
    approval_required: true
    approvers:
      - "ml-lead@gameforge.dev"
      - "engineering-director@gameforge.dev"
    performance_gates:
      - metric: "perplexity"
        operator: "<"
        threshold: 3.5
        required: true
```

### Monitoring Configuration

```yaml
# ml-platform/monitoring/monitoring-config.yaml
drift_thresholds:
  low: 0.1
  medium: 0.2
  high: 0.3
  critical: 0.5

alerting:
  channels: ["email", "slack"]
  email:
    to: ["ml-team@gameforge.dev"]
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
```

### Archival Configuration

```yaml
# ml-platform/archival/archival-config.yaml
policies:
  - name: "model_artifacts"
    retention_days: 30
    auto_delete_days: 730
    storage_class: "standard_ia"
    file_patterns: ["**/*.pth", "**/*.ckpt"]
```

## 📊 Monitoring Dashboard

### View Registry Statistics

```bash
python -m ml_platform.registry.registry_manager stats

# Output:
# 📊 Registry Statistics:
#    Models by stage: {'development': 5, 'staging': 2, 'production': 1}
#    Models by environment: {'staging': 2, 'production': 1}
#    Deployments (last 7 days): 3
#    Pending promotions: 1
```

### Generate Monitoring Report

```bash
python -m ml_platform.monitoring.drift_detector report \
  --model-id "abc123" \
  --days 7

# Output:
# 📊 Monitoring Report for abc123
#    Period: 2024-12-02 to 2024-12-09
#    Performance: {'avg_accuracy': 0.85, 'accuracy_trend': 'improving'}
#    Drift: {'features_with_drift': 2, 'total_drift_events': 5}
#    Alerts: {'total_alerts': 3}
#    Recommendations: ['Monitor closely', 'Schedule model evaluation']
```

### View Archival Statistics

```bash
python -m ml_platform.archival.archival_manager stats

# Output:
# 📊 Archival Statistics:
#    Archived items: 156
#    Total archived: 12.4 GB
#    Recent cleanup operations: 8
#    Large files discovered: 23
#    Total large file size: 8.7 GB
```

## 🔧 Integration Examples

### CI/CD Integration

```yaml
# .gitlab-ci.yml
stages:
  - train
  - evaluate
  - promote
  - monitor

train_model:
  stage: train
  script:
    - python -m ml_platform.training.training_manager submit --job-file jobs/training.yaml

evaluate_model:
  stage: evaluate
  script:
    - python evaluate.py
    - python -m ml_platform.registry.registry_manager register --name $MODEL_NAME --version $CI_PIPELINE_ID

promote_to_staging:
  stage: promote
  script:
    - python -m ml_platform.registry.registry_manager promote --model-id $MODEL_ID --to-stage staging
  when: manual

setup_monitoring:
  stage: monitor
  script:
    - python -m ml_platform.monitoring.drift_detector baseline --model-id $MODEL_ID
```

### Python API Usage

```python
# Complete lifecycle example
from ml_platform.registry.registry_manager import ModelRegistry
from ml_platform.monitoring.drift_detector import MLMonitor
from ml_platform.archival.archival_manager import MLArchivalManager

# 1. Register model
registry = ModelRegistry()
model_id = registry.register_model(
    name="my-model",
    version="1.0.0",
    framework="pytorch",
    model_uri="s3://models/my-model.pth",
    description="Production model",
    author="ml-team@gameforge.dev"
)

# 2. Set up monitoring
monitor = MLMonitor()
monitor.establish_baseline(model_id, baseline_data)

# 3. Archive old artifacts
archiver = MLArchivalManager()
archiver.cleanup_old_artifacts("experiments/", dry_run=False)
```

## 📚 Documentation

- **Training Jobs**: [ml-platform/training/README.md](ml-platform/training/README.md)
- **Model Registry**: [ml-platform/registry/README.md](ml-platform/registry/README.md)
- **Monitoring**: [ml-platform/monitoring/README.md](ml-platform/monitoring/README.md)
- **Archival**: [ml-platform/archival/README.md](ml-platform/archival/README.md)

## 🛠️ Development

### Setup Development Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Set up pre-commit hooks
pre-commit install

# Run tests
pytest ml-platform/tests/

# Run linting
flake8 ml-platform/
black ml-platform/
```

### Contributing

1. Follow the existing code structure and patterns
2. Add comprehensive tests for new features
3. Update documentation and examples
4. Ensure all lint checks pass
5. Add appropriate logging and error handling

## 🚨 Troubleshooting

### Common Issues

**Large File Detection:**
```bash
# If git operations are slow due to large files
python -m ml_platform.archival.archival_manager scan --directory . --threshold 50
python -m ml_platform.archival.archival_manager git-cleanup --repo .
```

**Monitoring Alerts:**
```bash
# Check monitoring status
python -m ml_platform.monitoring.drift_detector report --model-id abc123

# Reset baselines if needed
python -m ml_platform.monitoring.drift_detector baseline --model-id abc123 --data-file new_baseline.csv
```

**Registry Issues:**
```bash
# List all models and their stages
python -m ml_platform.registry.registry_manager list

# Check promotion status
python -m ml_platform.registry.registry_manager stats
```

### Support

For issues and support:
- Create issues in the GameForge repository
- Contact the ML Platform team: ml-platform@gameforge.dev
- Check the troubleshooting documentation

## 📝 License

See [LICENSE](LICENSE) file for details.