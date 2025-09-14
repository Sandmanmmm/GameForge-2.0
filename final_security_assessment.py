"""
Final Security Assessment Report for GameForge Database
Comprehensive analysis of configuration, database, SQL injection, and migration security
"""

import re
from pathlib import Path
from typing import Dict, List, Any


class GameForgeSecurityAssessment:
    """Comprehensive security assessment for GameForge."""
    
    def __init__(self):
        self.workspace_path = Path(".")
    
    def assess_configuration_security(self) -> Dict[str, Any]:
        """Assess configuration security."""
        config_file = self.workspace_path / "gameforge" / "core" / "config.py"
        
        if not config_file.exists():
            return {
                'status': 'NOT_FOUND',
                'score': 0.0,
                'issues': ['Configuration file not found']
            }
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for secure patterns
            secure_patterns = [
                r'VaultClient',  # Vault integration
                r'os\.getenv',   # Environment variables
                r'_get_secret_or_env',  # Secure secret retrieval
            ]
            
            # Check for insecure patterns
            insecure_patterns = [
                r'open\s*\([^)]*[\'"][^\'"]*.(?:key|secret|password|token)',  # File reading secrets
                r'with\s+open.*(?:key|secret|password|token)',
                r'(?:password|secret|key|token)\s*=\s*[\'"][^\'"]+[\'"]',  # Hardcoded secrets
            ]
            
            secure_count = sum(1 for pattern in secure_patterns if re.search(pattern, content))
            insecure_count = sum(1 for pattern in insecure_patterns if re.search(pattern, content))
            
            if insecure_count > 0:
                return {
                    'status': 'INSECURE',
                    'score': 3.0,
                    'issues': [f'Found {insecure_count} insecure secret handling patterns']
                }
            elif secure_count >= 2:
                return {
                    'status': 'SECURE',
                    'score': 10.0,
                    'issues': []
                }
            else:
                return {
                    'status': 'BASIC',
                    'score': 7.0,
                    'issues': ['Limited secure secret handling patterns found']
                }
        
        except Exception as e:
            return {
                'status': 'ERROR',
                'score': 0.0,
                'issues': [f'Error analyzing config: {e}']
            }
    
    def assess_database_security(self) -> Dict[str, Any]:
        """Assess database security."""
        # Check main database files
        db_files = [
            "gameforge/app.py",
            "gameforge/core/health.py", 
            "scripts/migrate-database.py"
        ]
        
        sql_injection_risks = 0
        connection_security_score = 0
        total_files_checked = 0
        
        for file_path_str in db_files:
            file_path = self.workspace_path / file_path_str
            if not file_path.exists():
                continue
            
            total_files_checked += 1
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for SQL injection patterns (actual dangerous ones)
                dangerous_sql_patterns = [
                    r'cursor\.execute\s*\([^,)]*\+',  # String concatenation in execute
                    r'cursor\.execute\s*\(f[\'"]',    # F-string in execute
                    r'\.execute\([^,)]*%[sd]',        # String formatting in execute
                ]
                
                # Check for secure patterns
                secure_patterns = [
                    r'asyncpg\.create_pool',  # Connection pooling
                    r'SELECT\s+1',           # Health check queries
                    r'\.execute\([^,)]*,\s*\[',  # Parameterized queries
                ]
                
                sql_injection_risks += sum(1 for pattern in dangerous_sql_patterns 
                                         if re.search(pattern, content))
                connection_security_score += sum(1 for pattern in secure_patterns 
                                               if re.search(pattern, content))
                
            except Exception:
                continue
        
        if total_files_checked == 0:
            return {
                'status': 'NOT_FOUND',
                'score': 0.0,
                'sql_injection_risks': 0,
                'issues': ['No database files found']
            }
        
        if sql_injection_risks > 0:
            return {
                'status': 'VULNERABLE',
                'score': 2.0,
                'sql_injection_risks': sql_injection_risks,
                'issues': [f'Found {sql_injection_risks} SQL injection risks']
            }
        elif connection_security_score >= 2:
            return {
                'status': 'SECURE',
                'score': 9.0,
                'sql_injection_risks': 0,
                'issues': []
            }
        else:
            return {
                'status': 'BASIC',
                'score': 6.0,
                'sql_injection_risks': 0,
                'issues': ['Basic database security, could be improved']
            }
    
    def assess_migration_security(self) -> Dict[str, Any]:
        """Assess migration security with accurate detection."""
        migration_dirs = [
            "scripts/migrations",
            "migrations", 
            "archive/legacy-services/migrations"
        ]
        
        migration_files = []
        for dir_path_str in migration_dirs:
            dir_path = self.workspace_path / dir_path_str
            if dir_path.exists():
                migration_files.extend(dir_path.rglob("*.sql"))
        
        if not migration_files:
            return {
                'status': 'NO_MIGRATIONS',
                'score': 10.0,
                'total_migrations': 0,
                'issues': []
            }
        
        # Analyze actual dangerous patterns (not false positives)
        dangerous_patterns = [
            r'DELETE\s+FROM\s+\w+\s*;',  # DELETE without WHERE
            r'UPDATE\s+\w+\s+SET.*;\s*$',  # UPDATE without WHERE
            r'TRUNCATE\s+TABLE\s+(?!.*_temp|.*_backup)',  # TRUNCATE production tables
            r'DROP\s+(?:TABLE|DATABASE)\s+(?!IF\s+EXISTS)',  # DROP without IF EXISTS
        ]
        
        # Safe patterns that should not be flagged
        safe_exceptions = [
            r'JSONB\s+DEFAULT\s+',  # JSONB defaults
            r'GRANT\s+ALL.*TO\s+\w+',  # Database user grants (acceptable in setup)
            r'CREATE\s+TABLE',  # Table creation
            r'ALTER\s+TABLE',   # Table alterations
        ]
        
        total_migrations = len(migration_files)
        unsafe_migrations = 0
        security_issues = []
        
        for migration_file in migration_files:
            try:
                with open(migration_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_is_unsafe = False
                
                for line_num, line in enumerate(content.split('\n'), 1):
                    line = line.strip()
                    if not line or line.startswith('--'):
                        continue
                    
                    # Skip safe patterns
                    is_safe_exception = any(re.search(pattern, line, re.IGNORECASE) 
                                          for pattern in safe_exceptions)
                    if is_safe_exception:
                        continue
                    
                    # Check for actual dangerous patterns
                    for pattern in dangerous_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            security_issues.append(
                                f"{migration_file.name}:{line_num} - {line[:60]}..."
                            )
                            file_is_unsafe = True
                            break
                
                if file_is_unsafe:
                    unsafe_migrations += 1
                    
            except Exception:
                continue
        
        safe_migrations = total_migrations - unsafe_migrations
        security_score = (safe_migrations / total_migrations * 10.0) if total_migrations > 0 else 10.0
        
        if unsafe_migrations == 0:
            status = 'SECURE'
        elif security_score >= 7.0:
            status = 'MOSTLY_SECURE'
        else:
            status = 'NEEDS_REVIEW'
        
        return {
            'status': status,
            'score': security_score,
            'total_migrations': total_migrations,
            'safe_migrations': safe_migrations,
            'unsafe_migrations': unsafe_migrations,
            'issues': security_issues[:5]  # First 5 issues
        }
    
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate final comprehensive security report."""
        print("🔍 GameForge Security Assessment")
        print("=" * 50)
        
        # Run all assessments
        config_assessment = self.assess_configuration_security()
        database_assessment = self.assess_database_security() 
        migration_assessment = self.assess_migration_security()
        
        # Calculate overall score
        scores = [
            config_assessment['score'],
            database_assessment['score'],
            migration_assessment['score']
        ]
        overall_score = sum(scores) / len(scores)
        
        # Determine overall status
        if overall_score >= 9.0:
            overall_status = 'EXCELLENT'
            status_emoji = '🛡️'
        elif overall_score >= 7.0:
            overall_status = 'GOOD'
            status_emoji = '✅'
        elif overall_score >= 5.0:
            overall_status = 'ACCEPTABLE'
            status_emoji = '⚠️'
        else:
            overall_status = 'NEEDS_IMPROVEMENT'
            status_emoji = '🚨'
        
        # Display results
        print(f"\n📊 SECURITY ASSESSMENT RESULTS")
        print(f"Overall Security Score: {overall_score:.1f}/10.0")
        print(f"Overall Status: {overall_status}")
        
        print(f"\n🔧 Configuration Security: {config_assessment['score']:.1f}/10.0 ({config_assessment['status']})")
        if config_assessment['issues']:
            for issue in config_assessment['issues']:
                print(f"   • {issue}")
        
        print(f"\n🗄️ Database Security: {database_assessment['score']:.1f}/10.0 ({database_assessment['status']})")
        if database_assessment.get('sql_injection_risks', 0) > 0:
            print(f"   • SQL Injection Risks: {database_assessment['sql_injection_risks']}")
        if database_assessment['issues']:
            for issue in database_assessment['issues']:
                print(f"   • {issue}")
        
        print(f"\n📋 Migration Security: {migration_assessment['score']:.1f}/10.0 ({migration_assessment['status']})")
        if migration_assessment.get('total_migrations', 0) > 0:
            print(f"   • Total Migrations: {migration_assessment['total_migrations']}")
            print(f"   • Safe Migrations: {migration_assessment.get('safe_migrations', 0)}")
            if migration_assessment.get('unsafe_migrations', 0) > 0:
                print(f"   • Unsafe Migrations: {migration_assessment['unsafe_migrations']}")
        if migration_assessment['issues']:
            for issue in migration_assessment['issues']:
                print(f"   • {issue}")
        
        # Recommendations
        print(f"\n💡 Security Recommendations:")
        
        if config_assessment['status'] != 'SECURE':
            print("   🔧 Configuration:")
            print("      • Implement proper secret management with Vault or environment variables")
            print("      • Remove any hardcoded secrets from configuration files")
        
        if database_assessment['status'] != 'SECURE':
            print("   🗄️ Database:")
            print("      • Use parameterized queries exclusively ($1, $2, etc.)")
            print("      • Implement connection pooling and timeouts")
            print("      • Add database access logging")
        
        if migration_assessment['status'] != 'SECURE':
            print("   📋 Migrations:")
            print("      • Review unsafe migration patterns")
            print("      • Add WHERE clauses to DELETE/UPDATE statements")
            print("      • Use IF EXISTS checks for DROP operations")
        
        if overall_status == 'EXCELLENT':
            print("   ✅ Security practices are excellent - maintain current standards")
        elif overall_status == 'GOOD':
            print("   ✅ Good security posture - minor improvements recommended")
        
        print(f"\n{status_emoji} FINAL SECURITY STATUS: {overall_status}")
        print(f"Security Score: {overall_score:.1f}/10.0")
        
        return {
            'overall_score': overall_score,
            'overall_status': overall_status,
            'config_assessment': config_assessment,
            'database_assessment': database_assessment,
            'migration_assessment': migration_assessment
        }


def main():
    """Run comprehensive GameForge security assessment."""
    assessor = GameForgeSecurityAssessment()
    report = assessor.generate_final_report()
    return report


if __name__ == "__main__":
    main()