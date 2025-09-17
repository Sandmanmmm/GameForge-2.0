# Production Database Configuration for GameForge
# Connection pooling and production database settings

import os
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

# Production database configuration with connection pooling
DATABASE_CONFIG = {
    # Direct PostgreSQL connection (without pgBouncer)
    'DIRECT_DATABASE_URL': os.getenv(
        'DATABASE_URL', 
        'postgresql://gameforge:gameforge123@localhost:5432/gameforge_prod'
    ),
    
    # PgBouncer connection (recommended for production)
    'POOLED_DATABASE_URL': os.getenv(
        'PGBOUNCER_URL',
        'postgresql://gameforge:gameforge123@localhost:6432/gameforge_prod'
    ),
    
    # SQLAlchemy engine configuration
    'ENGINE_CONFIG': {
        'pool_size': 20,           # Number of connections to maintain
        'max_overflow': 30,        # Additional connections when pool is full
        'pool_timeout': 30,        # Seconds to wait for connection
        'pool_recycle': 3600,      # Recycle connections every hour
        'pool_pre_ping': True,     # Validate connections before use
        'echo': False,             # Set to True for SQL debugging
        'future': True,            # Use SQLAlchemy 2.0 style
    }
}

# Production Redis configuration (for caching and sessions)
REDIS_CONFIG = {
    'REDIS_URL': os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    'REDIS_POOL_SIZE': 10,
    'REDIS_TIMEOUT': 5,
}

# Production application configuration
PRODUCTION_CONFIG = {
    'DEBUG': False,
    'TESTING': False,
    'SECRET_KEY': os.getenv('SECRET_KEY', 'production-secret-key-change-me'),
    'JWT_SECRET_KEY': os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-me'),
    'CORS_ORIGINS': os.getenv('CORS_ORIGINS', '*').split(','),
    'MAX_CONTENT_LENGTH': 100 * 1024 * 1024,  # 100MB max file upload
}

# Database engine factory for production use
def create_production_engine(use_pooling=True):
    """Create a production database engine with appropriate pooling."""
    
    database_url = DATABASE_CONFIG['POOLED_DATABASE_URL'] if use_pooling else DATABASE_CONFIG['DIRECT_DATABASE_URL']
    
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        **DATABASE_CONFIG['ENGINE_CONFIG']
    )
    
    return engine

# Connection health check
def test_database_connection(engine):
    """Test database connection health."""
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1").scalar()
            return result == 1
    except Exception as e:
        print(f"Database connection test failed: {e}")
        return False

# Performance monitoring setup
def setup_database_monitoring(engine):
    """Setup database performance monitoring."""
    from sqlalchemy import event
    
    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()
    
    @event.listens_for(engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = time.time() - context._query_start_time
        if total > 1.0:  # Log slow queries (>1 second)
            print(f"Slow query detected: {total:.2f}s - {statement[:100]}...")

if __name__ == "__main__":
    # Test production database configuration
    print("Testing production database configuration...")
    
    engine = create_production_engine(use_pooling=False)
    if test_database_connection(engine):
        print("✅ Direct database connection successful")
    else:
        print("❌ Direct database connection failed")
    
    # Test with pooling if pgBouncer is available
    try:
        pooled_engine = create_production_engine(use_pooling=True)
        if test_database_connection(pooled_engine):
            print("✅ Pooled database connection successful")
        else:
            print("❌ Pooled database connection failed (pgBouncer may not be running)")
    except Exception as e:
        print(f"❌ Pooled connection setup failed: {e}")