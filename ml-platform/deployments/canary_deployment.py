"""
GameForge Canary Deployment System
==================================

Implements automated canary deployments for ML models with:
- Traffic splitting between model versions
- A/B testing with statistical validation
- Automated rollback based on performance metrics
- Integration with MLflow model registry
- Prometheus metrics collection
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import asyncpg
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import numpy as np
from scipy import stats
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
deployment_counter = Counter('gameforge_canary_deployments_total', 'Total canary deployments', ['model', 'version', 'status'])
request_latency = Histogram('gameforge_canary_request_duration_seconds', 'Request latency', ['model', 'version'])
error_rate = Counter('gameforge_canary_errors_total', 'Total errors', ['model', 'version', 'error_type'])
traffic_gauge = Gauge('gameforge_canary_traffic_percentage', 'Traffic percentage', ['model', 'version'])
model_accuracy = Gauge('gameforge_canary_model_accuracy', 'Model accuracy', ['model', 'version'])

class DeploymentStatus(Enum):
    """Deployment status enumeration"""
    PREPARING = "preparing"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    MONITORING = "monitoring"
    PROMOTING = "promoting"
    ROLLING_BACK = "rolling_back"
    COMPLETED = "completed"
    FAILED = "failed"

class MetricType(Enum):
    """Metric type enumeration"""
    ACCURACY = "accuracy"
    LATENCY = "latency"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"

@dataclass
class CanaryConfig:
    """Canary deployment configuration"""
    model_name: str
    current_version: str
    canary_version: str
    initial_traffic_percentage: int = 5
    max_traffic_percentage: int = 50
    traffic_increment: int = 5
    monitoring_duration_minutes: int = 30
    success_threshold: float = 0.95
    error_threshold: float = 0.05
    latency_threshold_ms: float = 500.0
    statistical_significance: float = 0.05
    min_requests_for_promotion: int = 1000
    auto_promote: bool = False
    auto_rollback: bool = True

@dataclass
class MetricData:
    """Metric data structure"""
    timestamp: datetime
    value: float
    metric_type: MetricType
    model_version: str

@dataclass
class ComparisonResult:
    """Statistical comparison result"""
    metric_type: MetricType
    current_mean: float
    canary_mean: float
    p_value: float
    is_significant: bool
    canary_is_better: bool
    confidence_interval: Tuple[float, float]

class TrafficSplitter:
    """Handles traffic splitting between model versions"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
    async def set_traffic_split(self, model_name: str, version_weights: Dict[str, int]) -> None:
        """Set traffic split weights for model versions"""
        key = f"traffic_split:{model_name}"
        await self.redis.hset(key, mapping=version_weights)
        await self.redis.expire(key, 3600)  # 1 hour expiry
        
        # Update Prometheus metrics
        for version, weight in version_weights.items():
            traffic_gauge.labels(model=model_name, version=version).set(weight)
            
        logger.info(f"Updated traffic split for {model_name}: {version_weights}")
        
    async def get_traffic_split(self, model_name: str) -> Dict[str, int]:
        """Get current traffic split weights"""
        key = f"traffic_split:{model_name}"
        weights = await self.redis.hgetall(key)
        return {k.decode(): int(v) for k, v in weights.items()}
        
    async def route_request(self, model_name: str) -> str:
        """Route request based on traffic split weights"""
        weights = await self.get_traffic_split(model_name)
        if not weights:
            return "current"  # Default to current version
            
        total_weight = sum(weights.values())
        if total_weight == 0:
            return "current"
            
        # Weighted random selection
        rand_val = np.random.random() * total_weight
        cumulative_weight = 0
        
        for version, weight in weights.items():
            cumulative_weight += weight
            if rand_val <= cumulative_weight:
                return version
                
        return "current"  # Fallback

class MetricsCollector:
    """Collects and analyzes model performance metrics"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis):
        self.db_pool = db_pool
        self.redis = redis_client
        
    async def record_request(self, model_name: str, version: str, 
                           latency_ms: float, error: bool = False) -> None:
        """Record a model request with metrics"""
        timestamp = datetime.utcnow()
        
        # Record in database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO model_metrics (model_name, model_version, metric_name, 
                                         metric_value, metric_type, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, model_name, version, "latency", latency_ms, "latency", timestamp)
            
            if error:
                await conn.execute("""
                    INSERT INTO model_metrics (model_name, model_version, metric_name, 
                                             metric_value, metric_type, timestamp)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, model_name, version, "error", 1.0, "error_rate", timestamp)
                
        # Update Prometheus metrics
        request_latency.labels(model=model_name, version=version).observe(latency_ms / 1000)
        if error:
            error_rate.labels(model=model_name, version=version, error_type="request").inc()
            
    async def record_prediction_accuracy(self, model_name: str, version: str, 
                                       accuracy: float) -> None:
        """Record prediction accuracy"""
        timestamp = datetime.utcnow()
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO model_metrics (model_name, model_version, metric_name, 
                                         metric_value, metric_type, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, model_name, version, "accuracy", accuracy, "accuracy", timestamp)
            
        # Update Prometheus metrics
        model_accuracy.labels(model=model_name, version=version).set(accuracy)
        
    async def get_metrics(self, model_name: str, version: str, 
                         metric_type: MetricType, 
                         start_time: datetime, 
                         end_time: datetime) -> List[MetricData]:
        """Get metrics for a specific time range"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT timestamp, metric_value, metric_type, model_version
                FROM model_metrics
                WHERE model_name = $1 AND model_version = $2 
                  AND metric_type = $3 AND timestamp BETWEEN $4 AND $5
                ORDER BY timestamp
            """, model_name, version, metric_type.value, start_time, end_time)
            
        return [
            MetricData(
                timestamp=row['timestamp'],
                value=float(row['metric_value']),
                metric_type=MetricType(row['metric_type']),
                model_version=row['model_version']
            )
            for row in rows
        ]

class StatisticalAnalyzer:
    """Performs statistical analysis for canary deployments"""
    
    @staticmethod
    def compare_metrics(current_data: List[float], canary_data: List[float], 
                       metric_type: MetricType, significance_level: float = 0.05) -> ComparisonResult:
        """Compare metrics between current and canary versions"""
        if len(current_data) < 10 or len(canary_data) < 10:
            # Not enough data for statistical comparison
            return ComparisonResult(
                metric_type=metric_type,
                current_mean=np.mean(current_data) if current_data else 0.0,
                canary_mean=np.mean(canary_data) if canary_data else 0.0,
                p_value=1.0,
                is_significant=False,
                canary_is_better=False,
                confidence_interval=(0.0, 0.0)
            )
            
        current_mean = np.mean(current_data)
        canary_mean = np.mean(canary_data)
        
        # Perform t-test
        t_stat, p_value = stats.ttest_ind(canary_data, current_data)
        is_significant = p_value < significance_level
        
        # Calculate confidence interval for the difference
        pooled_std = np.sqrt(((len(current_data) - 1) * np.var(current_data, ddof=1) + 
                             (len(canary_data) - 1) * np.var(canary_data, ddof=1)) / 
                            (len(current_data) + len(canary_data) - 2))
        
        standard_error = pooled_std * np.sqrt(1/len(current_data) + 1/len(canary_data))
        margin_of_error = stats.t.ppf(1 - significance_level/2, 
                                    len(current_data) + len(canary_data) - 2) * standard_error
        
        diff_mean = canary_mean - current_mean
        confidence_interval = (diff_mean - margin_of_error, diff_mean + margin_of_error)
        
        # Determine if canary is better based on metric type
        if metric_type in [MetricType.ACCURACY, MetricType.THROUGHPUT]:
            canary_is_better = canary_mean > current_mean
        else:  # For latency and error rate, lower is better
            canary_is_better = canary_mean < current_mean
            
        return ComparisonResult(
            metric_type=metric_type,
            current_mean=current_mean,
            canary_mean=canary_mean,
            p_value=p_value,
            is_significant=is_significant,
            canary_is_better=canary_is_better and is_significant,
            confidence_interval=confidence_interval
        )

class CanaryDeploymentManager:
    """Main canary deployment management system"""
    
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis, 
                 mlflow_url: str = "http://mlflow-server:5000"):
        self.db_pool = db_pool
        self.redis = redis_client
        self.mlflow_url = mlflow_url
        self.traffic_splitter = TrafficSplitter(redis_client)
        self.metrics_collector = MetricsCollector(db_pool, redis_client)
        self.analyzer = StatisticalAnalyzer()
        self.active_deployments: Dict[str, CanaryConfig] = {}
        
    async def start_canary_deployment(self, config: CanaryConfig) -> bool:
        """Start a new canary deployment"""
        try:
            logger.info(f"Starting canary deployment for {config.model_name}: "
                       f"{config.current_version} -> {config.canary_version}")
            
            # Validate model versions exist in MLflow
            if not await self._validate_model_versions(config):
                raise ValueError("Invalid model versions")
                
            # Record deployment in database
            await self._record_deployment(config, DeploymentStatus.PREPARING)
            
            # Initialize traffic split
            await self.traffic_splitter.set_traffic_split(
                config.model_name,
                {
                    config.current_version: 100 - config.initial_traffic_percentage,
                    config.canary_version: config.initial_traffic_percentage
                }
            )
            
            # Store active deployment
            self.active_deployments[config.model_name] = config
            
            # Update Prometheus metrics
            deployment_counter.labels(
                model=config.model_name,
                version=config.canary_version,
                status="started"
            ).inc()
            
            logger.info(f"Canary deployment started for {config.model_name} "
                       f"with {config.initial_traffic_percentage}% traffic")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start canary deployment: {e}")
            await self._record_deployment(config, DeploymentStatus.FAILED)
            return False
            
    async def monitor_deployment(self, model_name: str) -> bool:
        """Monitor active canary deployment"""
        if model_name not in self.active_deployments:
            return False
            
        config = self.active_deployments[model_name]
        
        try:
            # Get current metrics
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=config.monitoring_duration_minutes)
            
            # Collect metrics for comparison
            current_metrics = {}
            canary_metrics = {}
            
            for metric_type in [MetricType.ACCURACY, MetricType.LATENCY, MetricType.ERROR_RATE]:
                current_data = await self.metrics_collector.get_metrics(
                    model_name, config.current_version, metric_type, start_time, end_time
                )
                canary_data = await self.metrics_collector.get_metrics(
                    model_name, config.canary_version, metric_type, start_time, end_time
                )
                
                current_metrics[metric_type] = [d.value for d in current_data]
                canary_metrics[metric_type] = [d.value for d in canary_data]
                
            # Perform statistical analysis
            comparison_results = {}
            for metric_type in current_metrics:
                comparison_results[metric_type] = self.analyzer.compare_metrics(
                    current_metrics[metric_type],
                    canary_metrics[metric_type],
                    metric_type,
                    config.statistical_significance
                )
                
            # Make decision based on results
            decision = await self._make_deployment_decision(config, comparison_results)
            
            if decision == "promote":
                await self._promote_canary(config)
            elif decision == "rollback":
                await self._rollback_canary(config)
            elif decision == "continue":
                await self._increment_traffic(config)
                
            return True
            
        except Exception as e:
            logger.error(f"Error monitoring deployment {model_name}: {e}")
            return False
            
    async def _validate_model_versions(self, config: CanaryConfig) -> bool:
        """Validate that model versions exist in MLflow"""
        try:
            async with aiohttp.ClientSession() as session:
                # Check current version
                current_url = f"{self.mlflow_url}/api/2.0/mlflow/model-versions/get"
                current_params = {
                    "name": config.model_name,
                    "version": config.current_version
                }
                
                async with session.get(current_url, params=current_params) as response:
                    if response.status != 200:
                        logger.error(f"Current version {config.current_version} not found")
                        return False
                        
                # Check canary version
                canary_params = {
                    "name": config.model_name,
                    "version": config.canary_version
                }
                
                async with session.get(current_url, params=canary_params) as response:
                    if response.status != 200:
                        logger.error(f"Canary version {config.canary_version} not found")
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"Error validating model versions: {e}")
            return False
            
    async def _record_deployment(self, config: CanaryConfig, status: DeploymentStatus) -> None:
        """Record deployment status in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO model_deployments 
                (model_name, model_version, deployment_type, environment, 
                 traffic_percentage, status, deployment_config)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (model_name, model_version) 
                DO UPDATE SET status = $6, updated_at = CURRENT_TIMESTAMP
            """, config.model_name, config.canary_version, "canary", "production",
                config.initial_traffic_percentage, status.value, json.dumps(asdict(config)))
                
    async def _make_deployment_decision(self, config: CanaryConfig, 
                                      results: Dict[MetricType, ComparisonResult]) -> str:
        """Make deployment decision based on statistical analysis"""
        # Check if we have enough requests
        total_requests = len(results.get(MetricType.LATENCY, ComparisonResult(
            MetricType.LATENCY, 0, 0, 1, False, False, (0, 0)
        )).current_mean)
        
        if total_requests < config.min_requests_for_promotion:
            return "continue"
            
        # Check for critical failures
        error_result = results.get(MetricType.ERROR_RATE)
        if error_result and error_result.canary_mean > config.error_threshold:
            logger.warning(f"High error rate detected: {error_result.canary_mean}")
            return "rollback"
            
        latency_result = results.get(MetricType.LATENCY)
        if latency_result and latency_result.canary_mean > config.latency_threshold_ms:
            logger.warning(f"High latency detected: {latency_result.canary_mean}ms")
            return "rollback"
            
        # Check if canary is performing significantly better
        accuracy_result = results.get(MetricType.ACCURACY)
        if accuracy_result and accuracy_result.canary_is_better:
            current_traffic = await self._get_current_traffic_percentage(config)
            if current_traffic >= config.max_traffic_percentage and config.auto_promote:
                return "promote"
                
        # Check if canary is performing significantly worse
        significant_worse = any(
            result.is_significant and not result.canary_is_better
            for result in results.values()
        )
        
        if significant_worse and config.auto_rollback:
            return "rollback"
            
        return "continue"
        
    async def _get_current_traffic_percentage(self, config: CanaryConfig) -> int:
        """Get current traffic percentage for canary"""
        weights = await self.traffic_splitter.get_traffic_split(config.model_name)
        return weights.get(config.canary_version, 0)
        
    async def _increment_traffic(self, config: CanaryConfig) -> None:
        """Increment traffic to canary version"""
        current_traffic = await self._get_current_traffic_percentage(config)
        new_traffic = min(current_traffic + config.traffic_increment, 
                         config.max_traffic_percentage)
        
        await self.traffic_splitter.set_traffic_split(
            config.model_name,
            {
                config.current_version: 100 - new_traffic,
                config.canary_version: new_traffic
            }
        )
        
        logger.info(f"Increased canary traffic to {new_traffic}% for {config.model_name}")
        
    async def _promote_canary(self, config: CanaryConfig) -> None:
        """Promote canary to production"""
        logger.info(f"Promoting canary {config.canary_version} to production for {config.model_name}")
        
        # Set 100% traffic to canary
        await self.traffic_splitter.set_traffic_split(
            config.model_name,
            {config.canary_version: 100}
        )
        
        # Update model registry to mark canary as production
        async with aiohttp.ClientSession() as session:
            url = f"{self.mlflow_url}/api/2.0/mlflow/model-versions/transition-stage"
            data = {
                "name": config.model_name,
                "version": config.canary_version,
                "stage": "Production"
            }
            
            async with session.post(url, json=data) as response:
                if response.status != 200:
                    logger.error(f"Failed to update model stage: {response.status}")
                    
        # Update deployment status
        await self._record_deployment(config, DeploymentStatus.COMPLETED)
        
        # Remove from active deployments
        del self.active_deployments[config.model_name]
        
        deployment_counter.labels(
            model=config.model_name,
            version=config.canary_version,
            status="promoted"
        ).inc()
        
    async def _rollback_canary(self, config: CanaryConfig) -> None:
        """Rollback canary deployment"""
        logger.warning(f"Rolling back canary {config.canary_version} for {config.model_name}")
        
        # Set 100% traffic back to current version
        await self.traffic_splitter.set_traffic_split(
            config.model_name,
            {config.current_version: 100}
        )
        
        # Update deployment status
        await self._record_deployment(config, DeploymentStatus.FAILED)
        
        # Remove from active deployments
        del self.active_deployments[config.model_name]
        
        deployment_counter.labels(
            model=config.model_name,
            version=config.canary_version,
            status="rolled_back"
        ).inc()

async def main():
    """Main application entry point"""
    # Start Prometheus metrics server
    start_http_server(8080)
    
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
    redis_client = redis.from_url("redis://mlflow-redis:6379/2")
    
    # Initialize canary deployment manager
    manager = CanaryDeploymentManager(db_pool, redis_client)
    
    logger.info("GameForge Canary Deployment System started")
    
    # Main monitoring loop
    while True:
        try:
            # Monitor all active deployments
            for model_name in list(manager.active_deployments.keys()):
                await manager.monitor_deployment(model_name)
                
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"Error in main monitoring loop: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())