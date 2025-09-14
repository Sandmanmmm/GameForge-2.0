"""
Simplified Migration Security Analyzer
Analyzes SQL migration files for security issues without database dependencies
"""

import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class MigrationFile:
    """Represents a migration file."""
    path: Path
    version: str
    description: str
    checksum: str
    sql_content: str
    is_safe: bool = True
    security_issues: List[str] = None


class SimpleMigrationAnalyzer:
    """Analyzes migration files for security issues."""
    
    def __init__(self):
        self.dangerous_patterns = [
            # Dynamic SQL construction patterns
            r'.*\{.*\}.*',  # String interpolation
            r'.*%s.*',      # String formatting
            r'.*\+.*user.*\+.*',  # String concatenation with user data
            r'EXECUTE\s+.*\{',  # Dynamic execute
            
            # Potentially dangerous operations without WHERE clauses
            r'DELETE\s+FROM\s+\w+\s*;',  # DELETE without WHERE
            r'UPDATE\s+\w+\s+SET.*\s*;',  # UPDATE without WHERE (simplified)
            
            # Dangerous SQL operations (review needed)
            r'DROP\s+(?:TABLE|DATABASE|SCHEMA)\s+(?!IF\s+EXISTS)',
            r'TRUNCATE\s+TABLE',
            r'GRANT\s+ALL',  # Overly broad permissions
        ]
        
        self.safe_patterns = [
            # Comments
            r'^\s*--',
            r'^\s*/\*',
            
            # Static DDL operations
            r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS',
            r'CREATE\s+INDEX',
            r'ALTER\s+TABLE',
            
            # Safe DML with proper conditions
            r'INSERT\s+INTO.*VALUES',
            r'DELETE.*WHERE',
            r'UPDATE.*WHERE',
        ]
    
    def analyze_sql_content(self, content: str) -> tuple[bool, List[str]]:
        """Analyze SQL content for security issues."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('--') or line.startswith('/*'):
                continue
            
            # Check for dangerous patterns
            for pattern in self.dangerous_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(f"Line {i}: {pattern} - {line[:60]}...")
        
        is_safe = len(issues) == 0
        return is_safe, issues
    
    def analyze_migration_file(self, file_path: Path) -> MigrationFile:
        """Analyze a single migration file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract version from filename (001_initial_schema.sql)
            filename = file_path.name
            version_match = re.search(r'(\d+)', filename)
            version = version_match.group(1) if version_match else '0'
            
            # Extract description
            description_parts = filename.replace('.sql', '').split('_')[1:]
            description = ' '.join(description_parts) if description_parts else filename
            
            # Calculate checksum
            checksum = hashlib.md5(content.encode()).hexdigest()
            
            # Analyze security
            is_safe, issues = self.analyze_sql_content(content)
            
            return MigrationFile(
                path=file_path,
                version=version,
                description=description,
                checksum=checksum,
                sql_content=content,
                is_safe=is_safe,
                security_issues=issues or []
            )
        except Exception as e:
            return MigrationFile(
                path=file_path,
                version='error',
                description=f'Error reading file: {e}',
                checksum='',
                sql_content='',
                is_safe=False,
                security_issues=[f'File read error: {e}']
            )
    
    def scan_migrations_directory(self, migrations_dir: Path) -> List[MigrationFile]:
        """Scan all migration files in directory."""
        migration_files = []
        
        if not migrations_dir.exists():
            print(f"Migration directory not found: {migrations_dir}")
            return migration_files
        
        # Recursively find SQL files
        for sql_file in migrations_dir.rglob("*.sql"):
            migration = self.analyze_migration_file(sql_file)
            migration_files.append(migration)
        
        # Sort by version
        migration_files.sort(
            key=lambda x: int(x.version) if x.version.isdigit() else 0
        )
        return migration_files
    
    def generate_migration_report(self, migrations: List[MigrationFile]) -> Dict[str, Any]:
        """Generate comprehensive migration analysis report."""
        if not migrations:
            return {
                'total_migrations': 0,
                'safe_migrations': 0,
                'unsafe_migrations': 0,
                'security_score': 10.0,
                'security_issues': [],
                'recommendations': ['No migration files found']
            }
        
        total_migrations = len(migrations)
        safe_migrations = sum(1 for m in migrations if m.is_safe)
        unsafe_migrations = total_migrations - safe_migrations
        
        security_issues = []
        for migration in migrations:
            if migration.security_issues:
                security_issues.extend([
                    f"{migration.path.name}: {issue}" 
                    for issue in migration.security_issues
                ])
        
        # Calculate security score
        security_score = (safe_migrations / total_migrations * 10.0) if total_migrations > 0 else 10.0
        
        return {
            'total_migrations': total_migrations,
            'safe_migrations': safe_migrations,
            'unsafe_migrations': unsafe_migrations,
            'security_score': security_score,
            'security_issues': security_issues,
            'recommendations': self._generate_recommendations(migrations)
        }
    
    def _generate_recommendations(self, migrations: List[MigrationFile]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        unsafe_count = sum(1 for m in migrations if not m.is_safe)
        
        if unsafe_count == 0:
            recommendations.extend([
                "✅ All migrations are secure",
                "✅ Safe to transition to Alembic",
                "• Use setup_alembic.py to configure Alembic",
                "• Test migrations in development environment",
                "• Consider adding migration rollback procedures"
            ])
        else:
            recommendations.extend([
                f"⚠️ {unsafe_count} migrations have security issues",
                "• Review and fix unsafe migrations before transition",
                "• Remove dynamic SQL construction",
                "• Add proper WHERE clauses to DELETE/UPDATE statements",
                "• Use parameterized queries for any dynamic content"
            ])
        
        return recommendations


def main():
    """Run migration security analysis."""
    print("🔍 Migration Security Analyzer for GameForge")
    print("=" * 50)
    
    analyzer = SimpleMigrationAnalyzer()
    
    # Look for migrations in multiple possible locations
    possible_dirs = [
        Path("scripts/migrations"),
        Path("migrations"),
        Path("sql/migrations"),
        Path("archive/legacy-services/migrations"),
        Path("ml-platform/sql"),
        Path(".")  # Current directory for any SQL files
    ]
    
    all_migrations = []
    
    for migrations_dir in possible_dirs:
        if migrations_dir.exists():
            print(f"📂 Scanning: {migrations_dir}")
            migrations = analyzer.scan_migrations_directory(migrations_dir)
            all_migrations.extend(migrations)
    
    # Generate report
    report = analyzer.generate_migration_report(all_migrations)
    
    print(f"\n📊 MIGRATION SECURITY ANALYSIS")
    print(f"Total Migrations Found: {report['total_migrations']}")
    print(f"Safe Migrations: {report['safe_migrations']}")
    print(f"Unsafe Migrations: {report['unsafe_migrations']}")
    print(f"Security Score: {report['security_score']:.1f}/10.0")
    
    if report['unsafe_migrations'] > 0:
        print(f"\n⚠️ Security Issues Found:")
        for issue in report['security_issues'][:10]:  # Show first 10
            print(f"   • {issue}")
        
        if len(report['security_issues']) > 10:
            print(f"   ... and {len(report['security_issues']) - 10} more issues")
    
    print(f"\n🔍 Migration Files Found:")
    for migration in all_migrations:
        status = "✅ SAFE" if migration.is_safe else "⚠️ UNSAFE"
        print(f"   {migration.path.name}: v{migration.version} - {status}")
        if not migration.is_safe and migration.security_issues:
            for issue in migration.security_issues[:2]:  # Show first 2 issues
                print(f"      └─ {issue}")
    
    print(f"\n💡 Recommendations:")
    for rec in report['recommendations']:
        print(f"   {rec}")
    
    # Overall status
    if report['unsafe_migrations'] == 0:
        status = "SECURE"
        emoji = "✅"
    elif report['security_score'] >= 7.0:
        status = "MOSTLY_SECURE"
        emoji = "⚠️"
    else:
        status = "NEEDS_REVIEW"
        emoji = "🚨"
    
    print(f"\n{emoji} Migration Security Status: {status}")
    
    return report


if __name__ == "__main__":
    main()