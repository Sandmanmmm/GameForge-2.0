#!/usr/bin/env python3
"""
GameForge AI Production Readiness Validation
Final comprehensive audit against enterprise production checklist
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "production_validation", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class ProductionValidator:
    """Comprehensive production readiness validation"""
    
    def __init__(self):
        self.validation_results = {
            'security': {},
            'observability': {},
            'data_management': {},
            'cicd': {},
            'performance': {},
            'networking': {},
            'operations': {},
            'compliance': {}
        }
        self.overall_score = 0
    
    def check_security_implementation(self) -> Dict[str, bool]:
        """Validate security implementation"""
        checks = {
            'vault_secrets': self._check_file_exists('docker-compose.vault-secrets.yml'),
            'seccomp_profiles': self._check_file_exists('seccomp-profile.json'),
            'auth_middleware': self._check_file_exists('auth_middleware.py'),
            'ssl_certificates': self._check_env_var('SSL_CERT_PATH'),
            'network_isolation': self._check_docker_compose_networks(),
            'runtime_security': self._check_file_exists('configure-security.ps1'),
            'secrets_rotation': self._check_file_exists('deploy-secret-rotation-production.ps1'),
            'security_scanning': self._check_file_exists('.github/workflows/security-scan.yml')
        }
        
        self.validation_results['security'] = checks
        return checks
    
    def check_observability_implementation(self) -> Dict[str, bool]:
        """Validate observability implementation"""
        checks = {
            'json_logging': self._check_file_exists('docker-compose.json-logging.yml'),
            'prometheus_metrics': self._check_file_exists('prometheus/prometheus.yml'),
            'grafana_dashboards': self._check_file_exists('grafana/dashboards/gameforge-dashboard.json'),
            'elasticsearch_integration': self._check_file_exists('docker-compose.elasticsearch.yml'),
            'filebeat_logs': self._check_file_exists('filebeat/filebeat.yml'),
            'correlation_ids': self._check_code_pattern('correlation_id'),
            'health_endpoints': self._check_code_pattern('/health'),
            'metrics_endpoints': self._check_code_pattern('/metrics'),
            'automated_dashboards': self._check_file_exists('grafana/provisioning/dashboards/default.yml'),
            'alerting_rules': self._check_file_exists('prometheus/alerts.yml')
        }
        
        self.validation_results['observability'] = checks
        return checks
    
    def check_data_management_implementation(self) -> Dict[str, bool]:
        """Validate data management implementation"""
        checks = {
            'model_externalization': self._check_file_exists('scripts/download-models.py'),
            'runtime_downloads': self._check_code_pattern('async def download_model'),
            'database_migrations': self._check_file_exists('scripts/migrate-database.py'),
            'external_storage': self._check_file_exists('scripts/external-storage.py'),
            'storage_backends': self._check_code_pattern('ExternalStorageManager'),
            'volume_persistence': self._check_file_exists('external-storage-config.yaml'),
            'data_encryption': self._check_code_pattern('encryption'),
            'backup_automation': self._check_file_exists('backup-production.ps1')
        }
        
        self.validation_results['data_management'] = checks
        return checks
    
    def check_cicd_implementation(self) -> Dict[str, bool]:
        """Validate CI/CD implementation"""
        checks = {
            'github_actions': self._check_file_exists('.github/workflows/deploy.yml'),
            'security_scanning': self._check_file_exists('.github/workflows/security-scan.yml'),
            'image_signing': self._check_code_pattern('cosign'),
            'sbom_generation': self._check_code_pattern('syft'),
            'vulnerability_scanning': self._check_code_pattern('trivy'),
            'deployment_automation': self._check_file_exists('deploy-production-complete.ps1'),
            'rollback_strategy': self._check_code_pattern('rollback'),
            'environment_promotion': self._check_file_exists('deploy-phase4-production.ps1')
        }
        
        self.validation_results['cicd'] = checks
        return checks
    
    def check_performance_implementation(self) -> Dict[str, bool]:
        """Validate performance implementation"""
        checks = {
            'gpu_optimization': self._check_file_exists('deploy-gpu-workloads.ps1'),
            'model_caching': self._check_code_pattern('model_cache'),
            'async_processing': self._check_code_pattern('async def'),
            'resource_limits': self._check_docker_compose_resources(),
            'auto_scaling': self._check_code_pattern('scaling'),
            'load_balancing': self._check_docker_compose_pattern('deploy:'),
            'performance_monitoring': self._check_file_exists('grafana/dashboards/performance-dashboard.json'),
            'optimization_metrics': self._check_code_pattern('processing_time')
        }
        
        self.validation_results['performance'] = checks
        return checks
    
    def check_networking_implementation(self) -> Dict[str, bool]:
        """Validate networking implementation"""
        checks = {
            'service_mesh': self._check_docker_compose_networks(),
            'ssl_termination': self._check_file_exists('nginx/ssl.conf'),
            'rate_limiting': self._check_code_pattern('rate_limit'),
            'firewall_rules': self._check_file_exists('configure-security.ps1'),
            'dns_configuration': self._check_code_pattern('dns'),
            'network_policies': self._check_file_exists('k8s-network-policies.yaml'),
            'ingress_control': self._check_file_exists('nginx/nginx.conf'),
            'network_monitoring': self._check_code_pattern('network_metrics')
        }
        
        self.validation_results['networking'] = checks
        return checks
    
    def check_operations_implementation(self) -> Dict[str, bool]:
        """Validate operations implementation"""
        checks = {
            'container_orchestration': self._check_file_exists('docker-compose.production.yml'),
            'health_checks': self._check_docker_compose_healthchecks(),
            'graceful_shutdown': self._check_code_pattern('SIGTERM'),
            'backup_recovery': self._check_file_exists('backup-production.ps1'),
            'disaster_recovery': self._check_file_exists('DEPLOYMENT_GUIDE.md'),
            'monitoring_alerts': self._check_file_exists('prometheus/alerts.yml'),
            'log_aggregation': self._check_file_exists('docker-compose.elasticsearch.yml'),
            'maintenance_mode': self._check_code_pattern('maintenance')
        }
        
        self.validation_results['operations'] = checks
        return checks
    
    def check_compliance_implementation(self) -> Dict[str, bool]:
        """Validate compliance implementation"""
        checks = {
            'audit_logging': self._check_file_exists('audit-policy.yaml'),
            'data_privacy': self._check_code_pattern('gdpr'),
            'security_policies': self._check_file_exists('seccomp-profile.json'),
            'documentation': self._check_file_exists('DEPLOYMENT_GUIDE.md'),
            'change_management': self._check_file_exists('.github/workflows/deploy.yml'),
            'access_control': self._check_file_exists('auth_middleware.py'),
            'data_retention': self._check_code_pattern('retention'),
            'compliance_reporting': self._check_code_pattern('audit_log')
        }
        
        self.validation_results['compliance'] = checks
        return checks
    
    def _check_file_exists(self, file_path: str) -> bool:
        """Check if a file exists"""
        return Path(file_path).exists()
    
    def _check_env_var(self, var_name: str) -> bool:
        """Check if environment variable is set"""
        return os.getenv(var_name) is not None
    
    def _check_code_pattern(self, pattern: str) -> bool:
        """Check if a code pattern exists in the project"""
        # Simple implementation - check if pattern exists in any Python file
        for py_file in Path('.').rglob('*.py'):
            try:
                content = py_file.read_text(encoding='utf-8')
                if pattern in content:
                    return True
            except Exception:
                continue
        
        # Also check in YAML and configuration files
        for config_file in list(Path('.').rglob('*.yml')) + list(Path('.').rglob('*.yaml')):
            try:
                content = config_file.read_text(encoding='utf-8')
                if pattern in content:
                    return True
            except Exception:
                continue
        
        return False
    
    def _check_docker_compose_networks(self) -> bool:
        """Check if Docker Compose has network configuration"""
        compose_files = list(Path('.').glob('docker-compose*.yml'))
        for compose_file in compose_files:
            try:
                content = compose_file.read_text()
                if 'networks:' in content:
                    return True
            except Exception:
                continue
        return False
    
    def _check_docker_compose_resources(self) -> bool:
        """Check if Docker Compose has resource limits"""
        compose_files = list(Path('.').glob('docker-compose*.yml'))
        for compose_file in compose_files:
            try:
                content = compose_file.read_text()
                if 'resources:' in content or 'mem_limit:' in content:
                    return True
            except Exception:
                continue
        return False
    
    def _check_docker_compose_pattern(self, pattern: str) -> bool:
        """Check if Docker Compose files contain a pattern"""
        compose_files = list(Path('.').glob('docker-compose*.yml'))
        for compose_file in compose_files:
            try:
                content = compose_file.read_text()
                if pattern in content:
                    return True
            except Exception:
                continue
        return False
    
    def _check_docker_compose_healthchecks(self) -> bool:
        """Check if Docker Compose has health checks"""
        compose_files = list(Path('.').glob('docker-compose*.yml'))
        for compose_file in compose_files:
            try:
                content = compose_file.read_text()
                if 'healthcheck:' in content:
                    return True
            except Exception:
                continue
        return False
    
    def calculate_scores(self) -> Dict[str, float]:
        """Calculate scores for each category"""
        scores = {}
        
        for category, checks in self.validation_results.items():
            if checks:
                passed = sum(1 for result in checks.values() if result)
                total = len(checks)
                scores[category] = (passed / total) * 100
            else:
                scores[category] = 0
        
        return scores
    
    async def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run complete production readiness validation"""
        logger.info("🚀 Starting comprehensive production readiness validation...")
        
        # Run all validation checks
        validation_functions = [
            ('Security', self.check_security_implementation),
            ('Observability', self.check_observability_implementation),
            ('Data Management', self.check_data_management_implementation),
            ('CI/CD', self.check_cicd_implementation),
            ('Performance', self.check_performance_implementation),
            ('Networking', self.check_networking_implementation),
            ('Operations', self.check_operations_implementation),
            ('Compliance', self.check_compliance_implementation)
        ]
        
        for category_name, validation_func in validation_functions:
            logger.info(f"🔍 Validating {category_name}...")
            validation_func()
        
        # Calculate scores
        scores = self.calculate_scores()
        overall_score = sum(scores.values()) / len(scores) if scores else 0
        self.overall_score = overall_score
        
        # Generate detailed report
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_score': overall_score,
            'category_scores': scores,
            'detailed_results': self.validation_results,
            'summary': self._generate_summary(scores, overall_score),
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_summary(self, scores: Dict[str, float], overall_score: float) -> Dict[str, Any]:
        """Generate validation summary"""
        return {
            'production_ready': overall_score >= 95.0,
            'readiness_level': self._get_readiness_level(overall_score),
            'top_categories': sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3],
            'needs_improvement': [cat for cat, score in scores.items() if score < 90.0],
            'critical_gaps': self._identify_critical_gaps()
        }
    
    def _get_readiness_level(self, score: float) -> str:
        """Get readiness level description"""
        if score >= 98:
            return "ENTERPRISE_READY"
        elif score >= 95:
            return "PRODUCTION_READY"
        elif score >= 90:
            return "NEAR_PRODUCTION"
        elif score >= 80:
            return "DEVELOPMENT_COMPLETE"
        elif score >= 70:
            return "BETA_READY"
        else:
            return "DEVELOPMENT_PHASE"
    
    def _identify_critical_gaps(self) -> List[str]:
        """Identify critical gaps that must be addressed"""
        critical_gaps = []
        
        # Check for critical security issues
        security_results = self.validation_results.get('security', {})
        if not security_results.get('vault_secrets', False):
            critical_gaps.append("Missing Vault secrets management")
        if not security_results.get('ssl_certificates', False):
            critical_gaps.append("Missing SSL certificate configuration")
        
        # Check for critical observability issues
        observability_results = self.validation_results.get('observability', {})
        if not observability_results.get('json_logging', False):
            critical_gaps.append("Missing JSON structured logging")
        if not observability_results.get('prometheus_metrics', False):
            critical_gaps.append("Missing Prometheus metrics collection")
        
        # Check for critical data management issues
        data_results = self.validation_results.get('data_management', {})
        if not data_results.get('model_externalization', False):
            critical_gaps.append("Missing model externalization")
        if not data_results.get('database_migrations', False):
            critical_gaps.append("Missing database migration automation")
        
        return critical_gaps
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for improvement"""
        recommendations = []
        
        scores = self.calculate_scores()
        
        for category, score in scores.items():
            if score < 90:
                recommendations.append(f"Improve {category} implementation (current: {score:.1f}%)")
        
        # Add specific recommendations based on critical gaps
        critical_gaps = self._identify_critical_gaps()
        for gap in critical_gaps:
            recommendations.append(f"CRITICAL: Address {gap}")
        
        return recommendations
    
    def generate_report_file(self, report: Dict[str, Any]):
        """Generate detailed validation report file"""
        report_dir = Path('reports')
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = report_dir / f'production_validation_{timestamp}.json'
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📊 Detailed report saved: {report_file}")
        
        # Also generate human-readable summary
        summary_file = report_dir / f'production_summary_{timestamp}.md'
        self._generate_markdown_summary(report, summary_file)
        
        logger.info(f"📄 Summary report saved: {summary_file}")
    
    def _generate_markdown_summary(self, report: Dict[str, Any], output_file: Path):
        """Generate human-readable markdown summary"""
        content = f"""# GameForge AI Production Readiness Report

**Generated:** {report['timestamp']}
**Overall Score:** {report['overall_score']:.1f}%
**Readiness Level:** {report['summary']['readiness_level']}
**Production Ready:** {'✅ YES' if report['summary']['production_ready'] else '❌ NO'}

## Category Scores

"""
        
        for category, score in report['category_scores'].items():
            status = "✅" if score >= 90 else "⚠️" if score >= 80 else "❌"
            content += f"- {status} **{category.title()}:** {score:.1f}%\n"
        
        content += "\n## Critical Gaps\n\n"
        if report['summary']['critical_gaps']:
            for gap in report['summary']['critical_gaps']:
                content += f"- ❌ {gap}\n"
        else:
            content += "✅ No critical gaps identified\n"
        
        content += "\n## Recommendations\n\n"
        for rec in report['recommendations']:
            content += f"- {rec}\n"
        
        content += "\n## Detailed Results\n\n"
        for category, checks in report['detailed_results'].items():
            content += f"### {category.title()}\n\n"
            for check, passed in checks.items():
                status = "✅" if passed else "❌"
                content += f"- {status} {check.replace('_', ' ').title()}\n"
            content += "\n"
        
        output_file.write_text(content)

async def main():
    """Main validation function"""
    validator = ProductionValidator()
    
    try:
        # Run comprehensive validation
        report = await validator.run_comprehensive_validation()
        
        # Display results
        logger.info("=" * 60)
        logger.info("🎯 PRODUCTION READINESS VALIDATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"📊 Overall Score: {report['overall_score']:.1f}%")
        logger.info(f"🎖️  Readiness Level: {report['summary']['readiness_level']}")
        logger.info(f"🚀 Production Ready: {'YES' if report['summary']['production_ready'] else 'NO'}")
        
        logger.info("\n📈 Category Scores:")
        for category, score in report['category_scores'].items():
            status = "✅" if score >= 90 else "⚠️" if score >= 80 else "❌"
            logger.info(f"  {status} {category.title()}: {score:.1f}%")
        
        if report['summary']['critical_gaps']:
            logger.info("\n🚨 Critical Gaps:")
            for gap in report['summary']['critical_gaps']:
                logger.info(f"  ❌ {gap}")
        
        # Generate detailed report
        validator.generate_report_file(report)
        
        # Exit with appropriate code
        sys.exit(0 if report['summary']['production_ready'] else 1)
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())