"""
Database Migration Security Analyzer and Alembic Transition Tool
Analyzes current migration system and helps transition to Alembic safely
"""

import os
import re
import asyncio
import asyncpg
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib
import json


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


class MigrationSecurityAnalyzer:
    """Analyzes migration files for security issues."""
    
    def __init__(self):
        self.dangerous_patterns = [
            # Direct user input in SQL
            r'.*\{.*\}.*',  # String interpolation
            r'.*%s.*',      # String formatting
            r'.*\+.*user.*\+.*',  # String concatenation with user data
            
            # Dangerous SQL operations without proper validation
            r'DROP\s+(?:TABLE|DATABASE|SCHEMA)',
            r'TRUNCATE\s+TABLE',
            r'DELETE\s+FROM.*WHERE.*=.*\{',
            
            # Dynamic SQL construction
            r'EXECUTE\s+.*\{',
            r'exec\s*\(',
        ]
        
        self.safe_patterns = [
            # Comments
            r'^\s*--',
            r'^\s*/\*',
            
            # Static SQL
            r'^[^{%+]*$',  # No interpolation
            
            # Alembic patterns
            r'op\.',
            r'sa\.',
        ]
    
    def analyze_sql_content(self, content: str) -> tuple[bool, List[str]]:
        """Analyze SQL content for security issues."""
        issues = []
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('--'):
                continue
            
            # Check for dangerous patterns
            for pattern in self.dangerous_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(f"Dangerous pattern: {pattern} in line: {line[:50]}...")
        
        is_safe = len(issues) == 0
        return is_safe, issues
    
    def analyze_migration_file(self, file_path: Path) -> MigrationFile:
        """Analyze a single migration file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract version from filename (assuming format: V001__description.sql)
            filename = file_path.name
            version_match = re.search(r'V?(\d+)', filename)
            version = version_match.group(1) if version_match else '0'
            
            # Extract description
            description_match = re.search(r'__(.+)\.sql$', filename)
            description = description_match.group(1).replace('_', ' ') if description_match else filename
            
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
                security_issues=issues
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
        
        for sql_file in migrations_dir.glob("*.sql"):
            migration = self.analyze_migration_file(sql_file)
            migration_files.append(migration)
        
        # Sort by version
        migration_files.sort(key=lambda x: int(x.version) if x.version.isdigit() else 0)
        return migration_files


class AlembicTransitionTool:
    """Tool to help transition from custom migrations to Alembic."""
    
    def __init__(self):
        self.analyzer = MigrationSecurityAnalyzer()
    
    async def get_applied_migrations(self, db_url: str) -> List[Dict[str, Any]]:
        """Get list of applied migrations from database."""
        try:
            conn = await asyncpg.connect(db_url)
            try:
                # Check if schema_migrations table exists
                exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'schema_migrations'
                    )
                """)
                
                if not exists:
                    return []
                
                # Get applied migrations
                rows = await conn.fetch("""
                    SELECT version, applied_at, checksum 
                    FROM schema_migrations 
                    ORDER BY version
                """)
                
                return [dict(row) for row in rows]
            finally:
                await conn.close()
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return []
    
    def generate_alembic_migration(self, migration: MigrationFile) -> str:
        """Generate Alembic migration from SQL file."""
        template = f'''"""Migration {migration.version}: {migration.description}

Revision ID: {migration.checksum[:12]}
Revises: 
Create Date: auto-generated

"""
from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Apply migration {migration.version}."""
    # Original SQL from {migration.path.name}
    op.execute("""
{migration.sql_content}
    """)


def downgrade() -> None:
    """Reverse migration {migration.version}."""
    # Add downgrade logic here
    pass
'''
        return template
    
    def create_alembic_versions(self, migrations: List[MigrationFile], output_dir: Path):
        """Create Alembic version files from migrations."""
        output_dir.mkdir(exist_ok=True)
        
        for i, migration in enumerate(migrations):
            if not migration.is_safe:
                print(f"⚠️ Skipping unsafe migration: {migration.path.name}")
                continue
            
            # Generate filename
            timestamp = f"2024010{i+1:02d}_000000"  # Simple timestamp
            filename = f"{timestamp}_{migration.checksum[:8]}_migration_{migration.version}.py"
            
            # Generate content
            alembic_content = self.generate_alembic_migration(migration)
            
            # Write file
            output_path = output_dir / filename
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(alembic_content)
            
            print(f"✅ Created: {filename}")
    
    def generate_migration_report(self, migrations: List[MigrationFile]) -> Dict[str, Any]:
        """Generate comprehensive migration analysis report."""
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
        
        return {
            'total_migrations': total_migrations,
            'safe_migrations': safe_migrations,
            'unsafe_migrations': unsafe_migrations,
            'security_score': (safe_migrations / total_migrations * 10.0) if total_migrations > 0 else 10.0,
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
                "• Run setup_alembic.py to configure Alembic",
                "• Use generated Alembic versions",
                "• Test migrations in development environment"
            ])
        else:
            recommendations.extend([
                f"⚠️ {unsafe_count} migrations have security issues",
                "• Review and fix unsafe migrations before transition",
                "• Remove dynamic SQL construction",
                "• Add input validation where needed",
                "• Test all migrations thoroughly"
            ])
        
        return recommendations


async def main():
    """Run migration security analysis and Alembic transition."""
    print("🔍 Database Migration Security Analyzer")
    print("=" * 50)
    
    tool = AlembicTransitionTool()
    
    # Look for migrations directory
    migrations_dir = Path("scripts/migrations")
    if not migrations_dir.exists():
        migrations_dir = Path("migrations")
    if not migrations_dir.exists():
        migrations_dir = Path("sql/migrations")
    
    print(f"📂 Scanning migrations in: {migrations_dir}")
    
    # Analyze migrations
    migrations = tool.analyzer.scan_migrations_directory(migrations_dir)
    report = tool.generate_migration_report(migrations)
    
    print(f"\n📊 MIGRATION ANALYSIS RESULTS")
    print(f"Total Migrations: {report['total_migrations']}")
    print(f"Safe Migrations: {report['safe_migrations']}")
    print(f"Unsafe Migrations: {report['unsafe_migrations']}")
    print(f"Security Score: {report['security_score']:.1f}/10.0")
    
    if report['unsafe_migrations'] > 0:
        print(f"\n⚠️ Security Issues Found:")
        for issue in report['security_issues'][:10]:  # Show first 10
            print(f"   • {issue}")
        
        if len(report['security_issues']) > 10:
            print(f"   ... and {len(report['security_issues']) - 10} more issues")
    
    print(f"\n🔍 Migration Details:")
    for migration in migrations[:5]:  # Show first 5
        status = "✅ SAFE" if migration.is_safe else "⚠️ UNSAFE"
        print(f"   {migration.path.name}: {status}")
    
    if len(migrations) > 5:
        print(f"   ... and {len(migrations) - 5} more migrations")
    
    # Check database connection
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        print(f"\n🔌 Checking applied migrations...")
        applied = await tool.get_applied_migrations(db_url)
        print(f"Applied in database: {len(applied)} migrations")
    else:
        print(f"\n💡 Set DATABASE_URL to check applied migrations")
    
    print(f"\n💡 Recommendations:")
    for rec in report['recommendations']:
        print(f"   {rec}")
    
    # Offer to create Alembic versions
    if report['safe_migrations'] > 0:
        print(f"\n🚀 Generate Alembic Versions?")
        print(f"This will create Alembic migration files from your SQL migrations.")
        
        # For demo purposes, create the files
        alembic_versions_dir = Path("alembic/versions")
        if alembic_versions_dir.parent.exists():
            tool.create_alembic_versions(
                [m for m in migrations if m.is_safe], 
                alembic_versions_dir
            )
            print(f"✅ Alembic versions created in {alembic_versions_dir}")
    
    status = "SECURE" if report['unsafe_migrations'] == 0 else "NEEDS_REVIEW"
    status_emoji = "✅" if status == "SECURE" else "⚠️"
    print(f"\n{status_emoji} Migration Security Status: {status}")


if __name__ == "__main__":
    asyncio.run(main())