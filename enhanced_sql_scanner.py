"""
Enhanced SQL Injection Scanner for GameForge
More accurate detection with reduced false positives
"""

import re
import ast
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class SQLInjectionFinding:
    """Represents a potential SQL injection vulnerability."""
    file_path: str
    line_number: int
    severity: str
    category: str
    description: str
    code_snippet: str
    recommendation: str


class EnhancedSQLScanner:
    """Enhanced SQL injection scanner with reduced false positives."""
    
    def __init__(self):
        # Actual dangerous patterns - only real SQL injection risks
        self.dangerous_patterns = [
            # Direct string concatenation with SQL keywords in execute calls
            r'\.execute\s*\(\s*["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*["\'].*\+',
            r'\.execute\s*\(\s*.*\+.*["\'].*(?:SELECT|INSERT|UPDATE|DELETE)',
            
            # F-string SQL injection in execute calls
            r'\.execute\s*\(\s*f["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*\{',
            
            # String format SQL injection in execute calls
            r'\.execute\s*\(\s*["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*%[sd]',
            r'\.execute\s*\(\s*["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*\.format\(',
            
            # SQL variable concatenation
            r'(?:sql|query)\s*=.*["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*["\'].*\+',
            r'(?:sql|query)\s*=.*f["\'].*(?:SELECT|INSERT|UPDATE|DELETE).*\{',
        ]
        
        # Patterns that should be ignored (safe practices)
        self.safe_patterns = [
            # Comments and docstrings
            r'^\s*#',
            r'^\s*"""',
            r'^\s*\'\'\'',
            
            # Regex patterns themselves (like in this file)
            r'r["\'].*["\']',
            
            # Logging statements
            r'log(?:ger)?\.(?:debug|info|warning|error|critical)',
            r'print\s*\(',
            
            # Route decorators
            r'@\w+\.\w+\(',
            
            # Template strings (Alembic)
            r'%\([^)]+\)s',
            
            # Dictionary updates (not SQL)
            r'\.update\s*\(',
            
            # Parameterized queries (safe)
            r'\.execute\s*\([^,)]*,\s*[\(\[]',  # Parameters passed
            r'\.execute\s*\(\s*["\'][^"\']*\$\d+',  # PostgreSQL parameters
        ]
    
    def is_safe_line(self, line: str) -> bool:
        """Check if a line is safe and should be ignored."""
        line_stripped = line.strip()
        
        # Empty lines and comments
        if not line_stripped or line_stripped.startswith('#'):
            return True
        
        # Check against safe patterns
        for pattern in self.safe_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        
        return False
    
    def scan_file(self, file_path: Path) -> List[SQLInjectionFinding]:
        """Scan a single Python file for SQL injection vulnerabilities."""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                # Skip safe lines
                if self.is_safe_line(line):
                    continue
                
                # Check for dangerous patterns
                for pattern in self.dangerous_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append(SQLInjectionFinding(
                            file_path=str(file_path),
                            line_number=line_num,
                            severity='HIGH',
                            category='SQL Injection Risk',
                            description='Potential SQL injection vulnerability detected',
                            code_snippet=line.strip(),
                            recommendation='Use parameterized queries with $1, $2, etc.'
                        ))
                        break  # One finding per line
                        
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
        
        return findings
    
    def scan_directory(self, directory: Path) -> List[SQLInjectionFinding]:
        """Scan all Python files in directory."""
        all_findings = []
        
        for py_file in directory.rglob("*.py"):
            # Skip certain directories
            skip_dirs = ['__pycache__', '.git', 'venv', 'env', 'node_modules', 'archive']
            if any(skip in str(py_file) for skip in skip_dirs):
                continue
            
            findings = self.scan_file(py_file)
            all_findings.extend(findings)
        
        return all_findings
    
    def generate_report(self, findings: List[SQLInjectionFinding]) -> Dict[str, Any]:
        """Generate security report."""
        if not findings:
            return {
                'status': 'SECURE',
                'total_vulnerabilities': 0,
                'severity_breakdown': {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
                'score': 10.0,
                'recommendations': ['✅ No SQL injection vulnerabilities detected']
            }
        
        severity_count = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        files_affected = set()
        
        for finding in findings:
            severity_count[finding.severity] += 1
            files_affected.add(finding.file_path)
        
        # Calculate score
        score = 10.0 - (severity_count['HIGH'] * 3.0)
        score = max(0.0, score)
        
        status = 'CRITICAL' if score < 3 else 'VULNERABLE' if score < 7 else 'SECURE'
        
        return {
            'status': status,
            'total_vulnerabilities': len(findings),
            'severity_breakdown': severity_count,
            'score': round(score, 1),
            'files_affected': list(files_affected),
            'findings': findings,
            'recommendations': self._get_recommendations(findings)
        }
    
    def _get_recommendations(self, findings: List[SQLInjectionFinding]) -> List[str]:
        """Generate recommendations."""
        if not findings:
            return ['✅ No SQL injection vulnerabilities detected']
        
        high_count = sum(1 for f in findings if f.severity == 'HIGH')
        
        return [
            f"🚨 Fix {high_count} SQL injection vulnerabilities",
            "• Use asyncpg parameterized queries: cursor.execute(sql, (param1, param2))",
            "• Replace string concatenation with $1, $2 placeholders",
            "• Validate and sanitize all user inputs"
        ]


def main():
    """Run enhanced SQL injection scan."""
    print("🔍 Enhanced SQL Injection Scanner for GameForge")
    print("=" * 50)
    
    scanner = EnhancedSQLScanner()
    workspace_path = Path(".")
    
    print(f"📂 Scanning: {workspace_path.absolute()}")
    
    findings = scanner.scan_directory(workspace_path)
    report = scanner.generate_report(findings)
    
    print(f"\n📊 SCAN RESULTS")
    print(f"Status: {report['status']}")
    print(f"Security Score: {report['score']}/10.0")
    print(f"Vulnerabilities: {report['total_vulnerabilities']}")
    
    if report['total_vulnerabilities'] > 0:
        print(f"\n🔍 Found Issues:")
        for finding in findings:
            print(f"\n📍 {finding.file_path}:{finding.line_number}")
            print(f"   {finding.description}")
            print(f"   Code: {finding.code_snippet}")
            print(f"   Fix: {finding.recommendation}")
    
    print(f"\n💡 Recommendations:")
    for rec in report['recommendations']:
        print(f"   {rec}")
    
    status_emoji = "✅" if report['status'] == 'SECURE' else "🚨"
    print(f"\n{status_emoji} GameForge SQL Security: {report['status']}")


if __name__ == "__main__":
    main()