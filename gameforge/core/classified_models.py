"""
Data Classification Database Integration
========================================

Production-ready SQLAlchemy models that integrate data classification into
GameForge's data persistence layer for automatic policy enforcement.
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set
import uuid

from gameforge.core.data_classification import (
    DataClassification, 
    DataClassificationPolicy,
    gameforge_classifier,
    SensitivityLevel,
    EncryptionRequirement,
    AccessPattern
)
from gameforge.core.database import Base

class ClassifiedDataMixin:
    """
    Mixin for database models that handle classified data.
    
    Automatically applies data classification policies to database models,
    including retention, encryption, and access control metadata.
    """
    
    @declared_attr
    def data_classification(cls):
        """Data classification for this model."""
        return Column(String(50), nullable=False, index=True)
    
    @declared_attr
    def sensitivity_level(cls):
        """Sensitivity level (1-5)."""
        return Column(Integer, nullable=False, default=3, index=True)
    
    @declared_attr
    def encryption_required(cls):
        """Encryption requirement level."""
        return Column(String(20), nullable=False, default="at_rest")
    
    @declared_attr
    def retention_until(cls):
        """When this data should be deleted based on retention policy."""
        return Column(DateTime, nullable=True, index=True)
    
    @declared_attr
    def archive_after(cls):
        """When this data should be archived."""
        return Column(DateTime, nullable=True, index=True)
    
    @declared_attr
    def classification_metadata(cls):
        """JSON metadata about classification policies applied."""
        return Column(JSON, nullable=True)
    
    @declared_attr
    def created_at(cls):
        """When the record was created."""
        return Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    @declared_attr
    def updated_at(cls):
        """When the record was last updated."""
        return Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @declared_attr
    def owner_id(cls):
        """ID of the user who owns this data."""
        return Column(String(36), nullable=True, index=True)
    
    @declared_attr
    def access_pattern(cls):
        """Current access pattern for this data."""
        return Column(String(20), nullable=False, default="owner_only")
    
    def __init_subclass__(cls, classification: DataClassification = None, **kwargs):
        """
        Initialize subclass with data classification.
        
        Args:
            classification: The data classification for this model
        """
        super().__init_subclass__(**kwargs)
        
        if classification:
            cls._data_classification = classification
            cls._apply_classification_policy()
    
    @classmethod
    def _apply_classification_policy(cls):
        """Apply data classification policy to the model."""
        if hasattr(cls, '_data_classification'):
            policy = gameforge_classifier.get_policy(cls._data_classification)
            if policy:
                cls._classification_policy = policy
    
    def apply_classification(self, classification: DataClassification, 
                           owner_id: str = None):
        """
        Apply data classification to this instance.
        
        Args:
            classification: The data classification to apply
            owner_id: The owner of this data
        """
        policy = gameforge_classifier.get_policy(classification)
        if not policy:
            raise ValueError(f"No policy found for classification {classification}")
        
        self.data_classification = classification.value
        self.sensitivity_level = policy.sensitivity.value
        self.encryption_required = policy.security.encryption.value
        self.owner_id = owner_id
        self.access_pattern = list(policy.access.allowed_patterns)[0].value if policy.access.allowed_patterns else "owner_only"
        
        # Calculate retention dates
        now = datetime.utcnow()
        if policy.retention.retention_period:
            self.retention_until = now + policy.retention.retention_period
        if policy.retention.archive_after:
            self.archive_after = now + policy.retention.archive_after
        
        # Store policy metadata
        self.classification_metadata = {
            "policy_applied_at": now.isoformat(),
            "retention_policy": policy.retention.to_dict(),
            "access_policy": policy.access.to_dict(),
            "security_policy": policy.security.to_dict(),
            "compliance": policy.compliance.to_dict()
        }
    
    def validate_access(self, user_roles: Set[str], access_pattern: AccessPattern,
                       is_owner: bool = False, is_admin: bool = False) -> bool:
        """
        Validate if access is allowed for this classified data.
        
        Args:
            user_roles: User's roles
            access_pattern: Requested access pattern
            is_owner: Whether user owns this data
            is_admin: Whether user is admin
            
        Returns:
            True if access is allowed, False otherwise
        """
        try:
            classification = DataClassification(self.data_classification)
            return gameforge_classifier.validate_access(
                classification, user_roles, access_pattern, is_owner, is_admin
            )
        except (ValueError, AttributeError):
            return False
    
    def is_expired(self) -> bool:
        """Check if this data has passed its retention period."""
        if self.retention_until:
            return datetime.utcnow() > self.retention_until
        return False
    
    def should_archive(self) -> bool:
        """Check if this data should be archived."""
        if self.archive_after:
            return datetime.utcnow() > self.archive_after
        return False
    
    def get_encryption_requirement(self) -> EncryptionRequirement:
        """Get the encryption requirement for this data."""
        try:
            return EncryptionRequirement(self.encryption_required)
        except ValueError:
            return EncryptionRequirement.AT_REST
    
    def get_sensitivity_level(self) -> SensitivityLevel:
        """Get the sensitivity level for this data."""
        try:
            return SensitivityLevel(self.sensitivity_level)
        except ValueError:
            return SensitivityLevel.CONFIDENTIAL
    
    def update_retention(self, new_classification: DataClassification = None):
        """Update retention dates based on current or new classification."""
        classification = new_classification or DataClassification(self.data_classification)
        policy = gameforge_classifier.get_policy(classification)
        
        if policy:
            now = datetime.utcnow()
            if policy.retention.retention_period:
                self.retention_until = now + policy.retention.retention_period
            if policy.retention.archive_after:
                self.archive_after = now + policy.retention.archive_after

class UserIdentityData(ClassifiedDataMixin):
    """Base class for user identity data."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.apply_classification(DataClassification.USER_IDENTITY, kwargs.get('owner_id'))

class UserAuthData(ClassifiedDataMixin):
    """Base class for user authentication data."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.apply_classification(DataClassification.USER_AUTH, kwargs.get('owner_id'))

class PaymentData(ClassifiedDataMixin):
    """Base class for payment and billing data."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.apply_classification(DataClassification.PAYMENT_DATA, kwargs.get('owner_id'))

class ProjectMetadata(ClassifiedDataMixin):
    """Base class for project metadata."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.apply_classification(DataClassification.PROJECT_METADATA, kwargs.get('owner_id'))

class AssetBinaries(ClassifiedDataMixin):
    """Base class for asset binaries and uploads."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.apply_classification(DataClassification.ASSET_BINARIES, kwargs.get('owner_id'))

class ModelArtifacts(ClassifiedDataMixin):
    """Base class for ML model artifacts."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.apply_classification(DataClassification.MODEL_ARTIFACTS, kwargs.get('owner_id'))

class AuditLogs(ClassifiedDataMixin):
    """Base class for audit logs."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.apply_classification(DataClassification.AUDIT_LOGS, kwargs.get('owner_id'))

class SecuritySecrets(ClassifiedDataMixin):
    """Base class for security secrets and keys."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.apply_classification(DataClassification.API_KEYS, kwargs.get('owner_id'))

class UsageAnalytics(ClassifiedDataMixin):
    """Base class for usage analytics and metrics."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.apply_classification(DataClassification.USAGE_ANALYTICS, kwargs.get('owner_id'))

# Utility functions for data classification in database operations

def classify_and_protect_data(data: Dict[str, Any], data_type: str, 
                            owner_id: str = None) -> Dict[str, Any]:
    """
    Classify data and add protection metadata.
    
    Args:
        data: Data dictionary to classify
        data_type: Type of data for classification
        owner_id: Owner of the data
        
    Returns:
        Data dictionary with classification metadata
    """
    classification = gameforge_classifier.classify_data(data_type)
    policy = gameforge_classifier.get_policy(classification)
    
    if policy:
        now = datetime.utcnow()
        
        data['data_classification'] = classification.value
        data['sensitivity_level'] = policy.sensitivity.value
        data['encryption_required'] = policy.security.encryption.value
        data['owner_id'] = owner_id
        data['created_at'] = now
        data['updated_at'] = now
        
        # Add retention dates
        if policy.retention.retention_period:
            data['retention_until'] = now + policy.retention.retention_period
        if policy.retention.archive_after:
            data['archive_after'] = now + policy.retention.archive_after
        
        # Add access pattern
        if policy.access.allowed_patterns:
            data['access_pattern'] = list(policy.access.allowed_patterns)[0].value
        
        # Add classification metadata
        data['classification_metadata'] = {
            "policy_applied_at": now.isoformat(),
            "classification": classification.value,
            "sensitivity": policy.sensitivity.value,
            "retention_policy": policy.retention.to_dict(),
            "access_policy": policy.access.to_dict(),
            "security_policy": policy.security.to_dict(),
            "compliance": policy.compliance.to_dict()
        }
    
    return data

def get_expired_data_query(session, model_class, current_time: datetime = None):
    """
    Get query for expired data based on retention policies.
    
    Args:
        session: SQLAlchemy session
        model_class: Model class to query
        current_time: Current time (defaults to now)
        
    Returns:
        Query for expired data
    """
    if current_time is None:
        current_time = datetime.utcnow()
    
    return session.query(model_class).filter(
        model_class.retention_until.isnot(None),
        model_class.retention_until < current_time
    )

def get_archivable_data_query(session, model_class, current_time: datetime = None):
    """
    Get query for data that should be archived.
    
    Args:
        session: SQLAlchemy session
        model_class: Model class to query
        current_time: Current time (defaults to now)
        
    Returns:
        Query for archivable data
    """
    if current_time is None:
        current_time = datetime.utcnow()
    
    return session.query(model_class).filter(
        model_class.archive_after.isnot(None),
        model_class.archive_after < current_time
    )

def audit_data_access(user_id: str, data_id: str, data_classification: str,
                     access_pattern: str, success: bool, session = None):
    """
    Audit data access for compliance and security monitoring.
    
    Args:
        user_id: ID of user accessing data
        data_id: ID of data being accessed
        data_classification: Classification of accessed data
        access_pattern: Type of access requested
        success: Whether access was granted
        session: Database session for logging
    """
    # This would integrate with your audit logging system
    audit_data = {
        "event_type": "data_access",
        "user_id": user_id,
        "data_id": data_id,
        "data_classification": data_classification,
        "access_pattern": access_pattern,
        "access_granted": success,
        "timestamp": datetime.utcnow().isoformat(),
        "ip_address": None,  # Would be filled by request context
        "user_agent": None   # Would be filled by request context
    }
    
    # Log to audit system (implementation depends on your logging infrastructure)
    print(f"AUDIT: {audit_data}")  # Placeholder - replace with actual audit logging