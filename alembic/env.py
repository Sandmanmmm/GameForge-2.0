"""
Alembic environment configuration for GameForge.
"""
import os
import sys
import importlib.util
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import pool, create_engine
from sqlalchemy.engine import Connection
from alembic import context

# Add the project root to Python path
project_root = Path(__file__).parent.parent
# Add project root to path 
sys.path.insert(0, str(project_root))
# Add models path for external models directory
sys.path.append(r"D:\models")

# Import your models here for autogenerate support
# Import from the production models package
from gameforge.models import Base
# Import all model classes to ensure they're registered with Base.metadata
from gameforge.models import User, UserAuthToken, Project, Asset, APIKey, AuditLog, UsageMetrics

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = Base.metadata

def get_database_url() -> str:
    """Get database URL from settings configuration."""
    try:
        from gameforge.core.config import get_settings
        settings = get_settings()
        # Use SQLite for development if no specific database URL is set
        if hasattr(settings, 'database_url') and settings.database_url:
            return settings.database_url
        else:
            # Default to SQLite for development
            return "sqlite:///./gameforge_dev.db"
    except Exception as e:
        # Fallback to SQLite if settings can't be loaded
        return "sqlite:///./gameforge_dev.db"
    
    # Convert asyncpg URL to sync for Alembic compatibility
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        )
    elif database_url.startswith("postgresql://"):
        # Already correct format
        pass
    else:
        raise ValueError("Unsupported database URL format")
    
    return database_url

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
    # Convert async postgres URL to sync if needed
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    elif db_url.startswith("sqlite+aiosqlite://"):
        db_url = db_url.replace("sqlite+aiosqlite://", "sqlite:///")
    
    # Override the config URL
    config.set_main_option("sqlalchemy.url", db_url)
    
    connectable = create_engine(db_url, poolclass=pool.NullPool)
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
