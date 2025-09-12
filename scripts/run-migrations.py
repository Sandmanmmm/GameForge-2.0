#!/usr/bin/env python3
"""
Database Migration Runner for GameForge AI
"""

import os
import psycopg2
import glob
import logging
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'postgres'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'gameforge'),
            'user': os.getenv('DB_USER', 'gameforge'),
            'password': os.getenv('DB_PASSWORD', 'gameforge123')
        }
    
    def connect(self):
        """Connect to database"""
        return psycopg2.connect(**self.db_config)
    
    def create_migrations_table(self):
        """Create migrations tracking table"""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(50) PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migrations"""
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version FROM schema_migrations ORDER BY version")
                return [row[0] for row in cur.fetchall()]
    
    def apply_migration(self, migration_file: str):
        """Apply a single migration"""
        version = os.path.basename(migration_file).replace('.sql', '')
        
        logger.info(f"Applying migration: {version}")
        
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        with self.connect() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(sql)
                    cur.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)",
                        (version,)
                    )
                    conn.commit()
                    logger.info(f"✅ Migration {version} applied successfully")
                except Exception as e:
                    conn.rollback()
                    logger.error(f"❌ Migration {version} failed: {e}")
                    raise
    
    def run_migrations(self):
        """Run all pending migrations"""
        logger.info("Starting database migrations...")
        
        # Create migrations table
        self.create_migrations_table()
        
        # Get applied migrations
        applied = set(self.get_applied_migrations())
        
        # Find all migration files
        migration_files = sorted(glob.glob('migrations/versions/*.sql'))
        
        for migration_file in migration_files:
            version = os.path.basename(migration_file).replace('.sql', '')
            
            if version not in applied:
                self.apply_migration(migration_file)
            else:
                logger.info(f"⏭️  Migration {version} already applied")
        
        logger.info("✅ All migrations completed")

if __name__ == "__main__":
    runner = MigrationRunner()
    runner.run_migrations()
