"""
Alembic environment configuration for GameForge.
Production-ready database migrations with comprehensive model support.
"""
import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from alembic import context

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import base and all models for migration detection
try:
    from gameforge.core.base import Base
    # Import all models to ensure they're detected by autogenerate
    from gameforge.models import *  # This imports all models
except ImportError as e:
    print(f"Warning: Could not import models: {e}")
    # If models cannot be imported, create minimal Base
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
# CRITICAL: Empty metadata since GF_Database handles all schema
target_metadata = Base.metadata


def get_database_url() -> str:
    """Get database URL from settings configuration."""
    try:
        from gameforge.core.config import get_settings
        settings = get_settings()
        
        # CRITICAL: Only allow GF_Database PostgreSQL - no SQLite fallback
        if hasattr(settings, 'database_url') and settings.database_url:
            db_url = settings.database_url
            # Ensure we're using GF_Database (PostgreSQL only)
            postgres_prefixes = ("postgresql://", "postgresql+asyncpg://")
            if not db_url.startswith(postgres_prefixes):
                raise ValueError(
                    f"Invalid database URL: {db_url}. "
                    "Only PostgreSQL GF_Database connections allowed."
                )
            
            # Convert asyncpg URL to sync for Alembic compatibility
            if db_url.startswith("postgresql+asyncpg://"):
                db_url = db_url.replace(
                    "postgresql+asyncpg://", "postgresql://"
                )
            return db_url
        else:
            raise ValueError(
                "DATABASE_URL not configured. "
                "GF_Database PostgreSQL connection required."
            )
    except Exception as e:
        raise ValueError(
            f"Failed to load GF_Database configuration: {e}. "
            "Ensure DATABASE_URL points to GF_Database PostgreSQL."
        )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Get database URL and ensure it's synchronous
    db_url = get_database_url()
    
    connectable = create_engine(db_url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()