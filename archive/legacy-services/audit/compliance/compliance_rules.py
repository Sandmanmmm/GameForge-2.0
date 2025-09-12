# Compliance Monitoring Configuration
# File: audit/compliance/compliance_rules.py

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

class ComplianceMonitor:
    def __init__(self):
        self.compliance_frameworks = {
            "SOC2": {
                "description": "SOC 2 Type II Compliance",
                "requirements": [
                    "user_access_logging",
                    "data_encryption_audit",
                    "system_availability_monitoring",
                    "data_processing_integrity",
                    "confidentiality_controls"
                ]
            },
            "GDPR": {
                "description": "General Data Protection Regulation",
                "requirements": [
                    "data_access_logging", 
                    "consent_tracking",
                    "data_deletion_audit",
                    "data_transfer_logging",
                    "breach_notification"
                ]
            },
            "PCI_DSS": {
                "description": "Payment Card Industry Data Security Standard",
                "requirements": [
                    "payment_transaction_logging",
                    "cardholder_data_access",
                    "security_testing_audit",
                    "access_control_monitoring"
                ]
            },
            "HIPAA": {
                "description": "Health Insurance Portability and Accountability Act",
                "requirements": [
                    "phi_access_logging",
                    "user_authentication_audit",
                    "data_transmission_logging",
                    "security_incident_tracking"
                ]
            }
        }

    def evaluate_soc2_compliance(self, audit_data: List[Dict]) -> Dict:
        """Evaluate SOC 2 compliance based on audit data"""

        compliance_score = 0
        total_checks = 5
        violations = []

        # Security - Access controls and user authentication
        auth_events = [event for event in audit_data if event.get('action') == 'authentication']
        if auth_events:
            failed_auth_rate = len([e for e in auth_events if not e.get('success', True)]) / len(auth_events)
            if failed_auth_rate < 0.05:  # Less than 5% failure rate
                compliance_score += 1
            else:
                violations.append(f"High authentication failure rate: {failed_auth_rate:.2%}")

        # Availability - System uptime and performance monitoring
        system_events = [event for event in audit_data if event.get('service') == 'system']
        uptime_events = [e for e in system_events if e.get('action') == 'health_check' and e.get('success')]
        if len(uptime_events) > 0:
            compliance_score += 1
        else:
            violations.append("Insufficient system availability monitoring")

        # Processing Integrity - Data processing accuracy
        data_events = [event for event in audit_data if 'data_processing' in event.get('action', '')]
        if data_events:
            success_rate = len([e for e in data_events if e.get('success', True)]) / len(data_events)
            if success_rate > 0.99:  # 99% success rate
                compliance_score += 1
            else:
                violations.append(f"Data processing integrity issue: {success_rate:.2%} success rate")

        # Confidentiality - Data access controls
        access_events = [event for event in audit_data if event.get('action') == 'data_access']
        unauthorized_access = [e for e in access_events if e.get('compliance_violation', False)]
        if len(unauthorized_access) == 0:
            compliance_score += 1
        else:
            violations.append(f"Unauthorized data access detected: {len(unauthorized_access)} events")

        # Privacy - Personal data handling
        privacy_events = [event for event in audit_data if 'personal_data' in event.get('resource', '')]
        if privacy_events:
            compliance_score += 1

        return {
            "framework": "SOC2",
            "compliance_score": compliance_score / total_checks,
            "violations": violations,
            "recommendation": "Maintain continuous monitoring and remediate violations",
            "next_audit_date": (datetime.now() + timedelta(days=90)).isoformat()
        }

    def evaluate_gdpr_compliance(self, audit_data: List[Dict]) -> Dict:
        """Evaluate GDPR compliance based on audit data"""

        compliance_score = 0
        total_checks = 4
        violations = []

        # Data access logging (Article 30)
        access_logs = [event for event in audit_data if event.get('action') in ['data_access', 'data_view']]
        if access_logs and all('user_id' in event for event in access_logs):
            compliance_score += 1
        else:
            violations.append("Incomplete data access logging")

        # Consent tracking (Article 7)
        consent_events = [event for event in audit_data if 'consent' in event.get('action', '')]
        if consent_events:
            compliance_score += 1
        else:
            violations.append("Missing consent tracking mechanisms")

        # Data deletion audit (Article 17 - Right to erasure)
        deletion_events = [event for event in audit_data if event.get('action') == 'data_deletion']
        if deletion_events:
            compliance_score += 1
        else:
            violations.append("No data deletion audit trail found")

        # Breach notification (Article 33)
        security_incidents = [event for event in audit_data if event.get('security_event', False)]
        breach_notifications = [event for event in audit_data if event.get('action') == 'breach_notification']
        if len(security_incidents) == 0 or len(breach_notifications) > 0:
            compliance_score += 1
        else:
            violations.append("Security incidents without proper breach notification")

        return {
            "framework": "GDPR",
            "compliance_score": compliance_score / total_checks,
            "violations": violations,
            "data_subject_rights": {
                "access_requests": len([e for e in audit_data if e.get('action') == 'data_access_request']),
                "deletion_requests": len([e for e in audit_data if e.get('action') == 'data_deletion_request']),
                "portability_requests": len([e for e in audit_data if e.get('action') == 'data_portability_request'])
            },
            "recommendation": "Ensure complete audit trails for all personal data processing",
            "next_audit_date": (datetime.now() + timedelta(days=365)).isoformat()
        }

    def generate_compliance_report(self, audit_data: List[Dict]) -> Dict:
        """Generate comprehensive compliance report"""

        report = {
            "report_timestamp": datetime.now().isoformat(),
            "audit_period": {
                "start": (datetime.now() - timedelta(days=30)).isoformat(),
                "end": datetime.now().isoformat()
            },
            "compliance_evaluations": {}
        }

        # Evaluate each compliance framework
        report["compliance_evaluations"]["SOC2"] = self.evaluate_soc2_compliance(audit_data)
        report["compliance_evaluations"]["GDPR"] = self.evaluate_gdpr_compliance(audit_data)

        # Overall compliance summary
        total_frameworks = len(report["compliance_evaluations"])
        average_score = sum(eval_result["compliance_score"] for eval_result in report["compliance_evaluations"].values()) / total_frameworks

        report["overall_compliance"] = {
            "average_score": average_score,
            "status": "COMPLIANT" if average_score > 0.8 else "NON_COMPLIANT" if average_score < 0.6 else "PARTIAL_COMPLIANCE",
            "total_violations": sum(len(eval_result["violations"]) for eval_result in report["compliance_evaluations"].values())
        }

        return report

# Compliance validation rules
COMPLIANCE_RULES = {
    "data_access": {
        "required_fields": ["user_id", "resource", "timestamp", "success"],
        "retention_days": 2555,  # 7 years for SOX compliance
        "encryption_required": True
    },
    "authentication": {
        "required_fields": ["user_id", "ip_address", "timestamp", "success", "method"],
        "retention_days": 2555,
        "mfa_required": True
    },
    "data_modification": {
        "required_fields": ["user_id", "resource", "timestamp", "old_value", "new_value"],
        "retention_days": 2555,
        "approval_required": True
    },
    "system_configuration": {
        "required_fields": ["user_id", "resource", "timestamp", "configuration_change"],
        "retention_days": 2555,
        "change_approval": True
    },
    "security_event": {
        "required_fields": ["timestamp", "event_type", "severity", "source_ip", "affected_resource"],
        "retention_days": 3650,  # 10 years for security events
        "immediate_alert": True
    }
}

def validate_audit_event(event: Dict, event_type: str) -> Dict:
    """Validate audit event against compliance rules"""

    if event_type not in COMPLIANCE_RULES:
        return {"valid": False, "error": f"Unknown event type: {event_type}"}

    rules = COMPLIANCE_RULES[event_type]
    validation_result = {"valid": True, "warnings": [], "errors": []}

    # Check required fields
    for field in rules["required_fields"]:
        if field not in event:
            validation_result["errors"].append(f"Missing required field: {field}")
            validation_result["valid"] = False

    # Check data quality
    if "timestamp" in event:
        try:
            datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
        except ValueError:
            validation_result["errors"].append("Invalid timestamp format")
            validation_result["valid"] = False

    if "user_id" in event and not event["user_id"]:
        validation_result["warnings"].append("Empty user_id field")

    return validation_result
