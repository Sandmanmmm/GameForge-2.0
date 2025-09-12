#!/usr/bin/env python3
"""
GameForge AI Network Security Audit Script
Validates network security configuration and identifies vulnerabilities
"""

import subprocess
import socket
import ssl
import requests
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkSecurityAuditor:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'vulnerabilities': [],
            'recommendations': []
        }
    
    def test_ssl_configuration(self):
        """Test SSL/TLS configuration"""
        logger.info("Testing SSL configuration...")
        
        try:
            context = ssl.create_default_context()
            with socket.create_connection(('localhost', 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname='localhost') as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    
                    self.results['tests']['ssl'] = {
                        'status': 'PASS',
                        'protocol': ssock.version(),
                        'cipher': cipher[0] if cipher else None,
                        'cert_subject': cert.get('subject', []),
                        'cert_expiry': cert.get('notAfter', 'Unknown')
                    }
                    
                    # Check for weak ciphers
                    if cipher and 'RC4' in cipher[0]:
                        self.results['vulnerabilities'].append({
                            'severity': 'HIGH',
                            'description': 'Weak cipher RC4 detected',
                            'recommendation': 'Disable RC4 ciphers in Nginx configuration'
                        })
        
        except Exception as e:
            self.results['tests']['ssl'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"SSL test failed: {e}")
    
    def test_security_headers(self):
        """Test HTTP security headers"""
        logger.info("Testing security headers...")
        
        try:
            response = requests.get('https://localhost/health', 
                                 verify=False, timeout=10)
            
            headers = response.headers
            required_headers = {
                'X-Frame-Options': 'DENY',
                'X-Content-Type-Options': 'nosniff',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000',
                'Content-Security-Policy': 'default-src'
            }
            
            missing_headers = []
            for header, expected in required_headers.items():
                if header not in headers:
                    missing_headers.append(header)
                elif expected not in headers[header]:
                    missing_headers.append(f"{header} (incorrect value)")
            
            self.results['tests']['security_headers'] = {
                'status': 'PASS' if not missing_headers else 'PARTIAL',
                'present_headers': list(headers.keys()),
                'missing_headers': missing_headers
            }
            
            if missing_headers:
                self.results['vulnerabilities'].append({
                    'severity': 'MEDIUM',
                    'description': f'Missing security headers: {missing_headers}',
                    'recommendation': 'Add missing security headers to Nginx configuration'
                })
        
        except Exception as e:
            self.results['tests']['security_headers'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"Security headers test failed: {e}")
    
    def test_rate_limiting(self):
        """Test rate limiting effectiveness"""
        logger.info("Testing rate limiting...")
        
        try:
            # Make rapid requests to test rate limiting
            responses = []
            for i in range(15):  # Should trigger rate limit
                try:
                    resp = requests.get('https://localhost/api/health', 
                                      verify=False, timeout=5)
                    responses.append(resp.status_code)
                except:
                    responses.append(0)
            
            rate_limited = any(code == 429 for code in responses)
            
            self.results['tests']['rate_limiting'] = {
                'status': 'PASS' if rate_limited else 'FAIL',
                'responses': responses,
                'rate_limit_triggered': rate_limited
            }
            
            if not rate_limited:
                self.results['vulnerabilities'].append({
                    'severity': 'MEDIUM',
                    'description': 'Rate limiting not working effectively',
                    'recommendation': 'Review and tune rate limiting configuration'
                })
        
        except Exception as e:
            self.results['tests']['rate_limiting'] = {
                'status': 'FAIL',
                'error': str(e)
            }
            logger.error(f"Rate limiting test failed: {e}")
    
    def test_internal_service_exposure(self):
        """Test that internal services are not exposed"""
        logger.info("Testing internal service exposure...")
        
        internal_ports = [5432, 6379, 9090, 3000, 9200]  # postgres, redis, prometheus, grafana, elasticsearch
        exposed_ports = []
        
        for port in internal_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    exposed_ports.append(port)
                sock.close()
            except:
                pass
        
        self.results['tests']['internal_exposure'] = {
            'status': 'PASS' if not exposed_ports else 'FAIL',
            'exposed_ports': exposed_ports
        }
        
        if exposed_ports:
            self.results['vulnerabilities'].append({
                'severity': 'HIGH',
                'description': f'Internal services exposed on ports: {exposed_ports}',
                'recommendation': 'Remove port mappings for internal services'
            })
    
    def generate_audit_report(self):
        """Generate comprehensive audit report"""
        report = []
        report.append("=" * 80)
        report.append("GAMEFORGE AI - NETWORK SECURITY AUDIT REPORT")
        report.append("=" * 80)
        report.append(f"Audit Date: {self.results['timestamp']}")
        report.append("")
        
        # Test results summary
        report.append("TEST RESULTS:")
        report.append("-" * 40)
        
        for test_name, test_result in self.results['tests'].items():
            status_icon = "✅" if test_result['status'] == 'PASS' else "⚠️" if test_result['status'] == 'PARTIAL' else "❌"
            report.append(f"{status_icon} {test_name.replace('_', ' ').title()}: {test_result['status']}")
        
        report.append("")
        
        # Vulnerabilities
        if self.results['vulnerabilities']:
            report.append("VULNERABILITIES FOUND:")
            report.append("-" * 25)
            
            for vuln in self.results['vulnerabilities']:
                severity_icon = "🔴" if vuln['severity'] == 'HIGH' else "🟡" if vuln['severity'] == 'MEDIUM' else "🟢"
                report.append(f"{severity_icon} {vuln['severity']}: {vuln['description']}")
                report.append(f"   Recommendation: {vuln['recommendation']}")
                report.append("")
        else:
            report.append("✅ NO CRITICAL VULNERABILITIES FOUND")
            report.append("")
        
        # Overall security score
        total_tests = len(self.results['tests'])
        passed_tests = sum(1 for test in self.results['tests'].values() if test['status'] == 'PASS')
        score = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report.append(f"OVERALL SECURITY SCORE: {score:.1f}%")
        report.append("")
        
        if score >= 90:
            report.append("🎉 EXCELLENT SECURITY POSTURE")
        elif score >= 75:
            report.append("✅ GOOD SECURITY POSTURE - Minor improvements needed")
        elif score >= 50:
            report.append("⚠️ MODERATE SECURITY POSTURE - Improvements required")
        else:
            report.append("❌ POOR SECURITY POSTURE - Immediate action required")
        
        return "\n".join(report)
    
    def run_audit(self):
        """Run complete security audit"""
        logger.info("Starting network security audit...")
        
        self.test_ssl_configuration()
        self.test_security_headers()
        self.test_rate_limiting()
        self.test_internal_service_exposure()
        
        # Generate and save report
        report = self.generate_audit_report()
        
        with open('network_security_audit.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        with open('network_security_audit_report.txt', 'w') as f:
            f.write(report)
        
        print(report)
        
        # Return exit code based on vulnerabilities
        high_severity = any(v['severity'] == 'HIGH' for v in self.results['vulnerabilities'])
        return 1 if high_severity else 0

if __name__ == "__main__":
    auditor = NetworkSecurityAuditor()
    exit_code = auditor.run_audit()
    exit(exit_code)
