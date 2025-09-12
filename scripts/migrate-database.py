#!/usr/bin/env python3
"""
GameForge AI Production Database Migration System
Handles PostgreSQL schema management and data migrations
"""

import os
import sys
import json
import logging
import asyncio
import psycopg2
import psycopg2.extensions
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any

import asyncpg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "database_migration", "message": "%(message)s", "correlation_id": "%(correlation_id)s"}',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/app/logs/database_migration.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Production-grade database migration system"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.migrations_dir = Path('/app/migrations')
        self.correlation_id = os.getenv('REQUEST_ID', f"migration-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        # Ensure migrations directory exists
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        
        # Add correlation ID to logger context
        old_factory = logging.getLogRecordFactory()
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.correlation_id = self.correlation_id
            return record
        logging.setLogRecordFactory(record_factory)
    
    async def check_connection(self) -> bool:
        """Test database connectivity"""
        try:
            conn = await asyncpg.connect(self.database_url)
            await conn.execute('SELECT 1')
            await conn.close()
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    async def ensure_migration_table(self, conn: asyncpg.Connection):
        """Create migration tracking table if it doesn't exist"""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(255) NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                execution_time_ms INTEGER,
                checksum VARCHAR(64),
                correlation_id VARCHAR(255)
            )
        """)
        
        # Create index for performance
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_schema_migrations_version 
            ON schema_migrations(version)
        """)
        
        logger.info("Migration tracking table ensured")
    
    async def get_applied_migrations(self, conn: asyncpg.Connection) -> List[str]:
        """Get list of already applied migrations"""
        rows = await conn.fetch("SELECT version FROM schema_migrations ORDER BY version")
        return [row['version'] for row in rows]
    
    def get_migration_files(self) -> List[Dict[str, Any]]:
        """Get list of migration files to apply"""
        migrations = []
        
        # Look for SQL migration files
        for sql_file in sorted(self.migrations_dir.glob('*.sql')):
            # Extract version from filename (e.g., 001_initial_schema.sql)
            parts = sql_file.stem.split('_', 1)
            if len(parts) >= 2 and parts[0].isdigit():
                version = parts[0]
                name = parts[1] if len(parts) > 1 else sql_file.stem
                
                migrations.append({
                    'version': version,
                    'name': name,
                    'file_path': sql_file,
                    'type': 'sql'
                })
        
        # Look for Python migration files
        for py_file in sorted(self.migrations_dir.glob('*.py')):
            if py_file.name.startswith('migration_'):
                parts = py_file.stem.split('_', 2)
                if len(parts) >= 3 and parts[1].isdigit():
                    version = parts[1]
                    name = parts[2] if len(parts) > 2 else py_file.stem
                    
                    migrations.append({
                        'version': version,
                        'name': name,
                        'file_path': py_file,
                        'type': 'python'
                    })
        
        return sorted(migrations, key=lambda x: x['version'])
    
    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of migration file"""
        import hashlib
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    async def apply_sql_migration(self, conn: asyncpg.Connection, migration: Dict[str, Any]) -> bool:
        """Apply SQL migration file"""
        try:
            sql_content = migration['file_path'].read_text(encoding='utf-8')
            
            # Split on semicolons and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            start_time = datetime.now()
            
            async with conn.transaction():
                for statement in statements:
                    if statement:
                        await conn.execute(statement)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Record migration
            checksum = self.calculate_checksum(migration['file_path'])
            await conn.execute("""
                INSERT INTO schema_migrations (version, name, execution_time_ms, checksum, correlation_id)
                VALUES ($1, $2, $3, $4, $5)
            """, migration['version'], migration['name'], int(execution_time), checksum, self.correlation_id)
            
            logger.info(f"Applied SQL migration {migration['version']}: {migration['name']} ({execution_time:.2f}ms)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply SQL migration {migration['version']}: {e}")
            return False
    
    async def apply_python_migration(self, conn: asyncpg.Connection, migration: Dict[str, Any]) -> bool:
        """Apply Python migration file"""
        try:
            # Import the migration module
            import importlib.util
            spec = importlib.util.spec_from_file_location("migration", migration['file_path'])
            migration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration_module)
            
            # Check if it has the required up() function
            if not hasattr(migration_module, 'up'):
                logger.error(f"Python migration {migration['version']} missing 'up()' function")
                return False
            
            start_time = datetime.now()
            
            # Execute the migration
            async with conn.transaction():
                await migration_module.up(conn)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Record migration
            checksum = self.calculate_checksum(migration['file_path'])
            await conn.execute("""
                INSERT INTO schema_migrations (version, name, execution_time_ms, checksum, correlation_id)
                VALUES ($1, $2, $3, $4, $5)
            """, migration['version'], migration['name'], int(execution_time), checksum, self.correlation_id)
            
            logger.info(f"Applied Python migration {migration['version']}: {migration['name']} ({execution_time:.2f}ms)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply Python migration {migration['version']}: {e}")
            return False
    
    async def validate_migration_integrity(self, conn: asyncpg.Connection) -> bool:
        """Validate that applied migrations match their checksums"""
        logger.info("Validating migration integrity...")
        
        applied_migrations = await conn.fetch("""
            SELECT version, name, checksum FROM schema_migrations 
            ORDER BY version
        """)
        
        integrity_ok = True
        
        for migration_record in applied_migrations:
            version = migration_record['version']
            stored_checksum = migration_record['checksum']
            
            # Find the migration file
            migration_files = self.get_migration_files()
            migration_file = next((m for m in migration_files if m['version'] == version), None)
            
            if migration_file:
                current_checksum = self.calculate_checksum(migration_file['file_path'])
                if current_checksum != stored_checksum:
                    logger.error(f"Migration integrity check failed for {version}: checksum mismatch")
                    integrity_ok = False
                else:
                    logger.info(f"Migration {version}: integrity OK")
            else:
                logger.warning(f"Migration file for version {version} not found (possibly removed)")
        
        return integrity_ok
    
    async def run_migrations(self, validate_integrity: bool = True) -> bool:
        """Run all pending migrations"""
        logger.info("Starting database migration process")
        
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # Ensure migration table exists
            await self.ensure_migration_table(conn)
            
            # Validate integrity of existing migrations
            if validate_integrity:
                if not await self.validate_migration_integrity(conn):
                    logger.error("Migration integrity validation failed")
                    await conn.close()
                    return False
            
            # Get applied and pending migrations
            applied_migrations = await self.get_applied_migrations(conn)
            available_migrations = self.get_migration_files()
            
            # Filter to pending migrations
            pending_migrations = [
                m for m in available_migrations 
                if m['version'] not in applied_migrations
            ]
            
            if not pending_migrations:
                logger.info("No pending migrations to apply")
                await conn.close()
                return True
            
            logger.info(f"Found {len(pending_migrations)} pending migrations")
            
            # Apply migrations in order
            success_count = 0
            for migration in pending_migrations:
                logger.info(f"Applying migration {migration['version']}: {migration['name']}")
                
                if migration['type'] == 'sql':
                    success = await self.apply_sql_migration(conn, migration)
                elif migration['type'] == 'python':
                    success = await self.apply_python_migration(conn, migration)
                else:
                    logger.error(f"Unknown migration type: {migration['type']}")
                    success = False
                
                if success:
                    success_count += 1
                else:
                    logger.error(f"Migration {migration['version']} failed, stopping")
                    break
            
            await conn.close()
            
            if success_count == len(pending_migrations):
                logger.info(f"Successfully applied {success_count} migrations")
                return True
            else:
                logger.error(f"Migration process failed: {success_count}/{len(pending_migrations)} applied")
                return False
                
        except Exception as e:
            logger.error(f"Migration process failed: {e}")
            return False
    
    async def rollback_migration(self, target_version: str) -> bool:
        """Rollback to a specific migration version"""
        logger.info(f"Rolling back to migration version: {target_version}")
        
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # Get migrations to rollback (those after target version)
            to_rollback = await conn.fetch("""
                SELECT version, name FROM schema_migrations 
                WHERE version > $1
                ORDER BY version DESC
            """, target_version)
            
            if not to_rollback:
                logger.info("No migrations to rollback")
                await conn.close()
                return True
            
            # Remove migrations from tracking table
            async with conn.transaction():
                await conn.execute("""
                    DELETE FROM schema_migrations WHERE version > $1
                """, target_version)
            
            logger.info(f"Rolled back {len(to_rollback)} migrations")
            await conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

# Create initial migration files if they don't exist
def create_initial_migrations():
    """Create initial migration files for GameForge schema"""
    migrations_dir = Path('/app/migrations')
    migrations_dir.mkdir(parents=True, exist_ok=True)
    
    # Initial schema migration
    initial_schema = """-- GameForge AI Initial Schema
-- Version: 001
-- Description: Create core tables for GameForge AI platform

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- Sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_name ON projects(name);

-- Generated content table
CREATE TABLE IF NOT EXISTS generated_content (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL, -- 'image', 'text', 'audio', etc.
    prompt TEXT NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    model_version VARCHAR(50),
    generation_params JSONB DEFAULT '{}',
    content_url VARCHAR(255), -- URL to stored content
    content_metadata JSONB DEFAULT '{}',
    processing_time_ms INTEGER,
    status VARCHAR(50) DEFAULT 'processing', -- 'processing', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_generated_content_project_id ON generated_content(project_id);
CREATE INDEX idx_generated_content_user_id ON generated_content(user_id);
CREATE INDEX idx_generated_content_status ON generated_content(status);
CREATE INDEX idx_generated_content_created_at ON generated_content(created_at);

-- Model usage tracking
CREATE TABLE IF NOT EXISTS model_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model_name VARCHAR(255) NOT NULL,
    operation_type VARCHAR(50) NOT NULL, -- 'inference', 'training', etc.
    usage_count INTEGER DEFAULT 1,
    processing_time_ms INTEGER,
    gpu_memory_mb INTEGER,
    cost_credits DECIMAL(10,4),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_model_usage_user_id ON model_usage(user_id);
CREATE INDEX idx_model_usage_model_name ON model_usage(model_name);
CREATE INDEX idx_model_usage_created_at ON model_usage(created_at);

-- API keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100),
    resource_id INTEGER,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    correlation_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX idx_audit_log_correlation_id ON audit_log(correlation_id);"""
    
    initial_file = migrations_dir / '001_initial_schema.sql'
    if not initial_file.exists():
        initial_file.write_text(initial_schema)
        logger.info("Created initial schema migration")

async def main():
    """Main function for standalone migration execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GameForge Database Migrator')
    parser.add_argument('--check-connection', action='store_true', help='Test database connection')
    parser.add_argument('--migrate', action='store_true', help='Run pending migrations')
    parser.add_argument('--rollback', help='Rollback to specific version')
    parser.add_argument('--create-initial', action='store_true', help='Create initial migration files')
    parser.add_argument('--validate', action='store_true', help='Validate migration integrity')
    
    args = parser.parse_args()
    
    # Create initial migrations if requested
    if args.create_initial:
        create_initial_migrations()
        print("✅ Initial migration files created")
        return
    
    migrator = DatabaseMigrator()
    
    try:
        if args.check_connection:
            success = await migrator.check_connection()
            sys.exit(0 if success else 1)
        elif args.migrate:
            success = await migrator.run_migrations()
            sys.exit(0 if success else 1)
        elif args.rollback:
            success = await migrator.rollback_migration(args.rollback)
            sys.exit(0 if success else 1)
        elif args.validate:
            conn = await asyncpg.connect(migrator.database_url)
            await migrator.ensure_migration_table(conn)
            success = await migrator.validate_migration_integrity(conn)
            await conn.close()
            sys.exit(0 if success else 1)
        else:
            # Default: run migrations
            success = await migrator.run_migrations()
            sys.exit(0 if success else 1)
            
    except Exception as e:
        logger.error(f"Migration operation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())