#!/usr/bin/env python3
"""
GameForge Model Registry Manager

Handles model registration, promotion, deployment, and lifecycle management
across dev → staging → production environments with approval workflows.
"""

import os
import json
import yaml
import sqlite3
import hashlib
import requests
import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import boto3
import mlflow
from mlflow.tracking import MlflowClient


class ModelStage(Enum):
    """Model lifecycle stages"""
    EXPERIMENTAL = "experimental"
    DEVELOPMENT = "development" 
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class Environment(Enum):
    """Deployment environments"""
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ModelMetadata:
    """Model metadata and registration information"""
    model_id: str
    name: str
    version: str
    framework: str
    stage: ModelStage
    environment: Optional[Environment]
    description: str
    author: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    model_uri: str
    artifacts_uri: str
    performance_metrics: Dict[str, float]
    quality_gates_passed: bool
    approval_status: Dict[str, bool]
    tags: List[str]
    metadata: Dict[str, Any]


@dataclass
class PromotionRequest:
    """Model promotion request"""
    model_id: str
    from_stage: ModelStage
    to_stage: ModelStage
    requestor: str
    justification: str
    prerequisites_met: bool
    approvals_required: List[str]
    approvals_received: List[str]
    created_at: datetime.datetime
    status: str  # pending, approved, rejected, completed


class ModelRegistry:
    """
    GameForge Model Registry for managing ML model lifecycle
    """
    
    def __init__(self, config_path: str = None):
        """Initialize the model registry"""
        
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent / "registry-config.yaml"
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize storage backends
        self._init_storage()
        self._init_database()
        self._init_mlflow()
        
        print(f"✅ Model Registry initialized with config: {config_path}")
    
    
    def _init_storage(self):
        """Initialize S3 storage backend"""
        self.s3_client = boto3.client('s3')
        self.storage_bucket = self.config['registry']['storage_location'].replace('s3://', '').split('/')[0]
        self.storage_prefix = '/'.join(self.config['registry']['storage_location'].replace('s3://', '').split('/')[1:])
        
    
    def _init_database(self):
        """Initialize metadata database"""
        db_path = Path(__file__).parent / "registry.db"
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._create_tables()
    
    
    def _init_mlflow(self):
        """Initialize MLflow integration"""
        # Set MLflow tracking URI if configured
        if 'MLFLOW_TRACKING_URI' in os.environ:
            mlflow.set_tracking_uri(os.environ['MLFLOW_TRACKING_URI'])
        else:
            # Use local tracking
            tracking_dir = Path(__file__).parent / "mlruns"
            tracking_dir.mkdir(exist_ok=True)
            mlflow.set_tracking_uri(f"file://{tracking_dir}")
        
        self.mlflow_client = MlflowClient()
    
    
    def _create_tables(self):
        """Create database tables for registry metadata"""
        
        # Models table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS models (
                model_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                framework TEXT NOT NULL,
                stage TEXT NOT NULL,
                environment TEXT,
                description TEXT,
                author TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                model_uri TEXT NOT NULL,
                artifacts_uri TEXT,
                performance_metrics TEXT,
                quality_gates_passed BOOLEAN,
                approval_status TEXT,
                tags TEXT,
                metadata TEXT
            )
        ''')
        
        # Promotion requests table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS promotion_requests (
                request_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                from_stage TEXT NOT NULL,
                to_stage TEXT NOT NULL,
                requestor TEXT NOT NULL,
                justification TEXT,
                prerequisites_met BOOLEAN,
                approvals_required TEXT,
                approvals_received TEXT,
                created_at TIMESTAMP NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY (model_id) REFERENCES models (model_id)
            )
        ''')
        
        # Deployment history table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS deployment_history (
                deployment_id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL,
                environment TEXT NOT NULL,
                version TEXT NOT NULL,
                deployed_at TIMESTAMP NOT NULL,
                deployed_by TEXT NOT NULL,
                status TEXT NOT NULL,
                health_check_passed BOOLEAN,
                rollback_version TEXT,
                FOREIGN KEY (model_id) REFERENCES models (model_id)
            )
        ''')
        
        self.conn.commit()
    
    
    def register_model(self, 
                      name: str,
                      version: str,
                      framework: str,
                      model_uri: str,
                      description: str,
                      author: str,
                      stage: ModelStage = ModelStage.EXPERIMENTAL,
                      performance_metrics: Dict[str, float] = None,
                      tags: List[str] = None,
                      metadata: Dict[str, Any] = None) -> str:
        """
        Register a new model in the registry
        
        Args:
            name: Model name
            version: Model version
            framework: ML framework (pytorch, tensorflow, etc.)
            model_uri: URI to model artifacts
            description: Model description
            author: Model author
            stage: Initial lifecycle stage
            performance_metrics: Performance metrics dict
            tags: Model tags
            metadata: Additional metadata
            
        Returns:
            model_id: Unique model identifier
        """
        
        # Generate unique model ID
        model_id = self._generate_model_id(name, version, author)
        
        # Create model metadata
        now = datetime.datetime.utcnow()
        model_metadata = ModelMetadata(
            model_id=model_id,
            name=name,
            version=version,
            framework=framework,
            stage=stage,
            environment=None,
            description=description,
            author=author,
            created_at=now,
            updated_at=now,
            model_uri=model_uri,
            artifacts_uri=None,
            performance_metrics=performance_metrics or {},
            quality_gates_passed=False,
            approval_status={},
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Store in database
        self._store_model_metadata(model_metadata)
        
        # Register with MLflow
        self._register_with_mlflow(model_metadata)
        
        print(f"✅ Model registered: {model_id}")
        print(f"   Name: {name}")
        print(f"   Version: {version}")
        print(f"   Stage: {stage.value}")
        print(f"   Author: {author}")
        
        return model_id
    
    
    def _generate_model_id(self, name: str, version: str, author: str) -> str:
        """Generate unique model ID"""
        content = f"{name}-{version}-{author}-{datetime.datetime.utcnow().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    
    def _store_model_metadata(self, metadata: ModelMetadata):
        """Store model metadata in database"""
        
        self.conn.execute('''
            INSERT OR REPLACE INTO models 
            (model_id, name, version, framework, stage, environment, description, 
             author, created_at, updated_at, model_uri, artifacts_uri, 
             performance_metrics, quality_gates_passed, approval_status, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metadata.model_id,
            metadata.name, 
            metadata.version,
            metadata.framework,
            metadata.stage.value,
            metadata.environment.value if metadata.environment else None,
            metadata.description,
            metadata.author,
            metadata.created_at,
            metadata.updated_at,
            metadata.model_uri,
            metadata.artifacts_uri,
            json.dumps(metadata.performance_metrics),
            metadata.quality_gates_passed,
            json.dumps(metadata.approval_status),
            json.dumps(metadata.tags),
            json.dumps(metadata.metadata)
        ))
        
        self.conn.commit()
    
    
    def _register_with_mlflow(self, metadata: ModelMetadata):
        """Register model with MLflow"""
        try:
            # Create or get existing registered model
            try:
                registered_model = self.mlflow_client.create_registered_model(
                    name=metadata.name,
                    description=metadata.description
                )
            except Exception:
                # Model already exists
                registered_model = self.mlflow_client.get_registered_model(metadata.name)
            
            # Create model version
            model_version = self.mlflow_client.create_model_version(
                name=metadata.name,
                source=metadata.model_uri,
                description=f"Version {metadata.version} - {metadata.description}"
            )
            
            # Set tags
            for tag in metadata.tags:
                self.mlflow_client.set_model_version_tag(
                    name=metadata.name,
                    version=model_version.version,
                    key="tag",
                    value=tag
                )
            
            # Set custom metadata
            self.mlflow_client.set_model_version_tag(
                name=metadata.name,
                version=model_version.version,
                key="gameforge_model_id",
                value=metadata.model_id
            )
            
        except Exception as e:
            print(f"⚠️  Warning: MLflow registration failed: {e}")
    
    
    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata by ID"""
        
        cursor = self.conn.execute(
            'SELECT * FROM models WHERE model_id = ?',
            (model_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return self._row_to_model_metadata(row)
    
    
    def list_models(self, 
                   stage: Optional[ModelStage] = None,
                   environment: Optional[Environment] = None,
                   author: Optional[str] = None,
                   tags: Optional[List[str]] = None) -> List[ModelMetadata]:
        """List models with optional filtering"""
        
        query = 'SELECT * FROM models WHERE 1=1'
        params = []
        
        if stage:
            query += ' AND stage = ?'
            params.append(stage.value)
        
        if environment:
            query += ' AND environment = ?'
            params.append(environment.value)
        
        if author:
            query += ' AND author = ?'
            params.append(author)
        
        query += ' ORDER BY created_at DESC'
        
        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()
        
        models = [self._row_to_model_metadata(row) for row in rows]
        
        # Filter by tags if specified
        if tags:
            filtered_models = []
            for model in models:
                if any(tag in model.tags for tag in tags):
                    filtered_models.append(model)
            models = filtered_models
        
        return models
    
    
    def _row_to_model_metadata(self, row) -> ModelMetadata:
        """Convert database row to ModelMetadata"""
        
        return ModelMetadata(
            model_id=row[0],
            name=row[1],
            version=row[2],
            framework=row[3],
            stage=ModelStage(row[4]),
            environment=Environment(row[5]) if row[5] else None,
            description=row[6],
            author=row[7],
            created_at=datetime.datetime.fromisoformat(row[8]),
            updated_at=datetime.datetime.fromisoformat(row[9]),
            model_uri=row[10],
            artifacts_uri=row[11],
            performance_metrics=json.loads(row[12]) if row[12] else {},
            quality_gates_passed=bool(row[13]),
            approval_status=json.loads(row[14]) if row[14] else {},
            tags=json.loads(row[15]) if row[15] else [],
            metadata=json.loads(row[16]) if row[16] else {}
        )
    
    
    def request_promotion(self,
                         model_id: str,
                         to_stage: ModelStage,
                         requestor: str,
                         justification: str) -> str:
        """
        Request model promotion to next stage
        
        Args:
            model_id: Model to promote
            to_stage: Target stage
            requestor: Person requesting promotion
            justification: Reason for promotion
            
        Returns:
            request_id: Promotion request ID
        """
        
        # Get current model
        model = self.get_model(model_id)
        if not model:
            raise ValueError(f"Model not found: {model_id}")
        
        # Validate promotion path
        if not self._is_valid_promotion(model.stage, to_stage):
            raise ValueError(f"Invalid promotion: {model.stage.value} → {to_stage.value}")
        
        # Check prerequisites
        prerequisites_met = self._check_promotion_prerequisites(model, to_stage)
        
        # Get required approvals
        approvals_required = self._get_required_approvals(to_stage)
        
        # Create promotion request
        request_id = f"promo-{model_id}-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        promotion_request = PromotionRequest(
            model_id=model_id,
            from_stage=model.stage,
            to_stage=to_stage,
            requestor=requestor,
            justification=justification,
            prerequisites_met=prerequisites_met,
            approvals_required=approvals_required,
            approvals_received=[],
            created_at=datetime.datetime.utcnow(),
            status="pending"
        )
        
        # Store promotion request
        self._store_promotion_request(request_id, promotion_request)
        
        # Send notifications
        self._send_promotion_notifications(promotion_request)
        
        print(f"✅ Promotion request created: {request_id}")
        print(f"   Model: {model.name} ({model_id})")
        print(f"   Promotion: {model.stage.value} → {to_stage.value}")
        print(f"   Prerequisites met: {prerequisites_met}")
        print(f"   Approvals required: {len(approvals_required)}")
        
        return request_id
    
    
    def _is_valid_promotion(self, from_stage: ModelStage, to_stage: ModelStage) -> bool:
        """Check if promotion path is valid"""
        
        valid_transitions = {
            ModelStage.EXPERIMENTAL: [ModelStage.DEVELOPMENT, ModelStage.ARCHIVED],
            ModelStage.DEVELOPMENT: [ModelStage.STAGING, ModelStage.ARCHIVED, ModelStage.EXPERIMENTAL],
            ModelStage.STAGING: [ModelStage.PRODUCTION, ModelStage.DEVELOPMENT, ModelStage.ARCHIVED],
            ModelStage.PRODUCTION: [ModelStage.DEPRECATED, ModelStage.ARCHIVED],
            ModelStage.DEPRECATED: [ModelStage.ARCHIVED],
            ModelStage.ARCHIVED: []
        }
        
        return to_stage in valid_transitions.get(from_stage, [])
    
    
    def _check_promotion_prerequisites(self, model: ModelMetadata, to_stage: ModelStage) -> bool:
        """Check if promotion prerequisites are met"""
        
        # Get stage configuration
        stage_config = self.config['environments'].get(to_stage.value.replace('production', 'production'))
        
        if not stage_config:
            return True
        
        # Check performance gates
        performance_gates = stage_config.get('performance_gates', [])
        for gate in performance_gates:
            metric = gate['metric']
            operator = gate['operator']
            threshold = gate['threshold']
            required = gate.get('required', False)
            
            if metric not in model.performance_metrics:
                if required:
                    print(f"❌ Missing required metric: {metric}")
                    return False
                continue
            
            value = model.performance_metrics[metric]
            
            if operator == '<' and value >= threshold:
                if required:
                    print(f"❌ Performance gate failed: {metric} = {value} (required < {threshold})")
                    return False
            elif operator == '>' and value <= threshold:
                if required:
                    print(f"❌ Performance gate failed: {metric} = {value} (required > {threshold})")
                    return False
        
        return True
    
    
    def _get_required_approvals(self, to_stage: ModelStage) -> List[str]:
        """Get list of required approvals for promotion"""
        
        # Map stages to environment configs
        stage_env_map = {
            ModelStage.STAGING: 'staging',
            ModelStage.PRODUCTION: 'production'
        }
        
        env_name = stage_env_map.get(to_stage)
        if not env_name:
            return []
        
        env_config = self.config['environments'].get(env_name, {})
        return env_config.get('approvers', [])
    
    
    def _store_promotion_request(self, request_id: str, request: PromotionRequest):
        """Store promotion request in database"""
        
        self.conn.execute('''
            INSERT INTO promotion_requests
            (request_id, model_id, from_stage, to_stage, requestor, justification,
             prerequisites_met, approvals_required, approvals_received, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request_id,
            request.model_id,
            request.from_stage.value,
            request.to_stage.value,
            request.requestor,
            request.justification,
            request.prerequisites_met,
            json.dumps(request.approvals_required),
            json.dumps(request.approvals_received),
            request.created_at,
            request.status
        ))
        
        self.conn.commit()
    
    
    def _send_promotion_notifications(self, request: PromotionRequest):
        """Send notifications for promotion request"""
        
        # This is a placeholder - implement actual notification logic
        print(f"📧 Sending promotion notifications:")
        print(f"   To: {', '.join(request.approvals_required)}")
        print(f"   Subject: Model promotion request: {request.model_id}")
    
    
    def approve_promotion(self, request_id: str, approver: str, approved: bool = True) -> bool:
        """
        Approve or reject a promotion request
        
        Args:
            request_id: Promotion request ID
            approver: Person providing approval
            approved: Whether request is approved
            
        Returns:
            bool: Whether promotion can proceed
        """
        
        # Get promotion request
        cursor = self.conn.execute(
            'SELECT * FROM promotion_requests WHERE request_id = ?',
            (request_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Promotion request not found: {request_id}")
        
        # Parse request data
        approvals_required = json.loads(row[8])
        approvals_received = json.loads(row[9])
        
        # Check if approver is authorized
        if approver not in approvals_required:
            raise ValueError(f"Unauthorized approver: {approver}")
        
        # Record approval/rejection
        if approved and approver not in approvals_received:
            approvals_received.append(approver)
        elif not approved:
            # Rejection - update status
            self.conn.execute(
                'UPDATE promotion_requests SET status = ? WHERE request_id = ?',
                ('rejected', request_id)
            )
            self.conn.commit()
            print(f"❌ Promotion request rejected by {approver}")
            return False
        
        # Update approvals
        self.conn.execute(
            'UPDATE promotion_requests SET approvals_received = ? WHERE request_id = ?',
            (json.dumps(approvals_received), request_id)
        )
        
        # Check if all approvals received
        all_approved = set(approvals_received) >= set(approvals_required)
        
        if all_approved:
            # Execute promotion
            self._execute_promotion(request_id)
            
            self.conn.execute(
                'UPDATE promotion_requests SET status = ? WHERE request_id = ?',
                ('completed', request_id)
            )
        
        self.conn.commit()
        
        print(f"✅ Approval recorded from {approver}")
        print(f"   Approvals: {len(approvals_received)}/{len(approvals_required)}")
        
        if all_approved:
            print(f"🚀 All approvals received - executing promotion")
        
        return all_approved
    
    
    def _execute_promotion(self, request_id: str):
        """Execute the promotion after all approvals"""
        
        # Get promotion request
        cursor = self.conn.execute(
            'SELECT * FROM promotion_requests WHERE request_id = ?',
            (request_id,)
        )
        
        row = cursor.fetchone()
        model_id = row[1]
        to_stage = ModelStage(row[3])
        
        # Update model stage
        self.conn.execute(
            'UPDATE models SET stage = ?, updated_at = ? WHERE model_id = ?',
            (to_stage.value, datetime.datetime.utcnow(), model_id)
        )
        
        # Deploy to environment if applicable
        if to_stage in [ModelStage.STAGING, ModelStage.PRODUCTION]:
            environment = Environment.STAGING if to_stage == ModelStage.STAGING else Environment.PRODUCTION
            self._deploy_to_environment(model_id, environment)
        
        self.conn.commit()
        
        print(f"✅ Model promoted to {to_stage.value}")
    
    
    def _deploy_to_environment(self, model_id: str, environment: Environment):
        """Deploy model to environment"""
        
        # This is a placeholder for actual deployment logic
        # In practice, this would:
        # 1. Update load balancer configuration
        # 2. Deploy to Kubernetes/container orchestration
        # 3. Run health checks
        # 4. Update monitoring
        
        deployment_id = f"deploy-{model_id}-{environment.value}-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # Record deployment
        self.conn.execute('''
            INSERT INTO deployment_history
            (deployment_id, model_id, environment, version, deployed_at, 
             deployed_by, status, health_check_passed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            deployment_id,
            model_id,
            environment.value,
            "latest",  # Could be actual version
            datetime.datetime.utcnow(),
            "system",
            "success",
            True
        ))
        
        # Update model environment
        self.conn.execute(
            'UPDATE models SET environment = ? WHERE model_id = ?',
            (environment.value, model_id)
        )
        
        print(f"🚀 Deployed to {environment.value}: {deployment_id}")
    
    
    def get_deployment_history(self, model_id: str) -> List[Dict]:
        """Get deployment history for a model"""
        
        cursor = self.conn.execute(
            'SELECT * FROM deployment_history WHERE model_id = ? ORDER BY deployed_at DESC',
            (model_id,)
        )
        
        rows = cursor.fetchall()
        
        history = []
        for row in rows:
            history.append({
                'deployment_id': row[0],
                'model_id': row[1],
                'environment': row[2],
                'version': row[3],
                'deployed_at': row[4],
                'deployed_by': row[5],
                'status': row[6],
                'health_check_passed': bool(row[7])
            })
        
        return history
    
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        
        stats = {}
        
        # Model counts by stage
        cursor = self.conn.execute(
            'SELECT stage, COUNT(*) FROM models GROUP BY stage'
        )
        stats['models_by_stage'] = dict(cursor.fetchall())
        
        # Model counts by environment
        cursor = self.conn.execute(
            'SELECT environment, COUNT(*) FROM models WHERE environment IS NOT NULL GROUP BY environment'
        )
        stats['models_by_environment'] = dict(cursor.fetchall())
        
        # Recent deployments
        cursor = self.conn.execute(
            'SELECT COUNT(*) FROM deployment_history WHERE deployed_at > datetime("now", "-7 days")'
        )
        stats['deployments_last_7_days'] = cursor.fetchone()[0]
        
        # Pending promotions
        cursor = self.conn.execute(
            'SELECT COUNT(*) FROM promotion_requests WHERE status = "pending"'
        )
        stats['pending_promotions'] = cursor.fetchone()[0]
        
        return stats


def main():
    """CLI interface for model registry"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GameForge Model Registry')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Register model
    register_parser = subparsers.add_parser('register', help='Register a new model')
    register_parser.add_argument('--name', required=True, help='Model name')
    register_parser.add_argument('--version', required=True, help='Model version')
    register_parser.add_argument('--framework', required=True, help='ML framework')
    register_parser.add_argument('--model-uri', required=True, help='Model URI')
    register_parser.add_argument('--description', required=True, help='Model description')
    register_parser.add_argument('--author', required=True, help='Model author')
    
    # List models
    list_parser = subparsers.add_parser('list', help='List models')
    list_parser.add_argument('--stage', help='Filter by stage')
    list_parser.add_argument('--environment', help='Filter by environment')
    list_parser.add_argument('--author', help='Filter by author')
    
    # Promote model
    promote_parser = subparsers.add_parser('promote', help='Request model promotion')
    promote_parser.add_argument('--model-id', required=True, help='Model ID')
    promote_parser.add_argument('--to-stage', required=True, help='Target stage')
    promote_parser.add_argument('--requestor', required=True, help='Requestor email')
    promote_parser.add_argument('--justification', required=True, help='Promotion justification')
    
    # Approve promotion
    approve_parser = subparsers.add_parser('approve', help='Approve promotion request')
    approve_parser.add_argument('--request-id', required=True, help='Promotion request ID')
    approve_parser.add_argument('--approver', required=True, help='Approver email')
    approve_parser.add_argument('--reject', action='store_true', help='Reject instead of approve')
    
    # Stats
    stats_parser = subparsers.add_parser('stats', help='Show registry statistics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize registry
    registry = ModelRegistry()
    
    try:
        if args.command == 'register':
            model_id = registry.register_model(
                name=args.name,
                version=args.version,
                framework=args.framework,
                model_uri=args.model_uri,
                description=args.description,
                author=args.author
            )
            print(f"Model registered with ID: {model_id}")
        
        elif args.command == 'list':
            stage = ModelStage(args.stage) if args.stage else None
            environment = Environment(args.environment) if args.environment else None
            
            models = registry.list_models(
                stage=stage,
                environment=environment,
                author=args.author
            )
            
            print(f"\n📋 Found {len(models)} models:")
            for model in models:
                print(f"   {model.model_id}: {model.name} v{model.version}")
                print(f"      Stage: {model.stage.value}")
                print(f"      Environment: {model.environment.value if model.environment else 'None'}")
                print(f"      Author: {model.author}")
                print()
        
        elif args.command == 'promote':
            request_id = registry.request_promotion(
                model_id=args.model_id,
                to_stage=ModelStage(args.to_stage),
                requestor=args.requestor,
                justification=args.justification
            )
            print(f"Promotion request created: {request_id}")
        
        elif args.command == 'approve':
            approved = registry.approve_promotion(
                request_id=args.request_id,
                approver=args.approver,
                approved=not args.reject
            )
            
            if approved:
                print("✅ Promotion approved and executed")
            else:
                print("❌ Promotion rejected" if args.reject else "⏳ Waiting for more approvals")
        
        elif args.command == 'stats':
            stats = registry.get_registry_stats()
            
            print("\n📊 Registry Statistics:")
            print(f"   Models by stage: {stats['models_by_stage']}")
            print(f"   Models by environment: {stats['models_by_environment']}")
            print(f"   Deployments (last 7 days): {stats['deployments_last_7_days']}")
            print(f"   Pending promotions: {stats['pending_promotions']}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())