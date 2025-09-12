# GameForge Dataset Versioning API Guide
=========================================

This document provides comprehensive information about the Dataset Versioning API with DVC integration.

## Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [API Endpoints](#api-endpoints)
4. [Usage Examples](#usage-examples)
5. [Data Validation](#data-validation)
6. [Drift Detection](#drift-detection)
7. [Lineage Tracking](#lineage-tracking)
8. [Best Practices](#best-practices)

## Overview

The GameForge Dataset Versioning API provides enterprise-grade dataset management with:

- **DVC Integration**: Version control for datasets with S3 backend
- **Data Validation**: Comprehensive quality checks with configurable rules
- **Drift Detection**: Statistical analysis to detect data distribution changes
- **Lineage Tracking**: Complete audit trail of dataset transformations
- **RESTful API**: Easy integration with ML pipelines and applications

### Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   ML Pipeline   │────│  Dataset API     │────│   PostgreSQL    │
│                 │    │                  │    │   (Metadata)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │
                       ┌──────────────────┐    ┌─────────────────┐
                       │   DVC + S3       │────│     Redis       │
                       │  (Data Storage)  │    │    (Cache)      │
                       └──────────────────┘    └─────────────────┘
```

## Quick Start

### 1. Start the Services

```bash
# Build and deploy
.\deploy-dataset-versioning.ps1 -Build -Deploy

# Test deployment
.\deploy-dataset-versioning.ps1 -Test
```

### 2. Upload Your First Dataset

```python
import requests

# Upload a dataset
with open('my_dataset.csv', 'rb') as f:
    files = {'file': f}
    data = {
        'name': 'game-player-data',
        'version': 'v1.0.0',
        'description': 'Player behavior dataset for AI training',
        'tags': '{"model_type": "behavior", "source": "game_logs"}'
    }
    response = requests.post('http://localhost:8080/datasets', files=files, data=data)
    print(response.json())
```

### 3. List and Download Datasets

```python
# List all datasets
response = requests.get('http://localhost:8080/datasets')
datasets = response.json()

# Download a specific version
response = requests.get('http://localhost:8080/datasets/game-player-data/versions/v1.0.0/download')
with open('downloaded_dataset.csv', 'wb') as f:
    f.write(response.content)
```

## API Endpoints

### Core Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/datasets` | Upload and create new dataset version |
| GET | `/datasets` | List all datasets with summary |
| GET | `/datasets/{name}/versions` | List versions of specific dataset |
| GET | `/datasets/{name}/versions/{version}` | Get dataset version details |
| GET | `/datasets/{name}/versions/{version}/download` | Download dataset version |
| DELETE | `/datasets/{name}/versions/{version}` | Mark version as deprecated |

### Analysis Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/datasets/{name}/versions/{version}/validation` | Get validation results |
| POST | `/datasets/{name}/drift-analysis` | Analyze drift between versions |
| GET | `/datasets/{name}/versions/{version}/lineage` | Get dataset lineage |
| GET | `/datasets/{name}/drift-history` | Get drift analysis history |
| GET | `/datasets/{name}/usage` | Get dataset usage statistics |

### System Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |
| GET | `/docs` | API documentation (Swagger UI) |

## Usage Examples

### 1. Game AI Model Dataset

```python
import requests
import json

# Upload training data for NPC behavior model
with open('npc_behavior_training.parquet', 'rb') as f:
    files = {'file': f}
    data = {
        'name': 'npc-behavior-training',
        'version': 'v1.0.0',
        'description': 'NPC behavior patterns for AI training',
        'tags': json.dumps({
            'model_type': 'npc-behavior',
            'data_source': 'game_telemetry',
            'player_count': '10000',
            'sessions': '50000'
        })
    }
    response = requests.post('http://localhost:8080/datasets', files=files, data=data)
    print(f"Dataset uploaded: {response.json()}")

# Check validation results
response = requests.get('http://localhost:8080/datasets/npc-behavior-training/versions/v1.0.0/validation')
validation = response.json()
print(f"Validation status: {validation['status']}")
print(f"Quality score: {validation['summary'].get('quality_score', 'N/A')}")
```

### 2. Dataset Evolution with Drift Detection

```python
# Upload updated version of the dataset
with open('npc_behavior_training_v2.parquet', 'rb') as f:
    files = {'file': f}
    data = {
        'name': 'npc-behavior-training',
        'version': 'v2.0.0',
        'description': 'Updated NPC behavior with new game features',
        'tags': json.dumps({
            'model_type': 'npc-behavior',
            'data_source': 'game_telemetry',
            'player_count': '15000',
            'sessions': '75000',
            'features_added': 'combat_behavior,exploration_patterns'
        }),
        'parent_datasets': json.dumps([
            {'name': 'npc-behavior-training', 'version': 'v1.0.0'}
        ])
    }
    response = requests.post('http://localhost:8080/datasets', files=files, data=data)

# Analyze drift between versions
response = requests.post('http://localhost:8080/datasets/npc-behavior-training/drift-analysis', 
                        params={
                            'baseline_version': 'v1.0.0',
                            'current_version': 'v2.0.0'
                        })
drift_analysis = response.json()
print(f"Overall drift score: {drift_analysis['overall_drift_score']}")
print(f"Drift status: {drift_analysis['drift_status']}")

# Get detailed column-level drift
for column, drift_info in drift_analysis['column_drifts'].items():
    print(f"{column}: {drift_info['drift_score']:.3f} ({drift_info['test_name']})")
```

### 3. Procedural Generation Dataset with Lineage

```python
# Upload base procedural generation data
with open('proc_gen_base.json', 'rb') as f:
    files = {'file': f}
    data = {
        'name': 'procedural-generation-base',
        'version': 'v1.0.0',
        'description': 'Base parameters for procedural world generation',
        'tags': json.dumps({
            'model_type': 'procedural-generation',
            'content_type': 'world_parameters',
            'biome_count': '8',
            'asset_variations': '500'
        })
    }
    response = requests.post('http://localhost:8080/datasets', files=files, data=data)

# Upload derived dataset with enhanced parameters
with open('proc_gen_enhanced.json', 'rb') as f:
    files = {'file': f}
    data = {
        'name': 'procedural-generation-enhanced',
        'version': 'v1.0.0',
        'description': 'Enhanced procedural generation with AI optimization',
        'tags': json.dumps({
            'model_type': 'procedural-generation',
            'content_type': 'optimized_parameters',
            'biome_count': '12',
            'asset_variations': '1200',
            'optimization_method': 'genetic_algorithm'
        }),
        'parent_datasets': json.dumps([
            {'name': 'procedural-generation-base', 'version': 'v1.0.0'}
        ])
    }
    response = requests.post('http://localhost:8080/datasets', files=files, data=data)

# Get lineage information
response = requests.get('http://localhost:8080/datasets/procedural-generation-enhanced/versions/v1.0.0/lineage')
lineage = response.json()
print(f"Dataset: {lineage['dataset_name']} v{lineage['version']}")
print(f"Parent datasets: {lineage['parent_datasets']}")
print(f"Created at: {lineage['created_at']}")
```

## Data Validation

The API automatically validates datasets using configurable rules defined in `dataset-validation.yaml`.

### Validation Categories

1. **Completeness**: Missing values, null percentages
2. **Consistency**: Data type consistency, format validation
3. **Validity**: Range checks, enumeration validation
4. **Accuracy**: Statistical outlier detection
5. **Uniqueness**: Duplicate detection

### Custom Validation Rules

Edit `ml-platform/config/dataset-validation.yaml`:

```yaml
datasets:
  my-custom-dataset:
    completeness:
      max_null_percentage: 0.05  # 5% max null values
      required_columns: ["id", "timestamp", "value"]
    
    consistency:
      column_types:
        id: "string"
        timestamp: "datetime"
        value: "numeric"
    
    validity:
      ranges:
        value: [0, 1000]
      enums:
        category: ["A", "B", "C"]
    
    accuracy:
      outlier_detection:
        method: "iqr"
        multiplier: 1.5
```

## Drift Detection

The system detects distribution changes between dataset versions using statistical tests:

### Numerical Columns
- **Kolmogorov-Smirnov Test**: Detects distribution shape changes
- **Welch's T-Test**: Detects mean differences
- **F-Test**: Detects variance changes

### Categorical Columns
- **Chi-Square Test**: Detects frequency distribution changes
- **Cramer's V**: Measures association strength

### Drift Thresholds

| Drift Score | Status | Meaning |
|-------------|---------|---------|
| 0.0 - 0.1 | No Drift | Distributions are very similar |
| 0.1 - 0.3 | Low Drift | Minor distribution changes |
| 0.3 - 0.7 | Medium Drift | Moderate distribution changes |
| 0.7 - 1.0 | High Drift | Significant distribution changes |

### Example: Monitoring Drift Over Time

```python
# Get drift history for the last 30 days
response = requests.get('http://localhost:8080/datasets/npc-behavior-training/drift-history?days=30')
drift_history = response.json()

# Plot drift over time
import matplotlib.pyplot as plt
import pandas as pd

df = pd.DataFrame(drift_history['drift_history'])
df['created_at'] = pd.to_datetime(df['created_at'])

plt.figure(figsize=(12, 6))
plt.plot(df['created_at'], df['drift_score'], marker='o')
plt.axhline(y=0.3, color='orange', linestyle='--', label='Medium Drift Threshold')
plt.axhline(y=0.7, color='red', linestyle='--', label='High Drift Threshold')
plt.xlabel('Date')
plt.ylabel('Drift Score')
plt.title('Dataset Drift Over Time')
plt.legend()
plt.show()
```

## Lineage Tracking

Track complete dataset lineage from raw data to final training datasets:

```python
# Get full lineage tree
def get_lineage_tree(dataset_name, version):
    response = requests.get(f'http://localhost:8080/datasets/{dataset_name}/versions/{version}/lineage')
    lineage = response.json()
    
    tree = {
        'dataset': f"{dataset_name}:{version}",
        'created_at': lineage['created_at'],
        'parents': []
    }
    
    for parent in lineage['parent_datasets']:
        parent_tree = get_lineage_tree(parent['name'], parent['version'])
        tree['parents'].append(parent_tree)
    
    return tree

# Visualize lineage
lineage_tree = get_lineage_tree('procedural-generation-enhanced', 'v1.0.0')
print(json.dumps(lineage_tree, indent=2))
```

## Best Practices

### 1. Dataset Naming Convention

```
{domain}-{model_type}-{data_type}
└─ Examples:
   ├── game-ai-training
   ├── npc-behavior-inference
   ├── procedural-generation-parameters
   └── player-analytics-features
```

### 2. Version Naming

```
v{major}.{minor}.{patch}[-{suffix}]
└─ Examples:
   ├── v1.0.0          # Initial release
   ├── v1.1.0          # Feature addition
   ├── v1.0.1          # Bug fix/cleanup
   └── v2.0.0-beta     # Major changes (pre-release)
```

### 3. Metadata Tagging

```python
tags = {
    # Required tags
    "model_type": "npc-behavior|procedural-generation|game-ai",
    "data_source": "game_telemetry|user_logs|synthetic",
    
    # Optional descriptive tags
    "environment": "production|staging|development",
    "quality": "high|medium|low",
    "player_segment": "casual|hardcore|new",
    "game_mode": "single_player|multiplayer|coop",
    
    # Technical metadata
    "format": "parquet|csv|json|hdf5",
    "compression": "gzip|snappy|none",
    "size_category": "small|medium|large|xlarge"
}
```

### 4. Validation Strategy

1. **Pre-upload Validation**: Check data quality before uploading
2. **Automated Validation**: Use API validation for consistent checks
3. **Custom Rules**: Define domain-specific validation rules
4. **Continuous Monitoring**: Set up alerts for validation failures

### 5. Drift Monitoring

1. **Baseline Management**: Establish stable baselines for comparison
2. **Threshold Tuning**: Adjust drift thresholds based on domain knowledge
3. **Regular Analysis**: Schedule periodic drift analysis
4. **Alert Integration**: Connect to monitoring systems for drift alerts

### 6. Performance Optimization

1. **Data Formats**: Use Parquet for large datasets, CSV for small ones
2. **Compression**: Enable compression for storage efficiency
3. **Chunking**: Split very large datasets into manageable chunks
4. **Caching**: Leverage Redis caching for frequently accessed metadata

### 7. Security Considerations

1. **Access Control**: Implement proper authentication and authorization
2. **Data Encryption**: Use encryption for sensitive datasets
3. **Audit Logging**: Enable comprehensive audit trails
4. **Network Security**: Use HTTPS and secure network configurations

### 8. Integration Patterns

```python
# Example: ML Pipeline Integration
class DatasetManager:
    def __init__(self, api_base_url):
        self.api_url = api_base_url
    
    def get_latest_training_data(self, dataset_name):
        """Get latest version of training dataset"""
        response = requests.get(f'{self.api_url}/datasets/{dataset_name}/versions/latest')
        if response.status_code == 200:
            version_info = response.json()
            # Download and return dataset
            download_response = requests.get(
                f'{self.api_url}/datasets/{dataset_name}/versions/{version_info["version"]}/download'
            )
            return download_response.content
        return None
    
    def check_drift_before_training(self, dataset_name, baseline_version):
        """Check for drift before starting training"""
        latest_response = requests.get(f'{self.api_url}/datasets/{dataset_name}/versions/latest')
        latest_version = latest_response.json()['version']
        
        drift_response = requests.post(
            f'{self.api_url}/datasets/{dataset_name}/drift-analysis',
            params={'baseline_version': baseline_version, 'current_version': latest_version}
        )
        
        drift_analysis = drift_response.json()
        if drift_analysis['overall_drift_score'] > 0.7:
            raise ValueError(f"High drift detected: {drift_analysis['overall_drift_score']}")
        
        return drift_analysis

# Usage in ML pipeline
dm = DatasetManager('http://localhost:8080')
training_data = dm.get_latest_training_data('npc-behavior-training')
drift_check = dm.check_drift_before_training('npc-behavior-training', 'v1.0.0')
```

## Error Handling

The API returns standard HTTP status codes with detailed error messages:

- **200**: Success
- **400**: Bad Request (invalid parameters, validation failures)
- **404**: Not Found (dataset/version doesn't exist)
- **409**: Conflict (version already exists)
- **500**: Internal Server Error

```python
# Example error handling
try:
    response = requests.post('http://localhost:8080/datasets', files=files, data=data)
    response.raise_for_status()  # Raises HTTPError for bad status codes
    result = response.json()
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 400:
        error_detail = e.response.json().get('detail', 'Unknown error')
        print(f"Validation failed: {error_detail}")
    elif e.response.status_code == 409:
        print("Dataset version already exists")
    else:
        print(f"API error: {e}")
except requests.exceptions.RequestException as e:
    print(f"Network error: {e}")
```

---

For more information, visit the interactive API documentation at `http://localhost:8080/docs` when the service is running.