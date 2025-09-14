"""
Comprehensive health checking for GameForge application.
"""
import asyncio
import time
from typing import Dict, Any, Optional

import redis.asyncio as redis
from gameforge.core.database import DatabaseManager


class HealthChecker:
    """Health checker for all application dependencies."""
    
    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        self.db_manager = db_manager
        self.redis_client = redis_client
        self.start_time = time.time()
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Basic health check with overall status.
        
        Returns:
            Dict with status and basic health information
        """
        health_checks = await self._run_health_checks()
        
        # Determine overall status
        all_healthy = all(
            check["status"] == "healthy" 
            for check in health_checks.values()
        )
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": time.time(),
            "uptime": time.time() - self.start_time,
            "checks": {
                name: check["status"] 
                for name, check in health_checks.items()
            }
        }
    
    async def detailed_health_check(self) -> Dict[str, Any]:
        """
        Detailed health check with full dependency information.
        
        Returns:
            Dict with detailed health information for all dependencies
        """
        health_checks = await self._run_health_checks()
        
        # Determine overall status
        all_healthy = all(
            check["status"] == "healthy" 
            for check in health_checks.values()
        )
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": time.time(),
            "uptime": time.time() - self.start_time,
            "version": "1.0.0",
            "environment": "production",
            "checks": health_checks
        }
    
    async def check_readiness(self) -> Dict[str, Any]:
        """
        Kubernetes readiness check.
        
        Returns:
            Dict indicating if the application is ready to serve traffic
        """
        health_checks = await self._run_health_checks()
        
        # For readiness, we need critical services to be healthy
        critical_services = ["database", "redis"]
        ready = all(
            health_checks.get(service, {}).get("status") == "healthy"
            for service in critical_services
        )
        
        return {
            "ready": ready,
            "timestamp": time.time(),
            "critical_services": {
                service: health_checks.get(service, {}).get("status", "unknown")
                for service in critical_services
            }
        }
    
    async def _run_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run all health checks concurrently."""
        checks = {}
        
        # Run checks concurrently
        tasks = []
        
        if self.db_manager:
            tasks.append(("database", self._check_database()))
        
        if self.redis_client:
            tasks.append(("redis", self._check_redis()))
        
        # Add other service checks
        tasks.extend([
            ("application", self._check_application()),
            ("disk_space", self._check_disk_space()),
            ("memory", self._check_memory())
        ])
        
        # Execute all checks
        for name, task in tasks:
            try:
                checks[name] = await task
            except Exception as e:
                checks[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.time()
                }
        
        return checks
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check SQLAlchemy database connectivity."""
        if not self.db_manager:
            return {
                "status": "unhealthy",
                "error": "Database manager not initialized",
                "timestamp": time.time()
            }
        
        try:
            start_time = time.time()
            # Use the database manager's health check method
            is_healthy = await self.db_manager.health_check()
            duration = time.time() - start_time
            
            if is_healthy:
                return {
                    "status": "healthy",
                    "response_time": f"{duration:.3f}s",
                    "timestamp": time.time()
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Database health check failed",
                    "response_time": f"{duration:.3f}s",
                    "timestamp": time.time()
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        if not self.redis_client:
            return {
                "status": "unhealthy",
                "error": "Redis client not initialized",
                "timestamp": time.time()
            }
        
        try:
            start_time = time.time()
            result = await self.redis_client.ping()
            duration = time.time() - start_time
            
            if result:
                return {
                    "status": "healthy",
                    "response_time": f"{duration:.3f}s",
                    "timestamp": time.time()
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Redis ping failed",
                    "timestamp": time.time()
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def _check_application(self) -> Dict[str, Any]:
        """Check application-specific health."""
        try:
            # Basic application health - could be extended
            # with more specific checks
            return {
                "status": "healthy",
                "uptime": time.time() - self.start_time,
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def _check_disk_space(self) -> Dict[str, Any]:
        """Check available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            
            # Convert to GB
            total_gb = total // (1024**3)
            used_gb = used // (1024**3)
            free_gb = free // (1024**3)
            usage_percent = (used / total) * 100
            
            # Consider unhealthy if > 90% used
            status = "unhealthy" if usage_percent > 90 else "healthy"
            
            return {
                "status": status,
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "usage_percent": round(usage_percent, 2),
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def _check_memory(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            # Consider unhealthy if > 90% used
            status = "unhealthy" if memory.percent > 90 else "healthy"
            
            return {
                "status": status,
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_percent": memory.percent,
                "timestamp": time.time()
            }
        except ImportError:
            # psutil not available
            return {
                "status": "unknown",
                "error": "psutil not available",
                "timestamp": time.time()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }