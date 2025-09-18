#!/usr/bin/env python3
"""
Add missing core production tables to complete the schema
"""

import psycopg2
import os
from dotenv import load_dotenv

def add_missing_core_tables():
    load_dotenv()
    
    conn = psycopg2.connect(
        host=os.getenv('DEV_DB_HOST'),
        port=os.getenv('DEV_DB_PORT'),
        database=os.getenv('DEV_DB_NAME'),
        user=os.getenv('DEV_DB_USER'),
        password=os.getenv('DEV_DB_PASSWORD')
    )
    
    cur = conn.cursor()
    
    try:
        print("🔧 Adding missing core production tables...")
        
        # 1. Access Tokens table (UserAuthToken model)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS access_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR(255) UNIQUE NOT NULL,
            token_type VARCHAR(50) DEFAULT 'bearer' NOT NULL,
            name VARCHAR(100),
            scopes JSON DEFAULT '[]',
            resource_type VARCHAR(50),
            resource_id VARCHAR(255),
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            last_used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT idx_access_tokens_user_id_key UNIQUE (user_id, name)
        )
        """)
        
        # Add indexes for access_tokens
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_access_tokens_user_id ON access_tokens(user_id);
        CREATE INDEX IF NOT EXISTS idx_access_tokens_hash ON access_tokens(token_hash);
        CREATE INDEX IF NOT EXISTS idx_access_tokens_expires ON access_tokens(expires_at);
        CREATE INDEX IF NOT EXISTS idx_access_tokens_resource ON access_tokens(resource_type, resource_id);
        CREATE INDEX IF NOT EXISTS idx_access_tokens_active ON access_tokens(is_active);
        """)
        print("  ✅ Created access_tokens table")
        
        # 2. Usage Metrics table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS usage_metrics (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            metric_type VARCHAR(100) NOT NULL,
            metric_name VARCHAR(100) NOT NULL,
            value DECIMAL(15,2) NOT NULL,
            unit VARCHAR(20),
            dimensions JSON DEFAULT '{}',
            tags VARCHAR[],
            period VARCHAR(20) DEFAULT 'point',
            period_start TIMESTAMP,
            period_end TIMESTAMP,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
        )
        """)
        
        # Add indexes for usage_metrics
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_usage_metrics_user_id ON usage_metrics(user_id);
        CREATE INDEX IF NOT EXISTS idx_usage_metrics_type ON usage_metrics(metric_type);
        CREATE INDEX IF NOT EXISTS idx_usage_metrics_name ON usage_metrics(metric_name);
        CREATE INDEX IF NOT EXISTS idx_usage_metrics_timestamp ON usage_metrics(timestamp);
        CREATE INDEX IF NOT EXISTS idx_usage_metrics_period ON usage_metrics(period, period_start);
        """)
        print("  ✅ Created usage_metrics table")
        
        # 3. Presigned URLs table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS presigned_urls (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            url TEXT NOT NULL,
            url_hash VARCHAR(64) UNIQUE NOT NULL,
            resource_type VARCHAR(50) NOT NULL,
            resource_id VARCHAR(255) NOT NULL,
            file_path VARCHAR(1000) NOT NULL,
            allowed_operations VARCHAR[],
            allowed_ips VARCHAR[],
            expires_at TIMESTAMP NOT NULL,
            max_uses INTEGER DEFAULT 1,
            use_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP
        )
        """)
        
        # Add indexes for presigned_urls
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_presigned_urls_user_id ON presigned_urls(user_id);
        CREATE INDEX IF NOT EXISTS idx_presigned_urls_expires ON presigned_urls(expires_at);
        CREATE INDEX IF NOT EXISTS idx_presigned_urls_resource ON presigned_urls(resource_type, resource_id);
        CREATE INDEX IF NOT EXISTS idx_presigned_urls_hash ON presigned_urls(url_hash);
        """)
        print("  ✅ Created presigned_urls table")
        
        # 4. Add some essential production features
        
        # Security Events table for advanced monitoring
        cur.execute("""
        CREATE TABLE IF NOT EXISTS security_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            event_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) DEFAULT 'info',
            source_ip INET,
            user_agent TEXT,
            event_data JSON DEFAULT '{}',
            risk_score INTEGER DEFAULT 0,
            is_resolved BOOLEAN DEFAULT FALSE,
            resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_security_events_user_id ON security_events(user_id);
        CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events(severity);
        CREATE INDEX IF NOT EXISTS idx_security_events_created ON security_events(created_at);
        CREATE INDEX IF NOT EXISTS idx_security_events_ip ON security_events(source_ip);
        """)
        print("  ✅ Created security_events table")
        
        # Rate Limits table for API throttling
        cur.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            api_key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,
            endpoint VARCHAR(200) NOT NULL,
            limit_type VARCHAR(20) NOT NULL, -- 'minute', 'hour', 'day'
            request_count INTEGER DEFAULT 0,
            max_requests INTEGER NOT NULL,
            window_start TIMESTAMP NOT NULL,
            window_end TIMESTAMP NOT NULL,
            is_blocked BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT ensure_user_or_api_key CHECK (user_id IS NOT NULL OR api_key_id IS NOT NULL)
        )
        """)
        
        cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_rate_limits_user_id ON rate_limits(user_id);
        CREATE INDEX IF NOT EXISTS idx_rate_limits_api_key_id ON rate_limits(api_key_id);
        CREATE INDEX IF NOT EXISTS idx_rate_limits_endpoint ON rate_limits(endpoint);
        CREATE INDEX IF NOT EXISTS idx_rate_limits_window ON rate_limits(window_start, window_end);
        CREATE INDEX IF NOT EXISTS idx_rate_limits_blocked ON rate_limits(is_blocked);
        """)
        print("  ✅ Created rate_limits table")
        
        conn.commit()
        print("🎉 All missing core tables created successfully!")
        
        # Verify final table count
        cur.execute("""
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        AND table_name != 'alembic_version'
        """)
        
        result = cur.fetchone()
        table_count = result[0] if result else 0
        print(f"📊 Total production tables: {table_count}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_missing_core_tables()