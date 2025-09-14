"""
Structured logging configuration for GameForge AI Platform.
Provides ELK-stack compatible JSON logging with proper context.
"""
import logging
import sys
import structlog
from typing import Any, Dict
import json
from datetime import datetime


class ELKFormatter(logging.Formatter):
    """Custom formatter for ELK stack compatibility."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON for ELK ingestion."""
        log_data = {
            "@timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "service": "gameforge-ai",
            "environment": "production"
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, default=str)


def setup_structured_logging():
    """
    Configure structured logging for the entire application.
    Sets up both standard logging and structlog for ELK compatibility.
    """
    # Configure standard logging with ELK formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ELKFormatter())
    
    # Remove default handlers and add our ELK handler
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    
    # Configure structlog for structured logging
    structlog.configure(
        processors=[
            # Filter by log level
            structlog.stdlib.filter_by_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Add log level
            structlog.stdlib.add_log_level,
            # Process positional arguments
            structlog.stdlib.PositionalArgumentsFormatter(),
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Add stack info for errors
            structlog.processors.StackInfoRenderer(),
            # Format exception info
            structlog.processors.format_exc_info,
            # Ensure unicode
            structlog.processors.UnicodeDecoder(),
            # Add service metadata
            add_service_metadata,
            # Output as JSON
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def add_service_metadata(logger, method_name, event_dict):
    """Add consistent service metadata to all log entries."""
    event_dict["service"] = "gameforge-ai"
    event_dict["environment"] = "production"
    event_dict["deployment"] = "vastai"
    return event_dict


def get_structured_logger(name: str):
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def log_ai_job_event(
    event_type: str,
    job_id: str,
    user_id: str,
    model: str = None,
    duration: float = None,
    error: str = None,
    **kwargs
):
    """
    Standardized logging for AI job events.
    
    Args:
        event_type: Type of event (job_started, job_completed, job_failed, etc.)
        job_id: Unique job identifier
        user_id: User who initiated the job
        model: AI model used
        duration: Job duration in seconds
        error: Error message if applicable
        **kwargs: Additional context fields
    """
    logger = get_structured_logger("gameforge.ai.jobs")
    
    log_data = {
        "event_type": event_type,
        "job_id": job_id,
        "user_id": user_id,
        **kwargs
    }
    
    if model:
        log_data["model"] = model
    if duration is not None:
        log_data["duration"] = duration
    if error:
        log_data["error"] = error
    
    if event_type.endswith("_failed") or error:
        logger.error(f"AI job event: {event_type}", **log_data)
    else:
        logger.info(f"AI job event: {event_type}", **log_data)


def log_security_event(
    event_type: str,
    user_id: str = None,
    ip_address: str = None,
    severity: str = "info",
    **kwargs
):
    """
    Standardized logging for security events.
    
    Args:
        event_type: Type of security event
        user_id: User involved in the event
        ip_address: Source IP address
        severity: Event severity (info, warning, error, critical)
        **kwargs: Additional context fields
    """
    logger = get_structured_logger("gameforge.security")
    
    log_data = {
        "event_type": event_type,
        "severity": severity,
        **kwargs
    }
    
    if user_id:
        log_data["user_id"] = user_id
    if ip_address:
        log_data["ip_address"] = ip_address
    
    if severity in ["error", "critical"]:
        logger.error(f"Security event: {event_type}", **log_data)
    elif severity == "warning":
        logger.warning(f"Security event: {event_type}", **log_data)
    else:
        logger.info(f"Security event: {event_type}", **log_data)


def log_api_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
    user_id: str = None,
    ip_address: str = None,
    **kwargs
):
    """
    Standardized logging for API requests.
    
    Args:
        method: HTTP method
        endpoint: API endpoint
        status_code: HTTP status code
        duration: Request duration in seconds
        user_id: Authenticated user ID
        ip_address: Client IP address
        **kwargs: Additional context fields
    """
    logger = get_structured_logger("gameforge.api")
    
    log_data = {
        "event_type": "api_request",
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration": duration,
        **kwargs
    }
    
    if user_id:
        log_data["user_id"] = user_id
    if ip_address:
        log_data["ip_address"] = ip_address
    
    if status_code >= 500:
        logger.error(f"API request: {method} {endpoint}", **log_data)
    elif status_code >= 400:
        logger.warning(f"API request: {method} {endpoint}", **log_data)
    else:
        logger.info(f"API request: {method} {endpoint}", **log_data)