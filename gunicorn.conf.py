"""
Gunicorn configuration for GameForge production deployment.
"""
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8080"
backlog = 2048

# Worker processes
workers = int(os.getenv("WORKERS", multiprocessing.cpu_count() * 2 + 1))
max_workers = int(os.getenv("MAX_WORKERS", workers * 2))
worker_class = os.getenv("WORKER_CLASS", "uvicorn.workers.UvicornWorker")
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True
timeout = int(os.getenv("WORKER_TIMEOUT", 300))
keepalive = 5

# Logging
loglevel = os.getenv("LOG_LEVEL", "info")
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "gameforge-app"

# Graceful shutdown
graceful_timeout = 30
max_requests_jitter = 10

# Security
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# SSL (if certificates are provided)
keyfile = os.getenv("SSL_KEYFILE")
certfile = os.getenv("SSL_CERTFILE")
ca_certs = os.getenv("SSL_CA_CERTS")
ssl_version = 5  # TLS 1.2+

# Worker configuration for uvicorn
raw_env = [
    "PYTHONPATH=/app",
    f"GAMEFORGE_ENV={os.getenv('GAMEFORGE_ENV', 'production')}",
]

# Health checks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("🚀 GameForge application starting up...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("🔄 GameForge application reloading...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("✅ GameForge application ready to serve requests")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("👋 GameForge application shutting down...")

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    server.log.info(f"👷 Worker {worker.pid} exited")

# Memory optimization
def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"👷 Worker {worker.pid} spawned")
    
    # Import torch and clean up if available
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            worker.log.info(f"🧹 GPU cache cleared for worker {worker.pid}")
    except ImportError:
        pass

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

# Application module
wsgi_app = "gameforge.app:app"