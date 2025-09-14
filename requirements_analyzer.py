"""
Requirements.txt Security and Version Analysis
Analyzes package versions for security and reproducibility issues
"""

import re
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class PackageIssue:
    """Represents a package version issue."""
    package: str
    current_version: str
    issue_type: str
    description: str
    recommendation: str
    severity: str


class RequirementsAnalyzer:
    """Analyzes requirements.txt for version pinning and security issues."""
    
    def __init__(self):
        self.unpinned_patterns = [
            r'^([a-zA-Z0-9_-]+)>=(.+)$',  # Greater than or equal
            r'^([a-zA-Z0-9_-]+)>(.+)$',   # Greater than
            r'^([a-zA-Z0-9_-]+)~=(.+)$',  # Compatible release
            r'^([a-zA-Z0-9_-]+)\^(.+)$',  # Caret (poetry style)
        ]
        
        self.range_patterns = [
            r'^([a-zA-Z0-9_-]+)==(.+)\.x$',     # Version with .x
            r'^([a-zA-Z0-9_-]+)==(.+)\.\*$',    # Version with .*
            r'^([a-zA-Z0-9_-]+)>=(.+),<(.+)$', # Range specification
        ]
        
        # Known current stable versions (as of September 2025)
        self.recommended_versions = {
            'fastapi': '0.104.1',
            'uvicorn': '0.24.0', 
            'pydantic': '2.5.2',
            'starlette': '0.27.0',
            'sqlalchemy': '2.0.23',
            'alembic': '1.13.0',
            'asyncpg': '0.29.0',
            'redis': '5.0.1',
            'celery': '5.3.4',
            'requests': '2.31.0',
            'httpx': '0.25.2',
            'psycopg2-binary': '2.9.9',
            'boto3': '1.34.0',
            'torch': '2.1.1',
            'transformers': '4.36.2',
            'pillow': '10.1.0',
            'numpy': '1.24.4',
            'cryptography': '41.0.8',
            'pytest': '7.4.3',
            'black': '23.11.0',
            'mypy': '1.7.1'
        }
    
    def analyze_requirements_file(self, file_path: Path) -> List[PackageIssue]:
        """Analyze a requirements.txt file for version issues."""
        issues = []
        
        if not file_path.exists():
            return [PackageIssue(
                package="requirements.txt",
                current_version="N/A",
                issue_type="FILE_NOT_FOUND",
                description="Requirements file not found",
                recommendation="Create requirements.txt file",
                severity="HIGH"
            )]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#') or line.startswith('-'):
                    continue
                
                # Check for unpinned versions
                for pattern in self.unpinned_patterns:
                    match = re.match(pattern, line)
                    if match:
                        package = match.group(1)
                        version = match.group(2)
                        
                        recommended = self.recommended_versions.get(package.lower(), "latest")
                        
                        issues.append(PackageIssue(
                            package=package,
                            current_version=f">={version}",
                            issue_type="UNPINNED_VERSION",
                            description=f"Package uses unpinned version {version}",
                            recommendation=f"Pin to specific version: {package}=={recommended}",
                            severity="MEDIUM"
                        ))
                        break
                
                # Check for version ranges
                for pattern in self.range_patterns:
                    match = re.match(pattern, line)
                    if match:
                        package = match.group(1)
                        version = match.group(2)
                        
                        issues.append(PackageIssue(
                            package=package,
                            current_version=line,
                            issue_type="VERSION_RANGE",
                            description=f"Package uses version range instead of exact pin",
                            recommendation=f"Use exact version: {package}=={version}",
                            severity="LOW"
                        ))
                        break
                
                # Check for duplicate packages
                package_name = line.split('==')[0].split('>=')[0].split('>')[0].split('[')[0]
                # This would require tracking seen packages - simplified for now
        
        except Exception as e:
            issues.append(PackageIssue(
                package="requirements.txt",
                current_version="N/A", 
                issue_type="READ_ERROR",
                description=f"Error reading file: {e}",
                recommendation="Fix file permissions or encoding",
                severity="HIGH"
            ))
        
        return issues
    
    def generate_fixed_requirements(self, file_path: Path) -> str:
        """Generate a fixed version of requirements.txt with pinned versions."""
        if not file_path.exists():
            return "# requirements.txt not found"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            fixed_lines = []
            
            for line in lines:
                original_line = line
                line = line.strip()
                
                # Keep comments and empty lines
                if not line or line.startswith('#') or line.startswith('-'):
                    fixed_lines.append(original_line)
                    continue
                
                # Fix unpinned versions
                fixed = False
                for pattern in self.unpinned_patterns:
                    match = re.match(pattern, line)
                    if match:
                        package = match.group(1)
                        recommended = self.recommended_versions.get(package.lower())
                        
                        if recommended:
                            # Handle extras (like uvicorn[standard])
                            if '[' in package:
                                base_package = package.split('[')[0]
                                extras = '[' + package.split('[')[1]
                                fixed_line = f"{base_package}{extras}=={recommended}"
                            else:
                                fixed_line = f"{package}=={recommended}"
                            
                            fixed_lines.append(fixed_line)
                            fixed = True
                            break
                
                if not fixed:
                    fixed_lines.append(original_line)
            
            return '\n'.join(fixed_lines)
        
        except Exception as e:
            return f"# Error processing file: {e}"
    
    def generate_report(self, issues: List[PackageIssue]) -> Dict[str, Any]:
        """Generate analysis report."""
        severity_counts = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        issue_types = {}
        
        for issue in issues:
            severity_counts[issue.severity] += 1
            issue_types[issue.issue_type] = issue_types.get(issue.issue_type, 0) + 1
        
        total_issues = len(issues)
        score = max(0, 10 - (severity_counts['HIGH'] * 3) - 
                   (severity_counts['MEDIUM'] * 1) - (severity_counts['LOW'] * 0.5))
        
        if total_issues == 0:
            status = 'EXCELLENT'
        elif score >= 8:
            status = 'GOOD'
        elif score >= 6:
            status = 'ACCEPTABLE'
        else:
            status = 'NEEDS_IMPROVEMENT'
        
        return {
            'total_issues': total_issues,
            'severity_counts': severity_counts,
            'issue_types': issue_types,
            'score': round(score, 1),
            'status': status,
            'issues': issues
        }


def main():
    """Analyze requirements.txt file."""
    print("🔍 Requirements.txt Security Analysis")
    print("=" * 50)
    
    analyzer = RequirementsAnalyzer()
    requirements_file = Path("requirements.txt")
    
    print(f"📂 Analyzing: {requirements_file.absolute()}")
    
    issues = analyzer.analyze_requirements_file(requirements_file)
    report = analyzer.generate_report(issues)
    
    print(f"\n📊 ANALYSIS RESULTS")
    print(f"Total Issues Found: {report['total_issues']}")
    print(f"Security Score: {report['score']}/10.0")
    print(f"Status: {report['status']}")
    
    if report['severity_counts']['HIGH'] > 0:
        print(f"🚨 High Severity: {report['severity_counts']['HIGH']}")
    if report['severity_counts']['MEDIUM'] > 0:
        print(f"⚠️ Medium Severity: {report['severity_counts']['MEDIUM']}")
    if report['severity_counts']['LOW'] > 0:
        print(f"ℹ️ Low Severity: {report['severity_counts']['LOW']}")
    
    print(f"\n📋 Issue Types:")
    for issue_type, count in report['issue_types'].items():
        print(f"   • {issue_type}: {count}")
    
    if issues:
        print(f"\n🔍 Detailed Issues:")
        for issue in issues[:10]:  # Show first 10
            print(f"\n📦 {issue.package}")
            print(f"   Current: {issue.current_version}")
            print(f"   Issue: {issue.description}")
            print(f"   Fix: {issue.recommendation}")
            print(f"   Severity: {issue.severity}")
        
        if len(issues) > 10:
            print(f"\n... and {len(issues) - 10} more issues")
    
    print(f"\n💡 Recommendations:")
    if report['status'] == 'EXCELLENT':
        print("   ✅ Requirements are properly pinned")
    else:
        print("   📌 Pin all package versions to exact releases")
        print("   🔒 Replace >= with == for reproducible builds")
        print("   ⚡ Update to latest stable versions for security")
        print("   🧪 Test dependency updates in staging environment")
    
    # Generate fixed requirements
    if issues:
        print(f"\n🔧 Generating fixed requirements.txt...")
        fixed_content = analyzer.generate_fixed_requirements(requirements_file)
        
        # Save to a new file
        fixed_file = Path("requirements_fixed.txt")
        with open(fixed_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print(f"✅ Fixed requirements saved to: {fixed_file}")
        print(f"📝 Review the changes and replace original file if acceptable")
    
    status_emoji = {
        'EXCELLENT': '✅',
        'GOOD': '👍', 
        'ACCEPTABLE': '⚠️',
        'NEEDS_IMPROVEMENT': '🚨'
    }.get(report['status'], '❓')
    
    print(f"\n{status_emoji} Requirements Status: {report['status']}")


if __name__ == "__main__":
    main()