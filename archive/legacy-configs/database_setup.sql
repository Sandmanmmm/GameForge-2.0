-- GameForge Production Database Setup
-- Generated: 2025-09-04T16:22:23.017854

-- Create database
CREATE DATABASE gameforge_production;

-- Create user with password
CREATE USER gameforge_prod WITH PASSWORD 'gf_db_Ww_r2OpXEAlPyZC7jc1_QSO8EZwdSRoS';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE gameforge_production TO gameforge_prod;

-- Connect to the database
\c gameforge_production;

-- Create tables (basic schema)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    roles JSONB DEFAULT '["user"]',
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    scopes JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS asset_generations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    prompt TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    result_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- Create indexes for performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_asset_generations_user ON asset_generations(user_id);
CREATE INDEX idx_asset_generations_status ON asset_generations(status);

-- Grant permissions on tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gameforge_prod;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gameforge_prod;
