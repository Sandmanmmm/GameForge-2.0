"""
SQL Injection Detection and Prevention Tool for GameForge
Comprehensive scanning for SQL injection vulnerabilities
"""

import re
import ast
import os
from pathlib import Path
from typing import List, Dict, Set, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SQLInjectionFinding:
    """Represents a potential SQL injection vulnerability."""
    file_path: str
    line_number: int
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'
    category: str
    description: str
    code_snippet: str
    recommendation: str


class SQLInjectionScanner:
    """Advanced SQL injection vulnerability scanner."""
    
    def __init__(self):
        # High-risk patterns that indicate SQL injection vulnerabilities
        self.high_risk_patterns = [
            # String concatenation with SQL
            r'["\'](?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER).*?\+',
            r'\+.*?["\'](?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)',
            
            # F-string formatting with SQL
            r'f["\'].*?(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER).*?\{',
            
            # String formatting with SQL
            r'["\'](?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER).*?%[sd]',
            r'["\'](?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER).*?\.format\(',
            
            # Direct variable interpolation
            r'(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER).*?\{.*?\}',
            
            # Vulnerable cursor.execute patterns
            r'cursor\.execute\s*\(\s*["\'].*?\+',
            r'cursor\.execute\s*\(\s*f["\']',
            
            # Dynamic SQL construction
            r'sql\s*=.*?\+.*?["\'](?:SELECT|INSERT|UPDATE|DELETE)',
            r'query\s*=.*?\+.*?["\'](?:SELECT|INSERT|UPDATE|DELETE)',
        ]
        
        # Medium-risk patterns
        self.medium_risk_patterns = [
            # Potential unsafe SQL construction
            r'["\'](?:WHERE|ORDER BY|GROUP BY).*?\+',
            r'["\'](?:WHERE|ORDER BY|GROUP BY).*?%[sd]',
            r'["\'](?:WHERE|ORDER BY|GROUP BY).*?\.format\(',
            
            # LIKE clause vulnerabilities
            r'LIKE.*?\+',
            r'LIKE.*?%[sd]',
        ]
        
        # Safe patterns that should NOT be flagged
        self.safe_patterns = [
            # Parameterized queries
            r'cursor\.execute\s*\(\s*["\'][^"\']*\$\d+',  # PostgreSQL $1, $2 parameters
            r'cursor\.execute\s*\(\s*["\'][^"\']*\?\s*,',  # SQLite ? parameters
            r'\.execute\([^)]*,\s*\(',  # Parameters passed separately
            
            # SQL constants (no variables)
            r'^["\'](?:SELECT|INSERT|UPDATE|DELETE).*["\']$',
            
            # Logging and documentation
            r'log(?:ger)?\.(?:debug|info|warning|error)',
            r'print\s*\(',
            r'#.*SQL',
            r'""".*SQL.*"""',
        ]
        
        # SQL keywords to check for
        self.sql_keywords = {
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'MERGE', 'CALL', 'EXPLAIN', 'PLAN', 'GRANT', 'REVOKE'
        }
    
    def scan_file(self, file_path: Path) -> List[SQLInjectionFinding]:
        """Scan a single Python file for SQL injection vulnerabilities."""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Parse AST for more sophisticated analysis
            try:
                tree = ast.parse(content)
                ast_findings = self._analyze_ast(tree, file_path, lines)
                findings.extend(ast_findings)
            except SyntaxError:
                # If AST parsing fails, fall back to regex-only analysis
                pass
            
            # Regex-based analysis
            regex_findings = self._analyze_with_regex(lines, file_path)
            findings.extend(regex_findings)
            
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
        
        return findings
    
    def _analyze_ast(self, tree: ast.AST, file_path: Path, lines: List[str]) -> List[SQLInjectionFinding]:
        """Analyze AST for SQL injection patterns."""
        findings = []
        
        class SQLInjectionVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                # Check for execute() calls
                if (isinstance(node.func, ast.Attribute) and 
                    node.func.attr in ['execute', 'executemany']):
                    
                    if node.args:
                        sql_arg = node.args[0]
                        line_num = node.lineno
                        
                        # Check for string concatenation in SQL
                        if isinstance(sql_arg, ast.BinOp) and isinstance(sql_arg.op, ast.Add):
                            findings.append(SQLInjectionFinding(
                                file_path=str(file_path),
                                line_number=line_num,
                                severity='HIGH',
                                category='String Concatenation',
                                description='SQL query constructed using string concatenation',
                                code_snippet=lines[line_num - 1] if line_num <= len(lines) else '',
                                recommendation='Use parameterized queries with placeholders ($1, $2, etc.)'
                            ))
                        
                        # Check for f-string usage
                        elif isinstance(sql_arg, ast.JoinedStr):
                            findings.append(SQLInjectionFinding(
                                file_path=str(file_path),
                                line_number=line_num,
                                severity='HIGH',
                                category='F-string Interpolation',
                                description='SQL query constructed using f-string interpolation',
                                code_snippet=lines[line_num - 1] if line_num <= len(lines) else '',
                                recommendation='Use parameterized queries instead of f-strings'
                            ))
                        
                        # Check for .format() calls
                        elif (isinstance(sql_arg, ast.Call) and 
                              isinstance(sql_arg.func, ast.Attribute) and 
                              sql_arg.func.attr == 'format'):
                            findings.append(SQLInjectionFinding(
                                file_path=str(file_path),
                                line_number=line_num,
                                severity='HIGH',
                                category='String Formatting',
                                description='SQL query constructed using .format() method',
                                code_snippet=lines[line_num - 1] if line_num <= len(lines) else '',
                                recommendation='Use parameterized queries instead of string formatting'
                            ))
                
                self.generic_visit(node)
        
        visitor = SQLInjectionVisitor()
        visitor.visit(tree)
        
        return findings
    
    def _analyze_with_regex(self, lines: List[str], file_path: Path) -> List[SQLInjectionFinding]:
        """Analyze file content using regex patterns."""
        findings = []
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Skip comments and empty lines
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            # Check if line is safe (skip safe patterns)
            is_safe = any(re.search(pattern, line, re.IGNORECASE) for pattern in self.safe_patterns)
            if is_safe:
                continue
            
            # Check high-risk patterns
            for pattern in self.high_risk_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(SQLInjectionFinding(
                        file_path=str(file_path),
                        line_number=line_num,
                        severity='HIGH',
                        category='Regex Detection',
                        description='Potential SQL injection via string manipulation',
                        code_snippet=line.strip(),
                        recommendation='Use parameterized queries with proper escaping'
                    ))
                    break  # One finding per line
            
            # Check medium-risk patterns
            for pattern in self.medium_risk_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append(SQLInjectionFinding(
                        file_path=str(file_path),
                        line_number=line_num,
                        severity='MEDIUM',
                        category='Potential Risk',
                        description='Potentially unsafe SQL construction',
                        code_snippet=line.strip(),
                        recommendation='Review for proper input validation and parameterization'
                    ))
                    break  # One finding per line
        
        return findings
    
    def scan_directory(self, directory: Path) -> List[SQLInjectionFinding]:
        """Scan all Python files in a directory for SQL injection vulnerabilities."""
        all_findings = []
        
        for py_file in directory.rglob("*.py"):
            # Skip certain directories
            if any(skip in str(py_file) for skip in ['__pycache__', '.git', 'venv', 'env', 'node_modules']):
                continue
            
            findings = self.scan_file(py_file)
            all_findings.extend(findings)
        
        return all_findings
    
    def generate_report(self, findings: List[SQLInjectionFinding]) -> Dict[str, Any]:
        """Generate a comprehensive security report."""
        if not findings:
            return {
                'status': 'SECURE',
                'total_files_scanned': 0,
                'total_vulnerabilities': 0,
                'severity_breakdown': {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
                'recommendations': ['No SQL injection vulnerabilities detected'],
                'score': 10.0
            }
        
        # Count by severity
        severity_count = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        files_affected = set()
        
        for finding in findings:
            severity_count[finding.severity] += 1
            files_affected.add(finding.file_path)
        
        # Calculate security score (10 = perfect, 0 = critical)
        score = 10.0
        score -= severity_count['HIGH'] * 3.0  # -3 points per HIGH
        score -= severity_count['MEDIUM'] * 1.0  # -1 point per MEDIUM
        score -= severity_count['LOW'] * 0.5   # -0.5 points per LOW
        score = max(0.0, score)
        
        status = 'CRITICAL' if score < 3 else 'VULNERABLE' if score < 7 else 'NEEDS_REVIEW'
        
        return {
            'status': status,
            'total_files_scanned': len(files_affected),
            'total_vulnerabilities': len(findings),
            'severity_breakdown': severity_count,
            'score': round(score, 1),
            'files_affected': sorted(list(files_affected)),
            'findings': findings,
            'recommendations': self._generate_recommendations(findings)
        }
    
    def _generate_recommendations(self, findings: List[SQLInjectionFinding]) -> List[str]:
        """Generate security recommendations based on findings."""
        recommendations = []
        
        high_count = sum(1 for f in findings if f.severity == 'HIGH')
        medium_count = sum(1 for f in findings if f.severity == 'MEDIUM')
        
        if high_count > 0:
            recommendations.append(f"🚨 CRITICAL: Fix {high_count} high-severity SQL injection vulnerabilities immediately")
            recommendations.append("• Replace string concatenation with parameterized queries")
            recommendations.append("• Use asyncpg's parameter substitution ($1, $2, etc.)")
            recommendations.append("• Implement input validation and sanitization")
        
        if medium_count > 0:
            recommendations.append(f"⚠️ WARNING: Review {medium_count} medium-risk SQL constructions")
            recommendations.append("• Validate all user inputs before SQL operations")
            recommendations.append("• Use prepared statements where possible")
        
        if high_count == 0 and medium_count == 0:
            recommendations.append("✅ No SQL injection vulnerabilities detected")
            recommendations.append("• Continue using parameterized queries")
            recommendations.append("• Maintain secure coding practices")
        
        return recommendations


def main():
    """Run SQL injection security scan on GameForge."""
    print("🔍 SQL Injection Security Scanner for GameForge")
    print("=" * 50)
    
    # Initialize scanner
    scanner = SQLInjectionScanner()
    
    # Scan the workspace
    workspace_path = Path(".")
    print(f"📂 Scanning directory: {workspace_path.absolute()}")
    
    findings = scanner.scan_directory(workspace_path)
    report = scanner.generate_report(findings)
    
    # Display results
    print(f"\n📊 SECURITY SCAN RESULTS")
    print(f"Status: {report['status']}")
    print(f"Security Score: {report['score']}/10.0")
    print(f"Files Scanned: {len(list(workspace_path.rglob('*.py')))}")
    print(f"Vulnerabilities Found: {report['total_vulnerabilities']}")
    
    if report['total_vulnerabilities'] > 0:
        print(f"\n📋 Severity Breakdown:")
        for severity, count in report['severity_breakdown'].items():
            if count > 0:
                emoji = "🚨" if severity == "HIGH" else "⚠️" if severity == "MEDIUM" else "ℹ️"
                print(f"   {emoji} {severity}: {count}")
        
        print(f"\n🔍 Detailed Findings:")
        for finding in findings[:10]:  # Show first 10 findings
            print(f"\n📍 {finding.file_path}:{finding.line_number}")
            print(f"   Severity: {finding.severity}")
            print(f"   Category: {finding.category}")
            print(f"   Description: {finding.description}")
            print(f"   Code: {finding.code_snippet}")
            print(f"   Fix: {finding.recommendation}")
        
        if len(findings) > 10:
            print(f"\n... and {len(findings) - 10} more findings")
    
    print(f"\n💡 Recommendations:")
    for rec in report['recommendations']:
        print(f"   {rec}")
    
    # Status emoji
    if report['status'] == 'SECURE':
        print(f"\n✅ GameForge SQL Injection Security: SECURE")
    elif report['status'] == 'NEEDS_REVIEW':
        print(f"\n⚠️ GameForge SQL Injection Security: NEEDS REVIEW")
    elif report['status'] == 'VULNERABLE':
        print(f"\n🚨 GameForge SQL Injection Security: VULNERABLE")
    else:
        print(f"\n💀 GameForge SQL Injection Security: CRITICAL")


if __name__ == "__main__":
    main()