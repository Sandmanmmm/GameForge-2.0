"""
GF_Database Health Check and Integration Validation
==================================================

Comprehensive health check to validate GameForge compatibility with GF_Database.
Validates all 19 tables, permission system, and migration status.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from gameforge.core.database import DatabaseManager
from gameforge.core.logging_config import get_structured_logger
from gameforge.core.config import get_settings

logger = get_structured_logger(__name__)


class GFDatabaseHealthCheck:
    """Comprehensive health check for GF_Database integration"""
    
    EXPECTED_TABLES = {
        # Core Application Tables (14 tables)
        'users': 'Complete user profiles with OAuth, 2FA, data classification',
        'user_preferences': 'Theme, notifications, language settings',
        'user_sessions': 'JWT token management with expiration tracking',
        'projects': 'Game development projects with metadata',
        'project_collaborators': 'Team management with role-based permissions',
        'assets': 'File management with versioning and classification',
        'game_templates': 'Template marketplace functionality',
        'ai_requests': 'AI service interaction tracking',
        'ml_models': 'Model artifacts with data classification',
        'datasets': 'Training data with versioning and classification',
        'audit_logs': 'Comprehensive action tracking with compliance fields',
        'api_keys': 'API access management with granular permissions',
        'system_config': 'Global system configuration',
        'schema_migrations': 'Database version control and migration tracking',
        
        # Integration Enhancement Tables (5 tables)
        'user_permissions': 'Granular user-level permissions with auto-assignment',
        'access_tokens': 'Short-lived credentials for temporary access',
        'presigned_urls': 'Direct file access tracking with expiration',
        'storage_configs': 'Multi-cloud storage provider configuration',
        'compliance_events': 'GDPR/CCPA compliance event logging'
    }
    
    EXPECTED_ROLES = ['basic_user', 'premium_user', 'ai_user', 'admin', 'super_admin']
    
    EXPECTED_PERMISSIONS = [
        'assets:read', 'assets:create', 'assets:update', 'assets:delete', 'assets:upload', 'assets:download',
        'projects:read', 'projects:create', 'projects:update', 'projects:delete', 'projects:share',
        'models:read', 'models:create', 'models:update', 'models:delete', 'models:train',
        'storage:read', 'storage:write', 'storage:delete', 'storage:admin',
        'ai:generate'
    ]
    
    def __init__(self):
        self.settings = get_settings()
        self.db_manager = DatabaseManager()
        
    async def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """
        Run complete health check and return detailed results
        
        Returns:
            Dictionary with health check results and recommendations
        """
        logger.info("🏥 Starting GF_Database comprehensive health check...")
        
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "unknown",
            "checks": {},
            "recommendations": [],
            "critical_issues": [],
            "warnings": []
        }
        
        try:
            # Initialize database connection
            await self.db_manager.initialize()
            
            # Run all health checks
            results["checks"]["connectivity"] = await self._check_database_connectivity()
            results["checks"]["schema"] = await self._check_schema_integrity()
            results["checks"]["tables"] = await self._check_table_structure()
            results["checks"]["migrations"] = await self._check_migration_status()
            results["checks"]["permissions"] = await self._check_permission_system()
            results["checks"]["roles"] = await self._check_user_roles()
            results["checks"]["storage"] = await self._check_storage_integration()
            results["checks"]["compliance"] = await self._check_compliance_features()
            results["checks"]["performance"] = await self._check_performance_metrics()
            
            # Determine overall status
            results["overall_status"] = self._calculate_overall_status(results["checks"])
            
            # Generate recommendations
            results["recommendations"] = self._generate_recommendations(results["checks"])
            
            logger.info(f"✅ Health check completed. Status: {results['overall_status']}")
            
        except Exception as e:
            results["overall_status"] = "critical_failure"
            results["critical_issues"].append(f"Health check failed: {str(e)}")
            logger.error(f"❌ Health check failed: {e}")
            
        return results
    
    async def _check_database_connectivity(self) -> Dict[str, Any]:
        """Test basic database connectivity"""
        try:
            async with self.db_manager.get_async_session() as session:
                result = await session.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                
                if test_value == 1:
                    return {
                        "status": "healthy",
                        "message": "Database connection successful",
                        "details": {
                            "database_url": self.settings.database_url.split('@')[1] if '@' in self.settings.database_url else "masked",
                            "connection_test": "passed"
                        }
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "message": "Database connection failed - unexpected response",
                        "details": {"test_result": test_value}
                    }
                    
        except Exception as e:
            return {
                "status": "critical",
                "message": f"Database connectivity failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_schema_integrity(self) -> Dict[str, Any]:
        """Check database schema integrity"""
        try:
            async with self.db_manager.get_async_session() as session:
                # Check if we can access information_schema
                result = await session.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
                ))
                table_count = result.scalar()
                
                return {
                    "status": "healthy" if table_count >= 19 else "warning",
                    "message": f"Found {table_count} tables in public schema",
                    "details": {
                        "expected_tables": 19,
                        "actual_tables": table_count,
                        "schema_accessible": True
                    }
                }
                
        except Exception as e:
            return {
                "status": "critical",
                "message": f"Schema integrity check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_table_structure(self) -> Dict[str, Any]:
        """Validate all expected tables exist with correct structure"""
        try:
            missing_tables = []
            existing_tables = []
            
            async with self.db_manager.get_async_session() as session:
                for table_name, description in self.EXPECTED_TABLES.items():
                    try:
                        result = await session.execute(text(
                            f"SELECT COUNT(*) FROM information_schema.tables "
                            f"WHERE table_name = '{table_name}' AND table_schema = 'public'"
                        ))
                        table_exists = result.scalar() > 0
                        
                        if table_exists:
                            existing_tables.append(table_name)
                        else:
                            missing_tables.append(table_name)
                            
                    except Exception as e:
                        missing_tables.append(f"{table_name} (error: {str(e)})")
            
            status = "healthy" if len(missing_tables) == 0 else "critical" if len(missing_tables) > 5 else "warning"
            
            return {
                "status": status,
                "message": f"Table structure check: {len(existing_tables)}/{len(self.EXPECTED_TABLES)} tables found",
                "details": {
                    "existing_tables": existing_tables,
                    "missing_tables": missing_tables,
                    "expected_count": len(self.EXPECTED_TABLES),
                    "actual_count": len(existing_tables)
                }
            }
            
        except Exception as e:
            return {
                "status": "critical",
                "message": f"Table structure check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_migration_status(self) -> Dict[str, Any]:
        """Check migration system status"""
        try:
            async with self.db_manager.get_async_session() as session:
                try:
                    # Check if schema_migrations table exists
                    result = await session.execute(text(
                        "SELECT version, applied_at FROM schema_migrations ORDER BY applied_at"
                    ))
                    migrations = result.fetchall()
                    
                    migration_versions = [row[0] for row in migrations]
                    
                    # Expected migrations for GF_Database integration
                    expected_migrations = ['001_initial_schema', '003_gameforge_integration_fixes']
                    missing_migrations = [m for m in expected_migrations if m not in migration_versions]
                    
                    status = "healthy" if len(missing_migrations) == 0 else "warning"
                    
                    return {
                        "status": status,
                        "message": f"Migration status: {len(migrations)} migrations applied",
                        "details": {
                            "applied_migrations": migration_versions,
                            "missing_migrations": missing_migrations,
                            "last_migration": migrations[-1] if migrations else None
                        }
                    }
                    
                except SQLAlchemyError:
                    # schema_migrations table doesn't exist
                    return {
                        "status": "critical",
                        "message": "Migration tracking system not found",
                        "details": {"error": "schema_migrations table missing"}
                    }
                    
        except Exception as e:
            return {
                "status": "critical",
                "message": f"Migration status check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_permission_system(self) -> Dict[str, Any]:
        """Validate permission system functionality"""
        try:
            async with self.db_manager.get_async_session() as session:
                # Check if permission-related tables exist
                permission_tables = ['user_permissions', 'users']
                missing_tables = []
                
                for table in permission_tables:
                    result = await session.execute(text(
                        f"SELECT COUNT(*) FROM information_schema.tables "
                        f"WHERE table_name = '{table}' AND table_schema = 'public'"
                    ))
                    if result.scalar() == 0:
                        missing_tables.append(table)
                
                if missing_tables:
                    return {
                        "status": "critical",
                        "message": f"Permission system incomplete: missing {missing_tables}",
                        "details": {"missing_tables": missing_tables}
                    }
                
                # Check if we have any user permissions
                try:
                    result = await session.execute(text("SELECT COUNT(*) FROM user_permissions"))
                    permission_count = result.scalar()
                    
                    status = "healthy" if permission_count > 0 else "warning"
                    message = f"Permission system active with {permission_count} permissions"
                    
                except SQLAlchemyError:
                    status = "warning"
                    message = "Permission tables exist but no permissions found"
                    permission_count = 0
                
                return {
                    "status": status,
                    "message": message,
                    "details": {
                        "permission_count": permission_count,
                        "expected_permissions": len(self.EXPECTED_PERMISSIONS),
                        "permission_tables_exist": True
                    }
                }
                
        except Exception as e:
            return {
                "status": "critical",
                "message": f"Permission system check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_user_roles(self) -> Dict[str, Any]:
        """Validate user role system"""
        try:
            async with self.db_manager.get_async_session() as session:
                try:
                    # Check if user_role enum exists and has correct values
                    result = await session.execute(text(
                        "SELECT unnest(enum_range(NULL::user_role)) as role_name"
                    ))
                    roles = [row[0] for row in result.fetchall()]
                    
                    missing_roles = [role for role in self.EXPECTED_ROLES if role not in roles]
                    extra_roles = [role for role in roles if role not in self.EXPECTED_ROLES]
                    
                    status = "healthy" if len(missing_roles) == 0 else "warning"
                    
                    return {
                        "status": status,
                        "message": f"Role system: {len(roles)} roles defined",
                        "details": {
                            "defined_roles": roles,
                            "expected_roles": self.EXPECTED_ROLES,
                            "missing_roles": missing_roles,
                            "extra_roles": extra_roles
                        }
                    }
                    
                except SQLAlchemyError:
                    return {
                        "status": "critical",
                        "message": "User role enum not found",
                        "details": {"error": "user_role enum missing"}
                    }
                    
        except Exception as e:
            return {
                "status": "critical",
                "message": f"User role check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_storage_integration(self) -> Dict[str, Any]:
        """Check storage integration features"""
        try:
            async with self.db_manager.get_async_session() as session:
                storage_tables = ['storage_configs', 'access_tokens', 'presigned_urls']
                existing_tables = []
                missing_tables = []
                
                for table in storage_tables:
                    result = await session.execute(text(
                        f"SELECT COUNT(*) FROM information_schema.tables "
                        f"WHERE table_name = '{table}' AND table_schema = 'public'"
                    ))
                    if result.scalar() > 0:
                        existing_tables.append(table)
                    else:
                        missing_tables.append(table)
                
                # Check if storage config exists
                storage_config_exists = False
                if 'storage_configs' in existing_tables:
                    try:
                        result = await session.execute(text("SELECT COUNT(*) FROM storage_configs"))
                        storage_config_exists = result.scalar() > 0
                    except SQLAlchemyError:
                        pass
                
                status = "healthy" if len(missing_tables) == 0 else "warning"
                
                return {
                    "status": status,
                    "message": f"Storage integration: {len(existing_tables)}/{len(storage_tables)} tables ready",
                    "details": {
                        "existing_tables": existing_tables,
                        "missing_tables": missing_tables,
                        "storage_config_exists": storage_config_exists
                    }
                }
                
        except Exception as e:
            return {
                "status": "critical",
                "message": f"Storage integration check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_compliance_features(self) -> Dict[str, Any]:
        """Check GDPR/CCPA compliance features"""
        try:
            async with self.db_manager.get_async_session() as session:
                compliance_tables = ['compliance_events', 'users', 'audit_logs']
                
                # Check if data classification enum exists
                try:
                    result = await session.execute(text(
                        "SELECT unnest(enum_range(NULL::data_classification)) as classification"
                    ))
                    classifications = [row[0] for row in result.fetchall()]
                    classification_enum_exists = len(classifications) > 0
                    
                except SQLAlchemyError:
                    classification_enum_exists = False
                    classifications = []
                
                # Check compliance_events table
                compliance_events_exists = False
                try:
                    result = await session.execute(text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_name = 'compliance_events' AND table_schema = 'public'"
                    ))
                    compliance_events_exists = result.scalar() > 0
                except SQLAlchemyError:
                    pass
                
                status = "healthy" if classification_enum_exists and compliance_events_exists else "warning"
                
                return {
                    "status": status,
                    "message": "Compliance features validation",
                    "details": {
                        "data_classification_enum": classification_enum_exists,
                        "classification_count": len(classifications),
                        "compliance_events_table": compliance_events_exists,
                        "gdpr_ready": classification_enum_exists and compliance_events_exists
                    }
                }
                
        except Exception as e:
            return {
                "status": "warning",
                "message": f"Compliance check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    async def _check_performance_metrics(self) -> Dict[str, Any]:
        """Check database performance and optimization"""
        try:
            async with self.db_manager.get_async_session() as session:
                # Check connection pool status
                pool_info = {}
                if hasattr(self.db_manager._async_engine, 'pool'):
                    pool = self.db_manager._async_engine.pool
                    pool_info = {
                        "pool_size": getattr(pool, 'size', 'unknown'),
                        "checked_in": getattr(pool, 'checkedin', 'unknown'),
                        "checked_out": getattr(pool, 'checkedout', 'unknown'),
                        "overflow": getattr(pool, 'overflow', 'unknown')
                    }
                
                # Check for critical indexes
                index_check = await session.execute(text(
                    "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public'"
                ))
                index_count = index_check.scalar()
                
                return {
                    "status": "healthy",
                    "message": f"Performance metrics: {index_count} indexes found",
                    "details": {
                        "connection_pool": pool_info,
                        "index_count": index_count,
                        "database_size": "unknown"  # Would need additional query
                    }
                }
                
        except Exception as e:
            return {
                "status": "warning",
                "message": f"Performance check failed: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _calculate_overall_status(self, checks: Dict[str, Dict[str, Any]]) -> str:
        """Calculate overall health status from individual checks"""
        statuses = [check.get("status", "unknown") for check in checks.values()]
        
        if "critical" in statuses:
            return "critical"
        elif "unhealthy" in statuses:
            return "unhealthy"
        elif "warning" in statuses:
            return "warning"
        elif all(status == "healthy" for status in statuses):
            return "healthy"
        else:
            return "unknown"
    
    def _generate_recommendations(self, checks: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations based on check results"""
        recommendations = []
        
        # Check for missing tables
        if checks.get("tables", {}).get("details", {}).get("missing_tables"):
            missing = checks["tables"]["details"]["missing_tables"]
            recommendations.append(
                f"Run database migrations to create missing tables: {', '.join(missing)}"
            )
        
        # Check migration status
        if checks.get("migrations", {}).get("details", {}).get("missing_migrations"):
            missing = checks["migrations"]["details"]["missing_migrations"]
            recommendations.append(
                f"Apply missing migrations: {', '.join(missing)}"
            )
        
        # Check permission system
        permission_count = checks.get("permissions", {}).get("details", {}).get("permission_count", 0)
        if permission_count == 0:
            recommendations.append(
                "Initialize permission system by creating users with roles to trigger auto-assignment"
            )
        
        # Check storage integration
        storage_missing = checks.get("storage", {}).get("details", {}).get("missing_tables", [])
        if storage_missing:
            recommendations.append(
                f"Complete storage integration by creating tables: {', '.join(storage_missing)}"
            )
        
        # Check compliance features
        if not checks.get("compliance", {}).get("details", {}).get("gdpr_ready", False):
            recommendations.append(
                "Enable GDPR/CCPA compliance by ensuring data_classification enum and compliance_events table exist"
            )
        
        return recommendations


# Convenience function for health check
async def run_gf_database_health_check() -> Dict[str, Any]:
    """Run comprehensive GF_Database health check"""
    health_checker = GFDatabaseHealthCheck()
    return await health_checker.run_comprehensive_health_check()


# CLI function for standalone health check
async def main():
    """CLI entry point for health check"""
    results = await run_gf_database_health_check()
    
    print("\n🏥 GF_Database Health Check Results")
    print("=" * 50)
    print(f"Overall Status: {results['overall_status'].upper()}")
    print(f"Timestamp: {results['timestamp']}")
    
    print("\n📊 Individual Checks:")
    for check_name, check_result in results['checks'].items():
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'unhealthy': '❌',
            'critical': '🚨'
        }.get(check_result['status'], '❓')
        
        print(f"  {status_emoji} {check_name}: {check_result['message']}")
    
    if results['recommendations']:
        print("\n💡 Recommendations:")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    if results['critical_issues']:
        print("\n🚨 Critical Issues:")
        for issue in results['critical_issues']:
            print(f"  - {issue}")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    asyncio.run(main())