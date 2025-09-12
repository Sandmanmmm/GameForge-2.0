#!/usr/bin/env python3
"""
========================================================================
GameForge AI - Model Externalization and Data Management
Remove models from images and implement runtime download from MinIO
========================================================================
"""

import os
import json
import yaml
import subprocess
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelExternalizer:
    """Externalize models and implement runtime download"""
    
    def __init__(self):
        self.models_config = {
            'text_generation': {
                'model_name': 'microsoft/DialoGPT-medium',
                'size_gb': 1.2,
                'minio_path': 'models/text-generation/dialogpt-medium'
            },
            'image_generation': {
                'model_name': 'runwayml/stable-diffusion-v1-5',
                'size_gb': 4.0,
                'minio_path': 'models/image-generation/stable-diffusion-v1-5'
            },
            'image_analysis': {
                'model_name': 'openai/clip-vit-base-patch32',
                'size_gb': 0.6,
                'minio_path': 'models/image-analysis/clip-vit-base'
            }
        }
    
    def create_model_download_script(self):
        """Create model download script for runtime"""
        
        download_script = '''#!/bin/bash
set -e

# Model download script for GameForge AI
# Downloads models from MinIO at runtime instead of baking into images

echo "=== GameForge AI Model Download Script ==="

# Configuration
MINIO_ENDPOINT=${MINIO_ENDPOINT:-"minio:9000"}
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-"gameforge"}
MINIO_SECRET_KEY=${MINIO_SECRET_KEY:-"gameforge123"}
MODELS_DIR=${MODELS_DIR:-"/app/models"}
MODEL_BUCKET=${MODEL_BUCKET:-"gameforge-models"}

# Install minio client if not present
if ! command -v mc &> /dev/null; then
    echo "Installing MinIO client..."
    wget https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/local/bin/mc
    chmod +x /usr/local/bin/mc
fi

# Configure minio client
echo "Configuring MinIO client..."
mc alias set gameforge-minio http://$MINIO_ENDPOINT $MINIO_ACCESS_KEY $MINIO_SECRET_KEY

# Create models directory
mkdir -p $MODELS_DIR

# Function to download model
download_model() {
    local model_name=$1
    local minio_path=$2
    local local_path="$MODELS_DIR/$model_name"
    
    echo "Checking for model: $model_name"
    
    # Check if model already exists locally
    if [ -d "$local_path" ] && [ "$(ls -A $local_path)" ]; then
        echo "✅ Model $model_name already exists locally"
        return 0
    fi
    
    echo "📥 Downloading model $model_name from MinIO..."
    mkdir -p "$local_path"
    
    # Download model files
    if mc cp --recursive gameforge-minio/$MODEL_BUCKET/$minio_path/ "$local_path/"; then
        echo "✅ Model $model_name downloaded successfully"
    else
        echo "❌ Failed to download model $model_name"
        # Try to download from Hugging Face as fallback
        echo "🔄 Attempting Hugging Face fallback..."
        python3 -c "
from transformers import AutoModel, AutoTokenizer
import os
model_name = '$model_name'
local_path = '$local_path'
try:
    model = AutoModel.from_pretrained(model_name, cache_dir=local_path)
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=local_path)
    print(f'✅ Downloaded {model_name} from Hugging Face')
except Exception as e:
    print(f'❌ Failed to download {model_name}: {e}')
"
    fi
}

# Download all required models
echo "Starting model downloads..."

download_model "dialogpt-medium" "text-generation/dialogpt-medium"
download_model "stable-diffusion-v1-5" "image-generation/stable-diffusion-v1-5"
download_model "clip-vit-base" "image-analysis/clip-vit-base"

echo "=== Model download complete ==="

# Verify models are available
echo "Verifying downloaded models..."
python3 -c "
import os
models_dir = os.environ.get('MODELS_DIR', '/app/models')
required_models = ['dialogpt-medium', 'stable-diffusion-v1-5', 'clip-vit-base']

for model in required_models:
    model_path = os.path.join(models_dir, model)
    if os.path.exists(model_path) and os.listdir(model_path):
        print(f'✅ {model} verified')
    else:
        print(f'❌ {model} missing or empty')
        exit(1)

print('🎉 All models verified successfully')
"

echo "🚀 Ready to start GameForge AI services"
'''
        
        with open('scripts/download-models.sh', 'w', encoding='utf-8') as f:
            f.write(download_script)
        
        # Make executable
        os.chmod('scripts/download-models.sh', 0o755)
        
        logger.info("Model download script created: scripts/download-models.sh")
    
    def create_optimized_dockerfile(self):
        """Create optimized Dockerfile without embedded models"""
        
        dockerfile_content = '''# GameForge AI - Optimized Production Dockerfile
# Models are downloaded at runtime, not embedded in image

FROM python:3.9-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    wget \\
    curl \\
    git \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r gameforge && useradd -r -g gameforge -u 1001 gameforge

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create models directory (will be populated at runtime)
RUN mkdir -p /app/models && chown -R gameforge:gameforge /app

# Copy model download script
COPY scripts/download-models.sh ./
RUN chmod +x download-models.sh

# Switch to non-root user
USER gameforge

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -f http://localhost:8080/health || exit 1

# Download models and start application
CMD ["bash", "-c", "./download-models.sh && python src/app.py"]
'''
        
        with open('Dockerfile.optimized', 'w', encoding='utf-8') as f:
            f.write(dockerfile_content)
        
        logger.info("Optimized Dockerfile created: Dockerfile.optimized")
    
    def create_database_migrations(self):
        """Create database migration system"""
        
        # Create migrations directory structure
        os.makedirs('migrations/versions', exist_ok=True)
        
        # Initial migration
        initial_migration = '''-- GameForge AI Database Schema
-- Initial migration: Create core tables

BEGIN;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings JSONB DEFAULT '{}'::jsonb
);

-- AI generations table
CREATE TABLE IF NOT EXISTS ai_generations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    generation_type VARCHAR(50) NOT NULL, -- 'text', 'image', 'analysis'
    input_data JSONB NOT NULL,
    output_data JSONB,
    model_used VARCHAR(100),
    processing_time_ms INTEGER,
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Model usage tracking
CREATE TABLE IF NOT EXISTS model_usage (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    usage_count INTEGER DEFAULT 1,
    total_processing_time_ms BIGINT DEFAULT 0,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_bucket DATE DEFAULT CURRENT_DATE
);

-- System metrics
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(50) NOT NULL,
    metric_value DECIMAL(10,4) NOT NULL,
    metric_unit VARCHAR(20),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_generations_project_id ON ai_generations(project_id);
CREATE INDEX IF NOT EXISTS idx_ai_generations_status ON ai_generations(status);
CREATE INDEX IF NOT EXISTS idx_ai_generations_type ON ai_generations(generation_type);
CREATE INDEX IF NOT EXISTS idx_model_usage_name_date ON model_usage(model_name, date_bucket);
CREATE INDEX IF NOT EXISTS idx_system_metrics_name_time ON system_metrics(metric_name, recorded_at);

COMMIT;
'''
        
        with open('migrations/versions/001_initial_schema.sql', 'w', encoding='utf-8') as f:
            f.write(initial_migration)
        
        # Migration runner script
        migration_runner = '''#!/usr/bin/env python3
"""
Database Migration Runner for GameForge AI
"""

import os
import psycopg2
import glob
import logging
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'postgres'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'gameforge'),
            'user': os.getenv('DB_USER', 'gameforge'),
            'password': os.getenv('DB_PASSWORD', 'gameforge123')
        }
    
    def connect(self):
        """Connect to database"""
        return psycopg2.connect(**self.db_config)
    
    def create_migrations_table(self):
        """Create migrations tracking table"""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(50) PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations"""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version FROM schema_migrations ORDER BY version")
                return [row[0] for row in cur.fetchall()]
    
    def apply_migration(self, migration_file: str):
        """Apply a single migration"""
        version = os.path.basename(migration_file).replace('.sql', '')
        
        logger.info(f"Applying migration: {version}")
        
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        with self.connect() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)",
                        (version,)
                    )
                    conn.commit()
                    logger.info(f"✅ Migration {version} applied successfully")
                except Exception as e:
                    conn.rollback()
                    logger.error(f"❌ Migration {version} failed: {e}")
                    raise
    
    def run_migrations(self):
        """Run all pending migrations"""
        logger.info("Starting database migrations...")
        
        # Create migrations table
        self.create_migrations_table()
        
        # Get applied migrations
        applied = set(self.get_applied_migrations())
        
        # Find all migration files
        migration_files = sorted(glob.glob('migrations/versions/*.sql'))
        
        for migration_file in migration_files:
            version = os.path.basename(migration_file).replace('.sql', '')
            
            if version not in applied:
                self.apply_migration(migration_file)
            else:
                logger.info(f"⏭️  Migration {version} already applied")
        
        logger.info("✅ All migrations completed")

if __name__ == "__main__":
    runner = MigrationRunner()
    runner.run_migrations()
'''
        
        with open('scripts/run-migrations.py', 'w', encoding='utf-8') as f:
            f.write(migration_runner)
        
        logger.info("Database migration system created")
    
    def create_storage_persistence_config(self):
        """Create external storage persistence configuration"""
        
        # External storage Docker Compose
        storage_config = {
            'version': '3.8',
            'services': {
                'gameforge-app': {
                    'volumes': [
                        '/data/gameforge/models:/app/models:rw',
                        '/data/gameforge/uploads:/app/uploads:rw',
                        '/data/gameforge/cache:/app/cache:rw'
                    ],
                    'environment': [
                        'MODELS_DIR=/app/models',
                        'UPLOADS_DIR=/app/uploads',
                        'CACHE_DIR=/app/cache'
                    ]
                },
                'postgres': {
                    'volumes': [
                        '/data/gameforge/postgres:/var/lib/postgresql/data:rw'
                    ]
                },
                'redis': {
                    'volumes': [
                        '/data/gameforge/redis:/data:rw'
                    ]
                },
                'minio': {
                    'volumes': [
                        '/data/gameforge/minio:/data:rw'
                    ]
                },
                'elasticsearch': {
                    'volumes': [
                        '/data/gameforge/elasticsearch:/usr/share/elasticsearch/data:rw'
                    ]
                },
                'prometheus': {
                    'volumes': [
                        '/data/gameforge/prometheus:/prometheus:rw'
                    ]
                },
                'grafana': {
                    'volumes': [
                        '/data/gameforge/grafana:/var/lib/grafana:rw'
                    ]
                }
            },
            'volumes': {
                'gameforge_models': {
                    'driver': 'local',
                    'driver_opts': {
                        'type': 'none',
                        'o': 'bind',
                        'device': '/data/gameforge/models'
                    }
                },
                'gameforge_postgres': {
                    'driver': 'local',
                    'driver_opts': {
                        'type': 'none',
                        'o': 'bind',
                        'device': '/data/gameforge/postgres'
                    }
                }
            }
        }
        
        with open('docker-compose.external-storage.yml', 'w') as f:
            yaml.dump(storage_config, f, default_flow_style=False, indent=2)
        
        # Storage setup script
        storage_setup = '''#!/bin/bash
# GameForge AI External Storage Setup
set -e

echo "=== Setting up GameForge AI External Storage ==="

# Create data directories
sudo mkdir -p /data/gameforge/{models,uploads,cache,postgres,redis,minio,elasticsearch,prometheus,grafana}

# Set proper permissions
sudo chown -R 1001:1001 /data/gameforge/models
sudo chown -R 1001:1001 /data/gameforge/uploads
sudo chown -R 1001:1001 /data/gameforge/cache
sudo chown -R 999:999 /data/gameforge/postgres
sudo chown -R 999:999 /data/gameforge/redis
sudo chown -R 1000:1000 /data/gameforge/minio
sudo chown -R 1000:1000 /data/gameforge/elasticsearch
sudo chown -R 65534:65534 /data/gameforge/prometheus
sudo chown -R 472:472 /data/gameforge/grafana

# Set directory permissions
sudo chmod 755 /data/gameforge
sudo chmod -R 755 /data/gameforge/*

echo "✅ External storage setup complete"
echo "Storage locations:"
echo "  Models: /data/gameforge/models"
echo "  Database: /data/gameforge/postgres"
echo "  Object Storage: /data/gameforge/minio"
echo "  Monitoring: /data/gameforge/{prometheus,grafana}"
'''
        
        with open('scripts/setup-external-storage.sh', 'w', encoding='utf-8') as f:
            f.write(storage_setup)
        
        os.chmod('scripts/setup-external-storage.sh', 0o755)
        
        logger.info("External storage configuration created")
    
    def create_model_management_system(self):
        """Create complete model management system"""
        
        model_manager = '''#!/usr/bin/env python3
"""
GameForge AI Model Management System
Handles model lifecycle, versioning, and deployment
"""

import os
import json
import hashlib
import shutil
from datetime import datetime
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self, models_dir: str = "/app/models"):
        self.models_dir = models_dir
        self.manifest_file = os.path.join(models_dir, "models_manifest.json")
        self.ensure_models_dir()
    
    def ensure_models_dir(self):
        """Ensure models directory exists"""
        os.makedirs(self.models_dir, exist_ok=True)
    
    def get_model_manifest(self) -> Dict:
        """Get current model manifest"""
        if os.path.exists(self.manifest_file):
            with open(self.manifest_file, 'r') as f:
                return json.load(f)
        return {"models": {}, "last_updated": None}
    
    def update_manifest(self, manifest: Dict):
        """Update model manifest"""
        manifest["last_updated"] = datetime.now().isoformat()
        with open(self.manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
    
    def calculate_model_hash(self, model_path: str) -> str:
        """Calculate hash of model files for verification"""
        hash_md5 = hashlib.md5()
        
        if os.path.isfile(model_path):
            with open(model_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        elif os.path.isdir(model_path):
            for root, dirs, files in os.walk(model_path):
                for file in sorted(files):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'rb') as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def register_model(self, model_name: str, model_path: str, model_type: str, version: str = "1.0.0"):
        """Register a model in the manifest"""
        manifest = self.get_model_manifest()
        
        model_info = {
            "path": model_path,
            "type": model_type,
            "version": version,
            "size_bytes": self.get_directory_size(model_path),
            "hash": self.calculate_model_hash(model_path),
            "registered_at": datetime.now().isoformat(),
            "last_used": None,
            "usage_count": 0
        }
        
        manifest["models"][model_name] = model_info
        self.update_manifest(manifest)
        
        logger.info(f"✅ Model {model_name} registered successfully")
    
    def get_directory_size(self, path: str) -> int:
        """Get total size of directory"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size
    
    def list_models(self) -> Dict:
        """List all registered models"""
        manifest = self.get_model_manifest()
        return manifest.get("models", {})
    
    def verify_model_integrity(self, model_name: str) -> bool:
        """Verify model integrity using hash"""
        manifest = self.get_model_manifest()
        
        if model_name not in manifest["models"]:
            logger.error(f"Model {model_name} not found in manifest")
            return False
        
        model_info = manifest["models"][model_name]
        model_path = os.path.join(self.models_dir, model_info["path"])
        
        if not os.path.exists(model_path):
            logger.error(f"Model path {model_path} does not exist")
            return False
        
        current_hash = self.calculate_model_hash(model_path)
        expected_hash = model_info["hash"]
        
        if current_hash != expected_hash:
            logger.error(f"Model {model_name} integrity check failed")
            return False
        
        logger.info(f"✅ Model {model_name} integrity verified")
        return True
    
    def cleanup_unused_models(self, days_unused: int = 30):
        """Clean up models not used for specified days"""
        manifest = self.get_model_manifest()
        current_time = datetime.now()
        
        for model_name, model_info in list(manifest["models"].items()):
            last_used = model_info.get("last_used")
            
            if last_used:
                last_used_date = datetime.fromisoformat(last_used)
                days_since_used = (current_time - last_used_date).days
                
                if days_since_used > days_unused:
                    model_path = os.path.join(self.models_dir, model_info["path"])
                    if os.path.exists(model_path):
                        shutil.rmtree(model_path)
                        logger.info(f"🗑️  Removed unused model: {model_name}")
                    
                    del manifest["models"][model_name]
        
        self.update_manifest(manifest)
    
    def generate_model_report(self) -> str:
        """Generate model usage report"""
        manifest = self.get_model_manifest()
        models = manifest.get("models", {})
        
        report = []
        report.append("=" * 60)
        report.append("GAMEFORGE AI - MODEL MANAGEMENT REPORT")
        report.append("=" * 60)
        report.append("")
        
        if not models:
            report.append("No models registered")
            return "\\n".join(report)
        
        total_size = sum(model["size_bytes"] for model in models.values())
        
        report.append(f"Total Models: {len(models)}")
        report.append(f"Total Size: {total_size / (1024**3):.2f} GB")
        report.append("")
        
        report.append("MODEL DETAILS:")
        report.append("-" * 40)
        
        for name, info in models.items():
            size_gb = info["size_bytes"] / (1024**3)
            last_used = info.get("last_used", "Never")
            report.append(f"• {name}")
            report.append(f"  Type: {info['type']}")
            report.append(f"  Version: {info['version']}")
            report.append(f"  Size: {size_gb:.2f} GB")
            report.append(f"  Usage Count: {info['usage_count']}")
            report.append(f"  Last Used: {last_used}")
            report.append("")
        
        return "\\n".join(report)

def main():
    """Main model management execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GameForge AI Model Manager')
    parser.add_argument('--action', choices=['list', 'verify', 'cleanup', 'report'], 
                      default='report', help='Action to perform')
    parser.add_argument('--model', help='Model name for verify action')
    parser.add_argument('--cleanup-days', type=int, default=30, 
                      help='Days unused for cleanup action')
    
    args = parser.parse_args()
    
    manager = ModelManager()
    
    if args.action == 'list':
        models = manager.list_models()
        print(json.dumps(models, indent=2))
    
    elif args.action == 'verify':
        if not args.model:
            print("--model required for verify action")
            return 1
        
        if manager.verify_model_integrity(args.model):
            print(f"✅ Model {args.model} verified")
            return 0
        else:
            print(f"❌ Model {args.model} verification failed")
            return 1
    
    elif args.action == 'cleanup':
        manager.cleanup_unused_models(args.cleanup_days)
        print(f"✅ Cleanup completed for models unused > {args.cleanup_days} days")
    
    elif args.action == 'report':
        report = manager.generate_model_report()
        print(report)
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
'''
        
        with open('scripts/model-manager.py', 'w', encoding='utf-8') as f:
            f.write(model_manager)
        
        logger.info("Model management system created")

def main():
    """Create all data and model management configurations"""
    logger.info("Creating comprehensive data and model management system...")
    
    externalizer = ModelExternalizer()
    
    externalizer.create_model_download_script()
    externalizer.create_optimized_dockerfile()
    externalizer.create_database_migrations()
    externalizer.create_storage_persistence_config()
    externalizer.create_model_management_system()
    
    logger.info("\nALL DATA & MODEL MANAGEMENT CONFIGURATIONS CREATED")
    logger.info("Key components:")
    logger.info("1. Model download script: scripts/download-models.sh")
    logger.info("2. Optimized Dockerfile: Dockerfile.optimized")
    logger.info("3. Database migrations: migrations/versions/")
    logger.info("4. External storage config: docker-compose.external-storage.yml")
    logger.info("5. Model manager: scripts/model-manager.py")

if __name__ == "__main__":
    main()