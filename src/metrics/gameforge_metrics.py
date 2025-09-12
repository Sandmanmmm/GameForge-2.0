# ========================================================================
# GameForge Application Metrics Implementation
# Prometheus metrics endpoints for custom services
# ========================================================================

import time
import psutil
import nvidia_ml_py3 as nvml
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
from flask import Flask, Response
import threading
from functools import wraps

class GameForgeMetrics:
    """Production metrics collection for GameForge AI platform"""
    
    def __init__(self):
        # Initialize NVIDIA ML
        try:
            nvml.nvmlInit()
            self.gpu_available = True
            self.gpu_count = nvml.nvmlDeviceGetCount()
        except:
            self.gpu_available = False
            self.gpu_count = 0
        
        # Application Metrics
        self.http_requests_total = Counter(
            'gameforge_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status']
        )
        
        self.inference_requests_total = Counter(
            'gameforge_inference_requests_total',
            'Total inference requests',
            ['model', 'status']
        )
        
        self.inference_duration = Histogram(
            'gameforge_inference_request_duration_seconds',
            'Inference request duration',
            ['model'],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )
        
        self.model_load_duration = Histogram(
            'gameforge_model_load_duration_seconds',
            'Model loading duration',
            ['model_name'],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
        )
        
        # GPU Metrics
        self.gpu_utilization = Gauge(
            'gameforge_gpu_utilization_percent',
            'GPU utilization percentage',
            ['gpu_id', 'gpu_name']
        )
        
        self.gpu_memory_used = Gauge(
            'gameforge_gpu_memory_used_bytes',
            'GPU memory used in bytes',
            ['gpu_id', 'gpu_name']
        )
        
        self.gpu_memory_total = Gauge(
            'gameforge_gpu_memory_total_bytes',
            'GPU memory total in bytes',
            ['gpu_id', 'gpu_name']
        )
        
        self.gpu_temperature = Gauge(
            'gameforge_gpu_temperature_celsius',
            'GPU temperature in Celsius',
            ['gpu_id', 'gpu_name']
        )
        
        # Model Storage Metrics
        self.model_downloads_total = Counter(
            'gameforge_model_download_total',
            'Total model downloads',
            ['model', 'status']
        )
        
        self.model_cache_hits = Counter(
            'gameforge_model_cache_hits_total',
            'Model cache hits'
        )
        
        self.model_cache_misses = Counter(
            'gameforge_model_cache_misses_total',
            'Model cache misses'
        )
        
        self.model_storage_size = Gauge(
            'gameforge_model_storage_bytes',
            'Model storage size in bytes',
            ['model']
        )
        
        # Security Metrics
        self.security_events_total = Counter(
            'gameforge_security_events_total',
            'Security events detected',
            ['event_type', 'severity']
        )
        
        self.auth_attempts_total = Counter(
            'gameforge_auth_attempts_total',
            'Authentication attempts',
            ['status', 'method']
        )
        
        # System Metrics
        self.worker_queue_size = Gauge(
            'gameforge_worker_queue_size',
            'Worker queue size',
            ['queue_name']
        )
        
        self.active_connections = Gauge(
            'gameforge_active_connections',
            'Active connections'
        )
        
        # Application Info
        self.app_info = Info(
            'gameforge_app_info',
            'Application information'
        )
        
        # Start background metrics collection
        self._start_background_collection()
    
    def _start_background_collection(self):
        """Start background thread for continuous metrics collection"""
        def collect_metrics():
            while True:
                try:
                    self._collect_gpu_metrics()
                    self._collect_system_metrics()
                    time.sleep(5)  # Collect every 5 seconds
                except Exception as e:
                    print(f"Error in metrics collection: {e}")
                    time.sleep(10)
        
        thread = threading.Thread(target=collect_metrics, daemon=True)
        thread.start()
    
    def _collect_gpu_metrics(self):
        """Collect GPU metrics using nvidia-ml-py"""
        if not self.gpu_available:
            return
        
        try:
            for i in range(self.gpu_count):
                handle = nvml.nvmlDeviceGetHandleByIndex(i)
                
                # GPU name
                name = nvml.nvmlDeviceGetName(handle).decode('utf-8')
                
                # Utilization
                util = nvml.nvmlDeviceGetUtilizationRates(handle)
                self.gpu_utilization.labels(gpu_id=str(i), gpu_name=name).set(util.gpu)
                
                # Memory
                mem_info = nvml.nvmlDeviceGetMemoryInfo(handle)
                self.gpu_memory_used.labels(gpu_id=str(i), gpu_name=name).set(mem_info.used)
                self.gpu_memory_total.labels(gpu_id=str(i), gpu_name=name).set(mem_info.total)
                
                # Temperature
                try:
                    temp = nvml.nvmlDeviceGetTemperature(handle, nvml.NVML_TEMPERATURE_GPU)
                    self.gpu_temperature.labels(gpu_id=str(i), gpu_name=name).set(temp)
                except:
                    pass  # Temperature might not be available
                
        except Exception as e:
            print(f"Error collecting GPU metrics: {e}")
    
    def _collect_system_metrics(self):
        """Collect system metrics"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            # Update application info
            self.app_info.info({
                'version': '1.0.0',
                'environment': 'production',
                'deployment': 'vastai',
                'cpu_cores': str(psutil.cpu_count()),
                'memory_total': str(memory.total),
                'gpu_count': str(self.gpu_count)
            })
            
        except Exception as e:
            print(f"Error collecting system metrics: {e}")
    
    # Decorator for timing inference requests
    def time_inference(self, model_name):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    self.inference_requests_total.labels(model=model_name, status='success').inc()
                    return result
                except Exception as e:
                    self.inference_requests_total.labels(model=model_name, status='error').inc()
                    raise
                finally:
                    duration = time.time() - start_time
                    self.inference_duration.labels(model=model_name).observe(duration)
            return wrapper
        return decorator
    
    # Decorator for timing model loading
    def time_model_load(self, model_name):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    self.model_load_duration.labels(model_name=model_name).observe(duration)
            return wrapper
        return decorator
    
    def record_http_request(self, method, endpoint, status):
        """Record HTTP request metrics"""
        self.http_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
    
    def record_security_event(self, event_type, severity='info'):
        """Record security events"""
        self.security_events_total.labels(event_type=event_type, severity=severity).inc()
    
    def record_auth_attempt(self, status, method='password'):
        """Record authentication attempts"""
        self.auth_attempts_total.labels(status=status, method=method).inc()
    
    def update_queue_size(self, queue_name, size):
        """Update worker queue size"""
        self.worker_queue_size.labels(queue_name=queue_name).set(size)
    
    def record_model_download(self, model, status):
        """Record model download events"""
        self.model_downloads_total.labels(model=model, status=status).inc()
    
    def record_cache_hit(self):
        """Record model cache hit"""
        self.model_cache_hits.inc()
    
    def record_cache_miss(self):
        """Record model cache miss"""
        self.model_cache_misses.inc()

# Global metrics instance
metrics = GameForgeMetrics()

# Flask app for metrics endpoint
app = Flask(__name__)

@app.route('/metrics')
def prometheus_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), mimetype='text/plain')

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'healthy', 'timestamp': time.time()}

@app.route('/metrics/gpu')
def gpu_metrics():
    """GPU-specific metrics endpoint"""
    gpu_data = {}
    if metrics.gpu_available:
        for i in range(metrics.gpu_count):
            try:
                handle = nvml.nvmlDeviceGetHandleByIndex(i)
                name = nvml.nvmlDeviceGetName(handle).decode('utf-8')
                util = nvml.nvmlDeviceGetUtilizationRates(handle)
                mem_info = nvml.nvmlDeviceGetMemoryInfo(handle)
                
                gpu_data[f'gpu_{i}'] = {
                    'name': name,
                    'utilization': util.gpu,
                    'memory_used': mem_info.used,
                    'memory_total': mem_info.total,
                    'memory_percent': (mem_info.used / mem_info.total) * 100
                }
            except:
                pass
    
    return gpu_data

if __name__ == '__main__':
    # Run metrics server
    app.run(host='0.0.0.0', port=8080, debug=False)