"""
GameForge Data Classification System
====================================

Production-ready data classification framework for consistent policy application
across user identity, payments, assets, models, logs, and security data.

This module provides:
- Data classification categories and sensitivity levels
- Policy definitions for retention, encryption, and access control
- Compliance and audit framework
- Integration points for data handling systems
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Set, Union, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

class DataClassification(Enum):
    """
    GameForge-specific data classification categories.
    Each category has distinct handling requirements and policies.
    """
    # A. User identity & authentication data
    USER_IDENTITY = "user_identity"
    USER_AUTH = "user_auth"
    
    # B. Payment & billing data (PCI-compliant)
    PAYMENT_DATA = "payment_data"
    BILLING_INFO = "billing_info"
    
    # C. Project & asset metadata
    PROJECT_METADATA = "project_metadata"
    ASSET_METADATA = "asset_metadata"
    
    # D. Asset binaries (high IP/PII risk)
    ASSET_BINARIES = "asset_binaries"
    USER_UPLOADS = "user_uploads"
    
    # E. Model artifacts & datasets
    MODEL_ARTIFACTS = "model_artifacts"
    TRAINING_DATASETS = "training_datasets"
    MODEL_METADATA = "model_metadata"
    
    # F. Logs & telemetry
    APPLICATION_LOGS = "application_logs"
    ACCESS_LOGS = "access_logs"
    AUDIT_LOGS = "audit_logs"
    SYSTEM_METRICS = "system_metrics"
    
    # G. Security secrets (highest sensitivity)
    API_KEYS = "api_keys"
    ENCRYPTION_KEYS = "encryption_keys"
    TLS_CERTIFICATES = "tls_certificates"
    VAULT_TOKENS = "vault_tokens"
    
    # H. Derived analytics (aggregated/anonymized)
    USAGE_ANALYTICS = "usage_analytics"
    BUSINESS_METRICS = "business_metrics"
    PERFORMANCE_METRICS = "performance_metrics"

class SensitivityLevel(Enum):
    """Data sensitivity levels with increasing security requirements."""
    PUBLIC = 1          # Public information, no protection needed
    INTERNAL = 2        # Internal use only, basic protection
    CONFIDENTIAL = 3    # Confidential data, strong protection
    RESTRICTED = 4      # Restricted access, very strong protection
    TOP_SECRET = 5      # Highest sensitivity, maximum protection

class EncryptionRequirement(Enum):
    """Encryption requirements for different data types."""
    NONE = "none"                    # No encryption required
    TRANSPORT = "transport"          # TLS in transit only
    AT_REST = "at_rest"             # Encryption at rest
    END_TO_END = "end_to_end"       # End-to-end encryption
    VAULT_MANAGED = "vault_managed"  # Vault/KMS managed encryption

class AccessPattern(Enum):
    """Common access patterns for policy enforcement."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    APPEND_ONLY = "append_only"
    ADMIN_ONLY = "admin_only"
    OWNER_ONLY = "owner_only"
    PUBLIC_READ = "public_read"

@dataclass
class RetentionPolicy:
    """Data retention policy configuration."""
    retention_period: timedelta
    archive_after: Optional[timedelta] = None
    purge_after: Optional[timedelta] = None
    legal_hold_override: bool = False
    backup_retention: Optional[timedelta] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "retention_days": self.retention_period.days,
            "archive_after_days": self.archive_after.days if self.archive_after else None,
            "purge_after_days": self.purge_after.days if self.purge_after else None,
            "legal_hold_override": self.legal_hold_override,
            "backup_retention_days": self.backup_retention.days if self.backup_retention else None
        }

@dataclass
class AccessPolicy:
    """Access control policy configuration."""
    allowed_patterns: Set[AccessPattern] = field(default_factory=set)
    required_roles: Set[str] = field(default_factory=set)
    owner_access: bool = True
    admin_override: bool = True
    audit_access: bool = True
    rate_limit: Optional[int] = None  # requests per minute
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed_patterns": [p.value for p in self.allowed_patterns],
            "required_roles": list(self.required_roles),
            "owner_access": self.owner_access,
            "admin_override": self.admin_override,
            "audit_access": self.audit_access,
            "rate_limit": self.rate_limit
        }

@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    encryption: EncryptionRequirement
    backup_encryption: EncryptionRequirement
    key_rotation_days: Optional[int] = None
    integrity_checks: bool = True
    audit_all_access: bool = False
    pii_detection: bool = False
    data_loss_prevention: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "encryption": self.encryption.value,
            "backup_encryption": self.backup_encryption.value,
            "key_rotation_days": self.key_rotation_days,
            "integrity_checks": self.integrity_checks,
            "audit_all_access": self.audit_all_access,
            "pii_detection": self.pii_detection,
            "data_loss_prevention": self.data_loss_prevention
        }

@dataclass
class ComplianceRequirements:
    """Compliance and regulatory requirements."""
    gdpr_applicable: bool = False
    ccpa_applicable: bool = False
    pci_dss_applicable: bool = False
    hipaa_applicable: bool = False
    soc2_applicable: bool = True  # Default for SaaS
    right_to_deletion: bool = False
    data_portability: bool = False
    breach_notification_required: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "gdpr": self.gdpr_applicable,
            "ccpa": self.ccpa_applicable,
            "pci_dss": self.pci_dss_applicable,
            "hipaa": self.hipaa_applicable,
            "soc2": self.soc2_applicable,
            "right_to_deletion": self.right_to_deletion,
            "data_portability": self.data_portability,
            "breach_notification": self.breach_notification_required
        }

@dataclass
class DataClassificationPolicy:
    """Complete policy definition for a data classification."""
    classification: DataClassification
    sensitivity: SensitivityLevel
    retention: RetentionPolicy
    access: AccessPolicy
    security: SecurityPolicy
    compliance: ComplianceRequirements
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary for JSON serialization."""
        return {
            "classification": self.classification.value,
            "sensitivity": self.sensitivity.value,
            "description": self.description,
            "retention": self.retention.to_dict(),
            "access": self.access.to_dict(),
            "security": self.security.to_dict(),
            "compliance": self.compliance.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def to_json(self) -> str:
        """Convert policy to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

class GameForgeDataClassifier:
    """
    GameForge Data Classification Engine.
    
    Provides standardized policies for all data types and handles
    classification-aware data operations.
    """
    
    def __init__(self):
        self._policies: Dict[DataClassification, DataClassificationPolicy] = {}
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Initialize default GameForge data classification policies."""
        
        # A. User Identity & Authentication
        self._policies[DataClassification.USER_IDENTITY] = DataClassificationPolicy(
            classification=DataClassification.USER_IDENTITY,
            sensitivity=SensitivityLevel.CONFIDENTIAL,
            retention=RetentionPolicy(
                retention_period=timedelta(days=2555),  # 7 years
                archive_after=timedelta(days=365),
                purge_after=timedelta(days=2555)
            ),
            access=AccessPolicy(
                allowed_patterns={AccessPattern.OWNER_ONLY, AccessPattern.ADMIN_ONLY},
                required_roles={"user", "admin"},
                audit_access=True,
                rate_limit=60
            ),
            security=SecurityPolicy(
                encryption=EncryptionRequirement.AT_REST,
                backup_encryption=EncryptionRequirement.AT_REST,
                key_rotation_days=90,
                pii_detection=True,
                audit_all_access=True
            ),
            compliance=ComplianceRequirements(
                gdpr_applicable=True,
                ccpa_applicable=True,
                right_to_deletion=True,
                data_portability=True
            ),
            description="User personal information: email, username, profile data"
        )
        
        self._policies[DataClassification.USER_AUTH] = DataClassificationPolicy(
            classification=DataClassification.USER_AUTH,
            sensitivity=SensitivityLevel.RESTRICTED,
            retention=RetentionPolicy(
                retention_period=timedelta(days=90),  # Short retention for auth tokens
                purge_after=timedelta(days=90)
            ),
            access=AccessPolicy(
                allowed_patterns={AccessPattern.OWNER_ONLY},
                required_roles={"authenticated"},
                audit_access=True,
                rate_limit=120
            ),
            security=SecurityPolicy(
                encryption=EncryptionRequirement.VAULT_MANAGED,
                backup_encryption=EncryptionRequirement.VAULT_MANAGED,
                key_rotation_days=30,
                audit_all_access=True
            ),
            compliance=ComplianceRequirements(
                breach_notification_required=True
            ),
            description="Authentication data: hashed passwords, OAuth tokens, session tokens"
        )
        
        # B. Payment & Billing (PCI-compliant)
        self._policies[DataClassification.PAYMENT_DATA] = DataClassificationPolicy(
            classification=DataClassification.PAYMENT_DATA,
            sensitivity=SensitivityLevel.TOP_SECRET,
            retention=RetentionPolicy(
                retention_period=timedelta(days=2555),  # 7 years for tax/audit
                archive_after=timedelta(days=365),
                legal_hold_override=True
            ),
            access=AccessPolicy(
                allowed_patterns={AccessPattern.ADMIN_ONLY},
                required_roles={"billing_admin", "compliance_officer"},
                audit_access=True,
                rate_limit=10
            ),
            security=SecurityPolicy(
                encryption=EncryptionRequirement.VAULT_MANAGED,
                backup_encryption=EncryptionRequirement.VAULT_MANAGED,
                key_rotation_days=30,
                integrity_checks=True,
                audit_all_access=True,
                data_loss_prevention=True
            ),
            compliance=ComplianceRequirements(
                pci_dss_applicable=True,
                breach_notification_required=True
            ),
            description="Payment method tokens, never raw card data (PCI-compliant)"
        )
        
        # C. Project & Asset Metadata
        self._policies[DataClassification.PROJECT_METADATA] = DataClassificationPolicy(
            classification=DataClassification.PROJECT_METADATA,
            sensitivity=SensitivityLevel.CONFIDENTIAL,
            retention=RetentionPolicy(
                retention_period=timedelta(days=1825),  # 5 years
                archive_after=timedelta(days=365)
            ),
            access=AccessPolicy(
                allowed_patterns={AccessPattern.OWNER_ONLY, AccessPattern.READ_WRITE},
                required_roles={"user"},
                owner_access=True,
                rate_limit=300
            ),
            security=SecurityPolicy(
                encryption=EncryptionRequirement.AT_REST,
                backup_encryption=EncryptionRequirement.AT_REST,
                key_rotation_days=180
            ),
            compliance=ComplianceRequirements(
                gdpr_applicable=True,
                right_to_deletion=True
            ),
            description="Project names, tags, descriptions, ownership, permissions"
        )
        
        # D. Asset Binaries (High IP/PII risk)
        self._policies[DataClassification.ASSET_BINARIES] = DataClassificationPolicy(
            classification=DataClassification.ASSET_BINARIES,
            sensitivity=SensitivityLevel.RESTRICTED,
            retention=RetentionPolicy(
                retention_period=timedelta(days=1825),  # 5 years
                archive_after=timedelta(days=180),
                backup_retention=timedelta(days=365)
            ),
            access=AccessPolicy(
                allowed_patterns={AccessPattern.OWNER_ONLY},
                required_roles={"user"},
                owner_access=True,
                rate_limit=60
            ),
            security=SecurityPolicy(
                encryption=EncryptionRequirement.END_TO_END,
                backup_encryption=EncryptionRequirement.VAULT_MANAGED,
                key_rotation_days=90,
                integrity_checks=True,
                pii_detection=True,
                data_loss_prevention=True
            ),
            compliance=ComplianceRequirements(
                gdpr_applicable=True,
                ccpa_applicable=True,
                right_to_deletion=True,
                data_portability=True
            ),
            description="Generated images, uploads - high IP and PII risk"
        )
        
        # E. Model Artifacts & Datasets
        self._policies[DataClassification.MODEL_ARTIFACTS] = DataClassificationPolicy(
            classification=DataClassification.MODEL_ARTIFACTS,
            sensitivity=SensitivityLevel.CONFIDENTIAL,
            retention=RetentionPolicy(
                retention_period=timedelta(days=1095),  # 3 years
                archive_after=timedelta(days=365),
                backup_retention=timedelta(days=730)
            ),
            access=AccessPolicy(
                allowed_patterns={AccessPattern.READ_ONLY, AccessPattern.ADMIN_ONLY},
                required_roles={"ml_engineer", "admin"},
                rate_limit=30
            ),
            security=SecurityPolicy(
                encryption=EncryptionRequirement.AT_REST,
                backup_encryption=EncryptionRequirement.AT_REST,
                key_rotation_days=180,
                integrity_checks=True
            ),
            compliance=ComplianceRequirements(),
            description="Base weights, LoRA deltas, training datasets, manifests"
        )
        
        # F. Logs & Telemetry
        self._policies[DataClassification.AUDIT_LOGS] = DataClassificationPolicy(
            classification=DataClassification.AUDIT_LOGS,
            sensitivity=SensitivityLevel.RESTRICTED,
            retention=RetentionPolicy(
                retention_period=timedelta(days=2555),  # 7 years for compliance
                archive_after=timedelta(days=90),
                legal_hold_override=True
            ),
            access=AccessPolicy(
                allowed_patterns={AccessPattern.APPEND_ONLY, AccessPattern.ADMIN_ONLY},
                required_roles={"security_admin", "compliance_officer"},
                audit_access=True,
                rate_limit=1000
            ),
            security=SecurityPolicy(
                encryption=EncryptionRequirement.AT_REST,
                backup_encryption=EncryptionRequirement.AT_REST,
                integrity_checks=True,
                audit_all_access=True
            ),
            compliance=ComplianceRequirements(
                soc2_applicable=True,
                breach_notification_required=True
            ),
            description="Security audit logs, access logs, compliance logs"
        )
        
        # G. Security Secrets (Highest sensitivity)
        self._policies[DataClassification.API_KEYS] = DataClassificationPolicy(
            classification=DataClassification.API_KEYS,
            sensitivity=SensitivityLevel.TOP_SECRET,
            retention=RetentionPolicy(
                retention_period=timedelta(days=90),
                purge_after=timedelta(days=90)
            ),
            access=AccessPolicy(
                allowed_patterns={AccessPattern.ADMIN_ONLY},
                required_roles={"security_admin", "infrastructure_admin"},
                audit_access=True,
                rate_limit=5
            ),
            security=SecurityPolicy(
                encryption=EncryptionRequirement.VAULT_MANAGED,
                backup_encryption=EncryptionRequirement.VAULT_MANAGED,
                key_rotation_days=30,
                integrity_checks=True,
                audit_all_access=True,
                data_loss_prevention=True
            ),
            compliance=ComplianceRequirements(
                breach_notification_required=True
            ),
            description="API keys, Vault tokens, TLS keys - Vault/KMS managed"
        )
        
        # H. Derived Analytics (Aggregated/anonymized)
        self._policies[DataClassification.USAGE_ANALYTICS] = DataClassificationPolicy(
            classification=DataClassification.USAGE_ANALYTICS,
            sensitivity=SensitivityLevel.INTERNAL,
            retention=RetentionPolicy(
                retention_period=timedelta(days=1095),  # 3 years
                archive_after=timedelta(days=365)
            ),
            access=AccessPolicy(
                allowed_patterns={AccessPattern.READ_ONLY, AccessPattern.PUBLIC_READ},
                required_roles={"analyst", "product_manager"},
                rate_limit=600
            ),
            security=SecurityPolicy(
                encryption=EncryptionRequirement.TRANSPORT,
                backup_encryption=EncryptionRequirement.AT_REST,
                key_rotation_days=365
            ),
            compliance=ComplianceRequirements(),
            description="Usage patterns, quotas, business metrics (aggregated/anonymized)"
        )
    
    def get_policy(self, classification: DataClassification) -> Optional[DataClassificationPolicy]:
        """Get policy for a specific data classification."""
        return self._policies.get(classification)
    
    def get_all_policies(self) -> Dict[DataClassification, DataClassificationPolicy]:
        """Get all data classification policies."""
        return self._policies.copy()
    
    def update_policy(self, policy: DataClassificationPolicy) -> None:
        """Update a data classification policy."""
        policy.updated_at = datetime.utcnow()
        self._policies[policy.classification] = policy
    
    def classify_data(self, data_type: str, content: Any = None) -> DataClassification:
        """
        Classify data based on type and content analysis.
        
        Args:
            data_type: String identifier of data type
            content: Optional content for analysis
            
        Returns:
            Appropriate DataClassification
        """
        # Simple rule-based classification
        data_type_lower = data_type.lower()
        
        if any(term in data_type_lower for term in ['email', 'username', 'profile', 'name']):
            return DataClassification.USER_IDENTITY
        elif any(term in data_type_lower for term in ['password', 'token', 'auth', 'login']):
            return DataClassification.USER_AUTH
        elif any(term in data_type_lower for term in ['payment', 'card', 'billing', 'invoice']):
            return DataClassification.PAYMENT_DATA
        elif any(term in data_type_lower for term in ['project', 'tag', 'description']):
            return DataClassification.PROJECT_METADATA
        elif any(term in data_type_lower for term in ['image', 'upload', 'asset', 'binary']):
            return DataClassification.ASSET_BINARIES
        elif any(term in data_type_lower for term in ['model', 'weight', 'dataset', 'training']):
            return DataClassification.MODEL_ARTIFACTS
        elif any(term in data_type_lower for term in ['log', 'audit', 'access']):
            return DataClassification.AUDIT_LOGS
        elif any(term in data_type_lower for term in ['key', 'secret', 'certificate', 'vault']):
            return DataClassification.API_KEYS
        elif any(term in data_type_lower for term in ['analytics', 'metrics', 'usage']):
            return DataClassification.USAGE_ANALYTICS
        else:
            # Default to internal if unsure
            return DataClassification.PROJECT_METADATA
    
    def validate_access(self, classification: DataClassification, 
                       user_roles: Set[str], access_pattern: AccessPattern,
                       is_owner: bool = False, is_admin: bool = False) -> bool:
        """
        Validate if access is allowed based on classification policy.
        
        Args:
            classification: Data classification
            user_roles: User's roles
            access_pattern: Requested access pattern
            is_owner: Whether user owns the data
            is_admin: Whether user is admin
            
        Returns:
            True if access is allowed, False otherwise
        """
        policy = self.get_policy(classification)
        if not policy:
            return False
        
        access_policy = policy.access
        
        # Admin override
        if is_admin and access_policy.admin_override:
            return True
        
        # Owner access
        if is_owner and access_policy.owner_access:
            return True
        
        # Check access pattern
        if access_pattern not in access_policy.allowed_patterns:
            return False
        
        # Check required roles
        if access_policy.required_roles and not access_policy.required_roles.intersection(user_roles):
            return False
        
        return True
    
    def get_retention_policy(self, classification: DataClassification) -> Optional[RetentionPolicy]:
        """Get retention policy for a data classification."""
        policy = self.get_policy(classification)
        return policy.retention if policy else None
    
    def get_encryption_requirement(self, classification: DataClassification) -> EncryptionRequirement:
        """Get encryption requirement for a data classification."""
        policy = self.get_policy(classification)
        return policy.security.encryption if policy else EncryptionRequirement.TRANSPORT
    
    def export_policies(self, file_path: str) -> None:
        """Export all policies to JSON file."""
        policies_dict = {
            classification.value: policy.to_dict() 
            for classification, policy in self._policies.items()
        }
        
        with open(file_path, 'w') as f:
            json.dump(policies_dict, f, indent=2)
    
    def get_compliance_requirements(self, classification: DataClassification) -> Optional[ComplianceRequirements]:
        """Get compliance requirements for a data classification."""
        policy = self.get_policy(classification)
        return policy.compliance if policy else None

# Global instance for application use
gameforge_classifier = GameForgeDataClassifier()

# Convenience functions
def classify_data(data_type: str, content: Any = None) -> DataClassification:
    """Classify data using the global classifier."""
    return gameforge_classifier.classify_data(data_type, content)

def get_policy(classification: DataClassification) -> Optional[DataClassificationPolicy]:
    """Get policy using the global classifier."""
    return gameforge_classifier.get_policy(classification)

def validate_access(classification: DataClassification, user_roles: Set[str], 
                   access_pattern: AccessPattern, is_owner: bool = False, 
                   is_admin: bool = False) -> bool:
    """Validate access using the global classifier."""
    return gameforge_classifier.validate_access(
        classification, user_roles, access_pattern, is_owner, is_admin
    )