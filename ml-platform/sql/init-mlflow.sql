-- MLflow Database Initialization Script
-- Creates necessary tables and indexes for production deployment

-- Create MLflow schema if not exists
CREATE SCHEMA IF NOT EXISTS mlflow;

-- Set search path
SET search_path TO mlflow, public;

-- Create tables for MLflow tracking
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id SERIAL PRIMARY KEY,
    name VARCHAR(256) NOT NULL UNIQUE,
    artifact_location VARCHAR(500),
    lifecycle_stage VARCHAR(32) CHECK (lifecycle_stage IN ('active', 'deleted')),
    creation_time BIGINT,
    last_update_time BIGINT
);

CREATE TABLE IF NOT EXISTS runs (
    run_uuid VARCHAR(32) NOT NULL PRIMARY KEY,
    name VARCHAR(250),
    source_type VARCHAR(20) CHECK (source_type IN ('NOTEBOOK', 'JOB', 'LOCAL', 'UNKNOWN', 'PROJECT')),
    source_name VARCHAR(500),
    entry_point_name VARCHAR(50),
    user_id VARCHAR(256),
    status VARCHAR(9) CHECK (status IN ('SCHEDULED', 'FAILED', 'FINISHED', 'RUNNING', 'KILLED')),
    start_time BIGINT,
    end_time BIGINT,
    source_version VARCHAR(50),
    lifecycle_stage VARCHAR(20) CHECK (lifecycle_stage IN ('active', 'deleted')),
    artifact_uri VARCHAR(200),
    experiment_id INTEGER NOT NULL,
    deleted_time BIGINT,
    FOREIGN KEY (experiment_id) REFERENCES experiments (experiment_id)
);

CREATE TABLE IF NOT EXISTS metrics (
    key VARCHAR(250) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    timestamp BIGINT NOT NULL,
    run_uuid VARCHAR(32) NOT NULL,
    step BIGINT DEFAULT 0 NOT NULL,
    is_nan BOOLEAN DEFAULT FALSE NOT NULL,
    PRIMARY KEY (key, timestamp, step, run_uuid, is_nan),
    FOREIGN KEY (run_uuid) REFERENCES runs (run_uuid)
);

CREATE TABLE IF NOT EXISTS params (
    key VARCHAR(250) NOT NULL,
    value VARCHAR(500) NOT NULL,
    run_uuid VARCHAR(32) NOT NULL,
    PRIMARY KEY (key, run_uuid),
    FOREIGN KEY (run_uuid) REFERENCES runs (run_uuid)
);

CREATE TABLE IF NOT EXISTS tags (
    key VARCHAR(250) NOT NULL,
    value VARCHAR(5000),
    run_uuid VARCHAR(32) NOT NULL,
    PRIMARY KEY (key, run_uuid),
    FOREIGN KEY (run_uuid) REFERENCES runs (run_uuid)
);

-- Model Registry tables
CREATE TABLE IF NOT EXISTS registered_models (
    name VARCHAR(256) NOT NULL PRIMARY KEY,
    creation_time BIGINT,
    last_updated_time BIGINT,
    description VARCHAR(5000)
);

CREATE TABLE IF NOT EXISTS model_versions (
    name VARCHAR(256) NOT NULL,
    version INTEGER NOT NULL,
    creation_time BIGINT,
    last_updated_time BIGINT,
    description VARCHAR(5000),
    user_id VARCHAR(256),
    current_stage VARCHAR(20),
    source VARCHAR(500),
    run_id VARCHAR(32),
    status VARCHAR(20) CHECK (status IN ('PENDING_REGISTRATION', 'FAILED_REGISTRATION', 'READY')),
    status_message VARCHAR(500),
    run_link VARCHAR(500),
    storage_location VARCHAR(500),
    PRIMARY KEY (name, version),
    FOREIGN KEY (name) REFERENCES registered_models (name) ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS model_version_tags (
    name VARCHAR(256) NOT NULL,
    version INTEGER NOT NULL,
    key VARCHAR(250) NOT NULL,
    value VARCHAR(5000),
    PRIMARY KEY (name, version, key),
    FOREIGN KEY (name, version) REFERENCES model_versions (name, version) ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS registered_model_tags (
    name VARCHAR(256) NOT NULL,
    key VARCHAR(250) NOT NULL,
    value VARCHAR(5000),
    PRIMARY KEY (name, key),
    FOREIGN KEY (name) REFERENCES registered_models (name) ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS registered_model_aliases (
    name VARCHAR(256) NOT NULL,
    alias VARCHAR(256) NOT NULL,
    version INTEGER NOT NULL,
    PRIMARY KEY (name, alias),
    FOREIGN KEY (name, version) REFERENCES model_versions (name, version) ON UPDATE CASCADE
);

-- Custom GameForge extensions
CREATE TABLE IF NOT EXISTS model_deployments (
    deployment_id SERIAL PRIMARY KEY,
    model_name VARCHAR(256) NOT NULL,
    model_version INTEGER NOT NULL,
    deployment_type VARCHAR(50) NOT NULL CHECK (deployment_type IN ('canary', 'blue_green', 'rolling', 'shadow')),
    environment VARCHAR(50) NOT NULL CHECK (environment IN ('staging', 'production', 'testing')),
    traffic_percentage INTEGER DEFAULT 0 CHECK (traffic_percentage >= 0 AND traffic_percentage <= 100),
    status VARCHAR(20) NOT NULL CHECK (status IN ('deploying', 'active', 'inactive', 'failed', 'rollback')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deployment_config JSONB,
    FOREIGN KEY (model_name, model_version) REFERENCES model_versions (name, version)
);

CREATE TABLE IF NOT EXISTS model_metrics (
    metric_id SERIAL PRIMARY KEY,
    model_name VARCHAR(256) NOT NULL,
    model_version INTEGER NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metric_type VARCHAR(50) NOT NULL CHECK (metric_type IN ('accuracy', 'precision', 'recall', 'f1', 'auc', 'latency', 'throughput', 'error_rate')),
    environment VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_name, model_version) REFERENCES model_versions (name, version)
);

CREATE TABLE IF NOT EXISTS model_drift_reports (
    report_id SERIAL PRIMARY KEY,
    model_name VARCHAR(256) NOT NULL,
    model_version INTEGER NOT NULL,
    drift_score DOUBLE PRECISION NOT NULL,
    drift_type VARCHAR(50) NOT NULL CHECK (drift_type IN ('data', 'concept', 'prediction')),
    threshold DOUBLE PRECISION NOT NULL,
    is_drift_detected BOOLEAN NOT NULL,
    report_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_name, model_version) REFERENCES model_versions (name, version)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_runs_experiment_id ON runs (experiment_id);
CREATE INDEX IF NOT EXISTS idx_runs_start_time ON runs (start_time);
CREATE INDEX IF NOT EXISTS idx_runs_lifecycle_stage ON runs (lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_metrics_run_uuid ON metrics (run_uuid);
CREATE INDEX IF NOT EXISTS idx_params_run_uuid ON params (run_uuid);
CREATE INDEX IF NOT EXISTS idx_tags_run_uuid ON tags (run_uuid);
CREATE INDEX IF NOT EXISTS idx_model_versions_name ON model_versions (name);
CREATE INDEX IF NOT EXISTS idx_model_versions_stage ON model_versions (current_stage);
CREATE INDEX IF NOT EXISTS idx_model_deployments_status ON model_deployments (status);
CREATE INDEX IF NOT EXISTS idx_model_deployments_environment ON model_deployments (environment);
CREATE INDEX IF NOT EXISTS idx_model_metrics_timestamp ON model_metrics (timestamp);
CREATE INDEX IF NOT EXISTS idx_model_drift_reports_created_at ON model_drift_reports (created_at);

-- Create roles and permissions
CREATE ROLE mlflow_admin;
CREATE ROLE mlflow_user;
CREATE ROLE mlflow_readonly;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA mlflow TO mlflow_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA mlflow TO mlflow_user;
GRANT SELECT ON ALL TABLES IN SCHEMA mlflow TO mlflow_readonly;

-- Grant sequence permissions
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA mlflow TO mlflow_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA mlflow TO mlflow_user;

-- Default experiment
INSERT INTO experiments (experiment_id, name, artifact_location, lifecycle_stage, creation_time, last_update_time)
VALUES (0, 'Default', 's3://gameforge-ml-artifacts/0', 'active', 
        EXTRACT(epoch FROM CURRENT_TIMESTAMP) * 1000, 
        EXTRACT(epoch FROM CURRENT_TIMESTAMP) * 1000)
ON CONFLICT (experiment_id) DO NOTHING;

-- GameForge specific experiments
INSERT INTO experiments (name, artifact_location, lifecycle_stage, creation_time, last_update_time)
VALUES 
    ('game-ai-models', 's3://gameforge-ml-artifacts/game-ai', 'active', 
     EXTRACT(epoch FROM CURRENT_TIMESTAMP) * 1000, 
     EXTRACT(epoch FROM CURRENT_TIMESTAMP) * 1000),
    ('npc-behavior', 's3://gameforge-ml-artifacts/npc-behavior', 'active', 
     EXTRACT(epoch FROM CURRENT_TIMESTAMP) * 1000, 
     EXTRACT(epoch FROM CURRENT_TIMESTAMP) * 1000),
    ('procedural-generation', 's3://gameforge-ml-artifacts/proc-gen', 'active', 
     EXTRACT(epoch FROM CURRENT_TIMESTAMP) * 1000, 
     EXTRACT(epoch FROM CURRENT_TIMESTAMP) * 1000)
ON CONFLICT (name) DO NOTHING;

-- Create audit trigger for model deployments
CREATE OR REPLACE FUNCTION update_deployment_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_model_deployments_timestamp
    BEFORE UPDATE ON model_deployments
    FOR EACH ROW
    EXECUTE FUNCTION update_deployment_timestamp();

-- Create notification function for critical drift detection
CREATE OR REPLACE FUNCTION notify_drift_detection()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_drift_detected = TRUE AND NEW.drift_score > 0.8 THEN
        PERFORM pg_notify('model_drift_alert', 
            json_build_object(
                'model_name', NEW.model_name,
                'model_version', NEW.model_version,
                'drift_score', NEW.drift_score,
                'drift_type', NEW.drift_type
            )::text
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER notify_critical_drift
    AFTER INSERT ON model_drift_reports
    FOR EACH ROW
    EXECUTE FUNCTION notify_drift_detection();

-- ========================================================================
-- Dataset Versioning and DVC Integration Tables
-- ========================================================================

-- Dataset metadata and versioning
CREATE TABLE IF NOT EXISTS dataset_metadata (
    dataset_id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(256) NOT NULL,
    version VARCHAR(100) NOT NULL,
    description TEXT,
    format VARCHAR(50) NOT NULL,
    size_bytes BIGINT NOT NULL,
    file_count INTEGER NOT NULL,
    schema_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(256) NOT NULL,
    tags JSONB,
    validation_results JSONB,
    lineage JSONB,
    status VARCHAR(50) DEFAULT 'available' CHECK (status IN ('uploading', 'validating', 'available', 'deprecated', 'archived', 'failed')),
    dvc_path VARCHAR(500),
    s3_path VARCHAR(500),
    UNIQUE(dataset_name, version)
);

-- Dataset drift analysis
CREATE TABLE IF NOT EXISTS dataset_drift_analysis (
    analysis_id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(256) NOT NULL,
    baseline_version VARCHAR(100) NOT NULL,
    current_version VARCHAR(100) NOT NULL,
    drift_score DOUBLE PRECISION NOT NULL,
    drift_status VARCHAR(50) NOT NULL CHECK (drift_status IN ('no_drift', 'minor_drift', 'moderate_drift', 'severe_drift')),
    analysis_results JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_name, baseline_version) REFERENCES dataset_metadata (dataset_name, version),
    FOREIGN KEY (dataset_name, current_version) REFERENCES dataset_metadata (dataset_name, version)
);

-- Data validation rules
CREATE TABLE IF NOT EXISTS dataset_validation_rules (
    rule_id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(256) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    column_name VARCHAR(256),
    condition_type VARCHAR(50) NOT NULL,
    threshold_value TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('error', 'warning', 'info')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dataset usage tracking
CREATE TABLE IF NOT EXISTS dataset_usage (
    usage_id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(256) NOT NULL,
    version VARCHAR(100) NOT NULL,
    used_by_experiment VARCHAR(256),
    used_by_model VARCHAR(256),
    usage_type VARCHAR(50) NOT NULL CHECK (usage_type IN ('training', 'validation', 'testing', 'inference')),
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(256),
    FOREIGN KEY (dataset_name, version) REFERENCES dataset_metadata (dataset_name, version)
);

-- Data lineage tracking
CREATE TABLE IF NOT EXISTS dataset_lineage (
    lineage_id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(256) NOT NULL,
    version VARCHAR(100) NOT NULL,
    parent_dataset_name VARCHAR(256),
    parent_version VARCHAR(100),
    transformation_type VARCHAR(100),
    transformation_script TEXT,
    transformation_params JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_name, version) REFERENCES dataset_metadata (dataset_name, version),
    FOREIGN KEY (parent_dataset_name, parent_version) REFERENCES dataset_metadata (dataset_name, version)
);

-- Data quality metrics
CREATE TABLE IF NOT EXISTS dataset_quality_metrics (
    metric_id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(256) NOT NULL,
    version VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metric_type VARCHAR(50) NOT NULL,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_name, version) REFERENCES dataset_metadata (dataset_name, version)
);

-- DVC cache management
CREATE TABLE IF NOT EXISTS dvc_cache_info (
    cache_id SERIAL PRIMARY KEY,
    dataset_name VARCHAR(256) NOT NULL,
    version VARCHAR(100) NOT NULL,
    dvc_hash VARCHAR(64) NOT NULL,
    cache_path VARCHAR(500) NOT NULL,
    cache_size_bytes BIGINT NOT NULL,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1,
    FOREIGN KEY (dataset_name, version) REFERENCES dataset_metadata (dataset_name, version)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_dataset_metadata_name_version ON dataset_metadata (dataset_name, version);
CREATE INDEX IF NOT EXISTS idx_dataset_metadata_created_at ON dataset_metadata (created_at);
CREATE INDEX IF NOT EXISTS idx_dataset_metadata_status ON dataset_metadata (status);
CREATE INDEX IF NOT EXISTS idx_dataset_drift_analysis_dataset ON dataset_drift_analysis (dataset_name);
CREATE INDEX IF NOT EXISTS idx_dataset_drift_analysis_created_at ON dataset_drift_analysis (created_at);
CREATE INDEX IF NOT EXISTS idx_dataset_usage_dataset ON dataset_usage (dataset_name, version);
CREATE INDEX IF NOT EXISTS idx_dataset_usage_used_at ON dataset_usage (used_at);
CREATE INDEX IF NOT EXISTS idx_dataset_lineage_dataset ON dataset_lineage (dataset_name, version);
CREATE INDEX IF NOT EXISTS idx_dataset_quality_metrics_dataset ON dataset_quality_metrics (dataset_name, version);
CREATE INDEX IF NOT EXISTS idx_dvc_cache_info_dataset ON dvc_cache_info (dataset_name, version);

-- Create update trigger for dataset metadata
CREATE OR REPLACE FUNCTION update_dataset_metadata_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_dataset_metadata_timestamp
    BEFORE UPDATE ON dataset_metadata
    FOR EACH ROW
    EXECUTE FUNCTION update_dataset_metadata_timestamp();

-- Create notification function for severe data drift
CREATE OR REPLACE FUNCTION notify_data_drift_detection()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.drift_status IN ('severe_drift', 'moderate_drift') THEN
        PERFORM pg_notify('data_drift_alert', 
            json_build_object(
                'dataset_name', NEW.dataset_name,
                'baseline_version', NEW.baseline_version,
                'current_version', NEW.current_version,
                'drift_score', NEW.drift_score,
                'drift_status', NEW.drift_status
            )::text
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER notify_data_drift
    AFTER INSERT ON dataset_drift_analysis
    FOR EACH ROW
    EXECUTE FUNCTION notify_data_drift_detection();

-- Grant permissions for dataset tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA mlflow TO mlflow_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA mlflow TO mlflow_user;
GRANT SELECT ON ALL TABLES IN SCHEMA mlflow TO mlflow_readonly;

-- Grant sequence permissions for new tables
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA mlflow TO mlflow_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA mlflow TO mlflow_user;