#!/usr/bin/env python3
"""
GameForge AI Application Metrics Integration
Integrates Prometheus metrics directly into the FastAPI application
"""

import time
import psutil
import asyncio
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import PlainTextResponse
from prometheus_client import (
    Counter, Histogram, Gauge, Info, Summary,
    CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
)
import redis
import psycopg2
from sqlalchemy import create_engine, text

# ========================================================================
# Prometheus Metrics Definition
# ========================================================================

# Create custom registry for GameForge metrics
gameforge_registry = CollectorRegistry()

# HTTP Request Metrics
http_requests_total = Counter(
    'gameforge_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=gameforge_registry
)

http_request_duration = Histogram(
    'gameforge_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=gameforge_registry,
    buckets=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]
)

# AI/ML Specific Metrics
inference_requests_total = Counter(
    'gameforge_inference_requests_total',
    'Total AI inference requests',
    ['model', 'status'],
    registry=gameforge_registry
)

inference_duration = Histogram(
    'gameforge_inference_duration_seconds',
    'AI inference duration in seconds',
    ['model'],
    registry=gameforge_registry,
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0]
)

model_load_time = Histogram(
    'gameforge_model_load_time_seconds',
    'Time taken to load AI models',
    ['model'],
    registry=gameforge_registry
)

gpu_utilization = Gauge(
    'gameforge_gpu_utilization_percent',
    'GPU utilization percentage',
    ['gpu_id'],
    registry=gameforge_registry
)

gpu_memory_used = Gauge(
    'gameforge_gpu_memory_used_bytes',
    'GPU memory used in bytes',
    ['gpu_id'],
    registry=gameforge_registry
)

gpu_memory_total = Gauge(
    'gameforge_gpu_memory_total_bytes',
    'GPU memory total in bytes',
    ['gpu_id'],
    registry=gameforge_registry
)

# Application Metrics
active_connections = Gauge(
    'gameforge_active_connections',
    'Number of active connections',
    registry=gameforge_registry
)

cache_hits_total = Counter(
    'gameforge_cache_hits_total',
    'Total cache hits',
    ['cache_type'],
    registry=gameforge_registry
)

cache_misses_total = Counter(
    'gameforge_cache_misses_total',
    'Total cache misses',
    ['cache_type'],
    registry=gameforge_registry
)

# Database Metrics
db_connections_active = Gauge(
    'gameforge_db_connections_active',
    'Active database connections',
    registry=gameforge_registry
)

db_query_duration = Histogram(
    'gameforge_db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    registry=gameforge_registry
)

# System Metrics
system_memory_usage = Gauge(
    'gameforge_system_memory_usage_bytes',
    'System memory usage in bytes',
    registry=gameforge_registry
)

system_cpu_usage = Gauge(
    'gameforge_system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=gameforge_registry
)

# Application Info
app_info = Info(
    'gameforge_app_info',
    'GameForge application information',
    registry=gameforge_registry
)

# ========================================================================
# Metrics Collection Classes
# ========================================================================

class MetricsCollector:
    """Collects and updates GameForge metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.redis_client = None
        self.db_engine = None
        self._setup_connections()
        
    def _setup_connections(self):
        """Setup Redis and Database connections"""
        try:
            # Redis connection
            self.redis_client = redis.Redis(
                host='redis',
                port=6379,
                decode_responses=True,
                socket_connect_timeout=5
            )
            
            # Database connection
            self.db_engine = create_engine(
                'postgresql://gameforge:gameforge_password@postgres:5432/gameforge_prod',
                pool_size=5,
                max_overflow=10
            )
            
        except Exception as e:
            self.logger.error(f"Failed to setup connections: {e}")
    
    async def collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            system_cpu_usage.set(cpu_percent)
            system_memory_usage.set(memory.used)
            
            # GPU Metrics (if available)
            await self._collect_gpu_metrics()
            
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    async def _collect_gpu_metrics(self):
        """Collect GPU metrics using nvidia-ml-py"""
        try:
            import pynvml
            
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                # GPU utilization
                utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                gpu_utilization.labels(gpu_id=str(i)).set(utilization.gpu)
                
                # GPU memory
                memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_memory_used.labels(gpu_id=str(i)).set(memory_info.used)
                gpu_memory_total.labels(gpu_id=str(i)).set(memory_info.total)
                
        except ImportError:
            # pynvml not available, skip GPU metrics
            pass
        except Exception as e:
            self.logger.error(f"Failed to collect GPU metrics: {e}")
    
    async def collect_database_metrics(self):
        """Collect database metrics"""
        try:
            if self.db_engine:
                with self.db_engine.connect() as conn:
                    # Active connections
                    result = conn.execute(text(
                        "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                    ))
                    active_count = result.scalar()
                    db_connections_active.set(active_count)
                    
        except Exception as e:
            self.logger.error(f"Failed to collect database metrics: {e}")
    
    async def collect_cache_metrics(self):
        """Collect cache metrics"""
        try:
            if self.redis_client:
                info = self.redis_client.info()
                
                # Cache hit ratio can be calculated from keyspace hits/misses
                if 'keyspace_hits' in info and 'keyspace_misses' in info:
                    cache_hits_total.labels(cache_type='redis')._value._value = info['keyspace_hits']
                    cache_misses_total.labels(cache_type='redis')._value._value = info['keyspace_misses']
                    
        except Exception as e:
            self.logger.error(f"Failed to collect cache metrics: {e}")

# ========================================================================
# Metrics Middleware
# ========================================================================

class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to collect HTTP metrics"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Get request info
        method = request.method
        path = request.url.path
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise e
        finally:
            # Record metrics
            duration = time.time() - start_time
            
            http_requests_total.labels(
                method=method,
                endpoint=path,
                status_code=status_code
            ).inc()
            
            http_request_duration.labels(
                method=method,
                endpoint=path
            ).observe(duration)
        
        return response

# ========================================================================
# FastAPI Integration
# ========================================================================

def setup_metrics(app: FastAPI) -> MetricsCollector:
    """Setup metrics for FastAPI application"""
    
    # Initialize metrics collector
    collector = MetricsCollector()
    
    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)
    
    # Set application info
    app_info.info({
        'version': '1.0.0',
        'environment': 'production',
        'service': 'gameforge-app'
    })
    
    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics_endpoint():
        """Prometheus metrics endpoint"""
        # Collect latest metrics
        await collector.collect_system_metrics()
        await collector.collect_database_metrics()
        await collector.collect_cache_metrics()
        
        # Generate Prometheus format
        return generate_latest(gameforge_registry)
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint with metrics"""
        try:
            # Check database
            db_healthy = True
            if collector.db_engine:
                with collector.db_engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            
            # Check Redis
            redis_healthy = True
            if collector.redis_client:
                collector.redis_client.ping()
            
            # Check GPU (if available)
            gpu_healthy = True
            try:
                import pynvml
                pynvml.nvmlInit()
            except:
                gpu_healthy = False
            
            health_status = {
                "status": "healthy",
                "database": db_healthy,
                "redis": redis_healthy,
                "gpu": gpu_healthy,
                "timestamp": time.time()
            }
            
            return health_status
            
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Health check failed: {e}")
    
    # Background task to collect metrics periodically
    @asynccontextmanager
    async def metrics_collection_task():
        async def collect_periodically():
            while True:
                try:
                    await collector.collect_system_metrics()
                    await collector.collect_database_metrics()
                    await collector.collect_cache_metrics()
                except Exception as e:
                    logging.error(f"Metrics collection error: {e}")
                await asyncio.sleep(30)  # Collect every 30 seconds
        
        task = asyncio.create_task(collect_periodically())
        yield
        task.cancel()
    
    # Add the background task to app lifespan
    app.router.lifespan_context = metrics_collection_task
    
    return collector

# ========================================================================
# Inference Metrics Decorators
# ========================================================================

def track_inference(model_name: str):
    """Decorator to track AI inference metrics"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                status = "success"
                return result
            except Exception as e:
                status = "error"
                raise e
            finally:
                duration = time.time() - start_time
                
                inference_requests_total.labels(
                    model=model_name,
                    status=status
                ).inc()
                
                inference_duration.labels(
                    model=model_name
                ).observe(duration)
        
        return wrapper
    return decorator

def track_model_loading(model_name: str):
    """Decorator to track model loading metrics"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                model_load_time.labels(model=model_name).observe(duration)
        
        return wrapper
    return decorator

# ========================================================================
# Usage Example
# ========================================================================

if __name__ == "__main__":
    # Example FastAPI app with metrics
    app = FastAPI(title="GameForge AI", version="1.0.0")
    
    # Setup metrics
    metrics_collector = setup_metrics(app)
    
    @app.get("/")
    async def root():
        return {"message": "GameForge AI with Prometheus metrics"}
    
    @app.post("/generate")
    @track_inference("stable-diffusion-xl")
    async def generate_image(prompt: str):
        # Simulate AI inference
        await asyncio.sleep(2)
        return {"prompt": prompt, "status": "generated"}
    
    # Run with: uvicorn gameforge_metrics_app:app --host 0.0.0.0 --port 8080