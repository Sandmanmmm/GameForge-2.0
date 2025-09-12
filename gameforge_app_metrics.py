
from flask import Flask, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time
import psutil
import threading

app = Flask(__name__)

# Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_CONNECTIONS = Gauge('active_connections', 'Active connections')
CPU_USAGE = Gauge('cpu_usage_percent', 'CPU usage percentage')
MEMORY_USAGE = Gauge('memory_usage_percent', 'Memory usage percentage')

def update_system_metrics():
    """Update system metrics in background"""
    while True:
        CPU_USAGE.set(psutil.cpu_percent())
        memory = psutil.virtual_memory()
        MEMORY_USAGE.set(memory.percent)
        time.sleep(30)

# Start metrics update thread
metrics_thread = threading.Thread(target=update_system_metrics, daemon=True)
metrics_thread.start()

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), mimetype='text/plain')

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'healthy', 'timestamp': time.time()}

@app.before_request
def before_request():
    """Track request start time"""
    REQUEST_DURATION.time()

@app.after_request
def after_request(response):
    """Track request metrics"""
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown',
        status=response.status_code
    ).inc()
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
