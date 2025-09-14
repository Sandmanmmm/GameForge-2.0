"""
Alembic Configuration Setup for GameForge
Configures Alembic for standardized database migrations
"""

from pathlib import Path


def setup_alembic_config():
    """Setup Alembic configuration for GameForge."""
    
    # Create alembic directory structure
    alembic_dir = Path("alembic")
    alembic_dir.mkdir(exist_ok=True)
    
    versions_dir = alembic_dir / "versions"
    versions_dir.mkdir(exist_ok=True)
    
    # Create alembic.ini
    alembic_ini_content = """
# A generic, single database configuration.

[alembic]
# template used to generate migration files
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_\
%%(rev)s_%%(slug)s

# path to migration scripts
script_location = alembic

# version path separator; As mentioned above, this is the character used to split
# version_path_separator = :

# the version locations.  This defaults to the value of (script_location)/versions.
# version_locations = %(here)s/bar:%(here)s/bat:alembic/versions

# version path separator; default is os.pathsep.
# version_path_separator = :

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

sqlalchemy.url = postgresql+asyncpg://%(DB_USER)s:%(DB_PASSWORD)s@\
%(DB_HOST)s:%(DB_PORT)s/%(DB_NAME)s

[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79

# lint with attempts to fix using "ruff" - use the exec runner, execute a binary
# hooks = ruff
# ruff.type = exec
# ruff.executable = %(here)s/.venv/bin/ruff
# ruff.options = --fix

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
    
    with open("alembic.ini", "w") as f:
        f.write(alembic_ini_content.strip())
    
    # Create env.py
    env_py_content = '''"""
Alembic environment configuration for GameForge.
"""
import asyncio
import os
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import your models here for autogenerate support
# from gameforge.models import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate support
target_metadata = None  # Replace with Base.metadata when you have models

def get_database_url() -> str:
    """Get database URL from environment."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
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

def do_run_migrations(connection: Connection) -> None:
    """Run migrations with database connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
    
    env_py_path = alembic_dir / "env.py"
    with open(env_py_path, "w") as f:
        f.write(env_py_content)
    
    # Create script.py.mako
    script_mako_content = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade database schema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade database schema."""
    ${downgrades if downgrades else "pass"}
'''
    
    script_mako_path = alembic_dir / "script.py.mako"
    with open(script_mako_path, "w") as f:
        f.write(script_mako_content)
    
    print("✅ Alembic configuration created successfully!")
    print("📁 Created directories:")
    print(f"   - {alembic_dir}")
    print(f"   - {versions_dir}")
    print("📄 Created files:")
    print("   - alembic.ini")
    print(f"   - {env_py_path}")
    print(f"   - {script_mako_path}")
    print()
    print("🚀 Next steps:")
    print("1. Set DATABASE_URL environment variable")
    print("2. Create models and update target_metadata in env.py")
    print("3. Run: alembic revision --autogenerate -m 'Initial migration'")
    print("4. Run: alembic upgrade head")


if __name__ == "__main__":
    setup_alembic_config()