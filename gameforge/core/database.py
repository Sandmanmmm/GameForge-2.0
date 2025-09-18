"""
Production-Ready SQLAlchemy Database Configuration
==================================================

Provides database engine, session management, and classified data models
for the GameForge AI Platform with full data classification integration.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Any, Dict
import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession, 
    async_sessionmaker, 
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy import (
    create_engine, 
    MetaData, 
    event,
    text
)
from gameforge.core.config import get_settings
from gameforge.core.logging_config import get_structured_logger
from gameforge.core.base import Base  # Import Base from separate module

# Import all models to ensure they're registered with SQLAlchemy
# This is critical for proper schema creation and relationships
from gameforge.models import *  # Import all 44 tables

logger = get_structured_logger(__name__)

# Naming convention for database constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

# Apply naming convention to metadata
Base.metadata.naming_convention = convention

class DatabaseManager:
    """
    Production-ready database manager with async support and connection pooling.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._async_engine: Optional[AsyncEngine] = None
        self._sync_engine = None
        self._async_session_factory: Optional[async_sessionmaker] = None
        self._sync_session_factory = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize database connections and session factories."""
        if self._initialized:
            return
        
        try:
            # Configure database URL for async operations
            db_url = self.settings.database_url
            
            # For development, allow local PostgreSQL connections
            postgres_prefixes = ("postgresql://", "postgresql+asyncpg://")
            if not db_url.startswith(postgres_prefixes):
                raise ValueError(
                    f"Invalid database URL: {db_url}. "
                    "Only PostgreSQL connections allowed."
                )
            
            logger.info(f"🔗 Connecting to database: {db_url.split('@')[0]}@***")
            
            # Convert sync PostgreSQL URL to async if needed
            if db_url.startswith("postgresql://"):
                async_db_url = db_url.replace(
                    "postgresql://", "postgresql+asyncpg://", 1
                )
            else:
                async_db_url = db_url
            
            # Create async engine with production settings
            self._async_engine = create_async_engine(
                async_db_url,
                echo=self.settings.debug,
                pool_pre_ping=True,
                pool_recycle=3600,  # Recycle connections every hour
                pool_size=20,  # GF_Database supports large connection pools
                max_overflow=30,
                connect_args={
                    "server_settings": {
                        "application_name": "gameforge_ai_platform",
                    }
                }
            )
            
            # Create sync engine for migrations and admin tasks
            if db_url.startswith("postgresql://"):
                sync_db_url = db_url
            else:
                sync_db_url = db_url.replace(
                    "postgresql+asyncpg://", "postgresql://", 1
                )
            self._sync_engine = create_engine(
                sync_db_url,
                echo=self.settings.debug,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_size=10,
                max_overflow=20
            )
            
            # Create session factories
            self._async_session_factory = async_sessionmaker(
                bind=self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self._sync_session_factory = sessionmaker(
                bind=self._sync_engine,
                expire_on_commit=False
            )
            
            # Test connection
            await self._test_connection()
            
            self._initialized = True
            logger.info("✅ Database manager initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database manager: {e}")
            raise
    
    async def _test_connection(self):
        """Test database connection."""
        try:
            async with self._async_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("🔗 Database connection test successful")
        except Exception as e:
            logger.error(f"🔗 Database connection test failed: {e}")
            raise
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session with automatic cleanup."""
        if not self._initialized:
            await self.initialize()
        
        async with self._async_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def get_sync_session(self):
        """Get sync database session for migrations and admin tasks."""
        if not self._initialized:
            raise RuntimeError("Database manager not initialized. Call initialize() first.")
        
        return self._sync_session_factory()
    
    async def create_tables(self):
        """Create all database tables."""
        if not self._initialized:
            await self.initialize()
        
        async with self._async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("📊 Database tables created")
    
    async def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        if not self._initialized:
            await self.initialize()
        
        async with self._async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("🗑️  Database tables dropped")
    
    async def close(self):
        """Close database connections."""
        if self._async_engine:
            await self._async_engine.dispose()
        if self._sync_engine:
            self._sync_engine.dispose()
        
        self._initialized = False
        logger.info("🔒 Database connections closed")
    
    async def health_check(self) -> bool:
        """Check database health by executing a simple query."""
        if not self._initialized or not self._async_engine:
            return False
            
        try:
            async with self.get_async_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1 as health_check"))
                row = result.fetchone()
                return row and row[0] == 1
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False
    
    @property
    def async_engine(self) -> AsyncEngine:
        """Get async database engine."""
        if not self._async_engine:
            raise RuntimeError("Database manager not initialized")
        return self._async_engine
    
    @property
    def sync_engine(self):
        """Get sync database engine."""
        if not self._sync_engine:
            raise RuntimeError("Database manager not initialized")
        return self._sync_engine

# Global database manager instance
db_manager = DatabaseManager()

def setup_database_event_listeners(db_manager: Optional["DatabaseManager"] = None):
    """
    Set up database event listeners.
    
    This function is separated to avoid issues during migration generation
    where event listeners can cause problems with pool assertions.
    
    Args:
        db_manager: Optional DatabaseManager instance to register events on.
                   If not provided, registers global event listeners.
    """
    from sqlalchemy.pool import Pool
    from sqlalchemy import Engine
    
    if db_manager and db_manager._async_engine:
        # Register events on the specific engine instance
        sync_engine = db_manager._async_engine.sync_engine
        
        @event.listens_for(sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance and data integrity."""
            if 'sqlite' in str(dbapi_connection):
                with dbapi_connection.cursor() as cursor:
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    cursor.execute("PRAGMA temp_store=MEMORY")
                    cursor.execute("PRAGMA mmap_size=268435456")  # 256MB

        @event.listens_for(sync_engine, "before_cursor_execute")
        def log_queries(conn, cursor, statement, parameters, context, executemany):
            """Log database queries in debug mode."""
            if get_settings().debug:
                logger.debug(f"🔍 SQL Query: {statement}")
                if parameters:
                    logger.debug(f"🔍 Parameters: {parameters}")
                    
        logger.info("✅ Database event listeners registered on engine instance")
    else:
        # Register global event listeners on Engine class
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma_global(dbapi_connection, connection_record):
            """Set SQLite pragmas for better performance and data integrity."""
            if 'sqlite' in str(dbapi_connection):
                with dbapi_connection.cursor() as cursor:
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    cursor.execute("PRAGMA temp_store=MEMORY")
                    cursor.execute("PRAGMA mmap_size=268435456")  # 256MB

        @event.listens_for(Engine, "before_cursor_execute")
        def log_queries_global(conn, cursor, statement, parameters, context, executemany):
            """Log database queries in debug mode."""
            if get_settings().debug:
                logger.debug(f"🔍 SQL Query: {statement}")
                if parameters:
                    logger.debug(f"🔍 Parameters: {parameters}")
                    
        logger.info("✅ Global database event listeners registered")

# Convenience functions for database operations
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session."""
    async with db_manager.get_async_session() as session:
        yield session

def get_sync_session():
    """Get sync database session."""
    return db_manager.get_sync_session()

async def init_database():
    """Initialize database."""
    await db_manager.initialize()

async def create_tables():
    """Create database tables."""
    await db_manager.create_tables()

async def close_database():
    """Close database connections."""
    await db_manager.close()

# Database event listeners for logging and monitoring


# Health check function for database
async def health_check() -> Dict[str, Any]:
    """Check database health."""
    try:
        async with db_manager.get_async_session() as session:
            result = await session.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                return {
                    "status": "healthy",
                    "database": "connected",
                    "engine": str(db_manager.async_engine.url).split('@')[0] + '@***'
                }
            else:
                return {
                    "status": "unhealthy",
                    "database": "query_failed"
                }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "connection_failed",
            "error": str(e)
        }

# Export all necessary components
__all__ = [
    'Base',
    'DatabaseManager',
    'db_manager',
    'get_async_session',
    'get_sync_session',
    'init_database',
    'create_tables',
    'close_database',
    'health_check'
]