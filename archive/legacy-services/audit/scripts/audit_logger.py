#!/usr/bin/env python3
"""
GameForge Audit Integration Library
Provides standardized audit logging for GameForge applications
"""

import json
import time
import uuid
import logging
import requests
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class AuditEventType(Enum):
    """Standard audit event types"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    SYSTEM_CONFIGURATION = "system_configuration"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_EVENT = "compliance_event"
    USER_ACTION = "user_action"
    API_ACCESS = "api_access"
    GAME_EVENT = "game_event"

class SeverityLevel(Enum):
    """Audit event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Standard audit event structure"""
    event_id: str
    timestamp: str
    event_type: str
    action: str
    resource: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_code: Optional[str] = None
    duration_ms: Optional[int] = None
    service: str = "gameforge"
    severity: str = "low"
    compliance_required: bool = False
    security_event: bool = False
    compliance_violation: bool = False
    tags: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    data_classification: str = "internal"
    retention_policy: str = "standard"
    compliance_framework: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert audit event to JSON string"""
        return json.dumps(self.to_dict(), default=str)

class AuditLogger:
    """Central audit logging client"""

    def __init__(self, 
                 service_name: str,
                 elasticsearch_url: str = "http://elasticsearch-audit:9200",
                 kafka_brokers: str = "kafka-audit:29092",
                 enable_kafka: bool = True,
                 enable_elasticsearch: bool = True,
                 enable_file_logging: bool = True,
                 log_file_path: str = "/var/log/gameforge/audit/audit.log"):

        self.service_name = service_name
        self.elasticsearch_url = elasticsearch_url
        self.kafka_brokers = kafka_brokers
        self.enable_kafka = enable_kafka
        self.enable_elasticsearch = enable_elasticsearch
        self.enable_file_logging = enable_file_logging
        self.log_file_path = log_file_path

        # Initialize Kafka producer if enabled
        if self.enable_kafka:
            try:
                from kafka import KafkaProducer
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=[self.kafka_brokers],
                    value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                    retries=3,
                    acks='all'
                )
            except ImportError:
                logging.warning("Kafka library not available, disabling Kafka logging")
                self.enable_kafka = False

        # Initialize file logger if enabled
        if self.enable_file_logging:
            import os
            os.makedirs(os.path.dirname(self.log_file_path), exist_ok=True)

            self.file_logger = logging.getLogger(f"audit.{service_name}")
            self.file_logger.setLevel(logging.INFO)

            handler = logging.FileHandler(self.log_file_path)
            formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')
            handler.setFormatter(formatter)
            self.file_logger.addHandler(handler)

    def create_event(self,
                    event_type: AuditEventType,
                    action: str,
                    resource: str,
                    user_id: Optional[str] = None,
                    session_id: Optional[str] = None,
                    ip_address: Optional[str] = None,
                    user_agent: Optional[str] = None,
                    success: bool = True,
                    error_code: Optional[str] = None,
                    duration_ms: Optional[int] = None,
                    severity: SeverityLevel = SeverityLevel.LOW,
                    compliance_required: bool = False,
                    security_event: bool = False,
                    tags: Optional[Dict[str, Any]] = None,
                    trace_id: Optional[str] = None,
                    **kwargs) -> AuditEvent:
        """Create a standardized audit event"""

        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type=event_type.value,
            action=action,
            resource=resource,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_code=error_code,
            duration_ms=duration_ms,
            service=self.service_name,
            severity=severity.value,
            compliance_required=compliance_required,
            security_event=security_event,
            tags=tags or {},
            trace_id=trace_id,
            **kwargs
        )

        return event

    def log_event(self, event: AuditEvent):
        """Log audit event to all configured destinations"""

        # Log to Kafka for real-time processing
        if self.enable_kafka and hasattr(self, 'kafka_producer'):
            try:
                self.kafka_producer.send('audit-events', event.to_dict())
                self.kafka_producer.flush()
            except Exception as e:
                logging.error(f"Failed to send audit event to Kafka: {e}")

        # Log to Elasticsearch for storage and analysis
        if self.enable_elasticsearch:
            try:
                self._send_to_elasticsearch(event)
            except Exception as e:
                logging.error(f"Failed to send audit event to Elasticsearch: {e}")

        # Log to file for backup and local analysis
        if self.enable_file_logging:
            try:
                self.file_logger.info(event.to_json())
            except Exception as e:
                logging.error(f"Failed to write audit event to file: {e}")

    def _send_to_elasticsearch(self, event: AuditEvent):
        """Send audit event to Elasticsearch"""

        index_name = f"gameforge-audit-{datetime.now().strftime('%Y.%m.%d')}"
        url = f"{self.elasticsearch_url}/{index_name}/_doc"

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Basic ZWxhc3RpYzphdWRpdF9zZWN1cmVfcGFzc3dvcmRfMjAyNA=='  # elastic:audit_secure_password_2024
        }

        response = requests.post(url, json=event.to_dict(), headers=headers, timeout=5)
        response.raise_for_status()

    def log_authentication(self, user_id: str, success: bool, ip_address: str, 
                          method: str = "password", **kwargs):
        """Log authentication event"""
        event = self.create_event(
            event_type=AuditEventType.AUTHENTICATION,
            action=f"authentication_{method}",
            resource="auth_system",
            user_id=user_id,
            ip_address=ip_address,
            success=success,
            security_event=not success,
            compliance_required=True,
            **kwargs
        )
        self.log_event(event)

    def log_data_access(self, user_id: str, resource: str, action: str = "read",
                       success: bool = True, **kwargs):
        """Log data access event"""
        event = self.create_event(
            event_type=AuditEventType.DATA_ACCESS,
            action=f"data_{action}",
            resource=resource,
            user_id=user_id,
            success=success,
            compliance_required=True,
            **kwargs
        )
        self.log_event(event)

    def log_game_event(self, user_id: str, action: str, resource: str,
                      success: bool = True, **kwargs):
        """Log game-specific event"""
        event = self.create_event(
            event_type=AuditEventType.GAME_EVENT,
            action=action,
            resource=resource,
            user_id=user_id,
            success=success,
            **kwargs
        )
        self.log_event(event)

    def log_security_event(self, event_description: str, severity: SeverityLevel,
                          user_id: Optional[str] = None, ip_address: Optional[str] = None,
                          **kwargs):
        """Log security event"""
        event = self.create_event(
            event_type=AuditEventType.SECURITY_EVENT,
            action="security_incident",
            resource="security_system",
            user_id=user_id,
            ip_address=ip_address,
            success=False,
            severity=severity,
            security_event=True,
            compliance_required=True,
            tags={"description": event_description},
            **kwargs
        )
        self.log_event(event)

# Decorator for automatic audit logging
def audit_log(event_type: AuditEventType, action: str, resource: str = None):
    """Decorator to automatically log function calls"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            audit_logger = kwargs.get('audit_logger') or getattr(func, 'audit_logger', None)

            if not audit_logger:
                # Create default logger if none provided
                audit_logger = AuditLogger("gameforge")

            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)

                # Extract audit context from kwargs or function attributes
                user_id = kwargs.get('user_id') or getattr(func, 'user_id', None)
                session_id = kwargs.get('session_id') or getattr(func, 'session_id', None)

                event = audit_logger.create_event(
                    event_type=event_type,
                    action=action,
                    resource=resource or func.__name__,
                    user_id=user_id,
                    session_id=session_id,
                    success=True,
                    duration_ms=duration_ms
                )
                audit_logger.log_event(event)

                return result

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)

                event = audit_logger.create_event(
                    event_type=event_type,
                    action=action,
                    resource=resource or func.__name__,
                    success=False,
                    error_code=str(type(e).__name__),
                    duration_ms=duration_ms,
                    tags={"error_message": str(e)}
                )
                audit_logger.log_event(event)
                raise

        return wrapper
    return decorator

# Example usage
if __name__ == "__main__":
    # Initialize audit logger
    audit = AuditLogger("gameforge-api")

    # Log authentication
    audit.log_authentication(
        user_id="user123",
        success=True,
        ip_address="192.168.1.100",
        method="oauth2"
    )

    # Log data access
    audit.log_data_access(
        user_id="user123",
        resource="player_profile",
        action="read"
    )

    # Log security event
    audit.log_security_event(
        event_description="Suspicious login pattern detected",
        severity=SeverityLevel.HIGH,
        user_id="user123",
        ip_address="192.168.1.100"
    )
