"""
GameForge Test Configuration and Fixtures

Central configuration for all test suites with shared fixtures,
test utilities, and common test infrastructure.
"""

import os
import sys
import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import Mock, AsyncMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Test configuration
TEST_CONFIG = {
    "database_url": "sqlite:///test.db",
    "redis_url": "redis://localhost:6379/15",  # Use test DB
    "test_data_dir": Path(__file__).parent / "data",
    "ml_models_dir": Path(__file__).parent / "models",
    "temp_dir": None,  # Will be set in fixtures
}

# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers and settings"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "ml: mark test as ML platform test"
    )
    config.addinivalue_line(
        "markers", "monitoring: mark test as monitoring test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "gpu: mark test as requiring GPU"
    )
    config.addinivalue_line(
        "markers", "network: mark test as requiring network access"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on location"""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        if "ml" in str(item.fspath):
            item.add_marker(pytest.mark.ml)
        elif "monitoring" in str(item.fspath):
            item.add_marker(pytest.mark.monitoring)


# ============================================================================
# Core Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files"""
    temp_path = tempfile.mkdtemp(prefix="gameforge_test_")
    TEST_CONFIG["temp_dir"] = Path(temp_path)
    
    try:
        yield Path(temp_path)
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_config(temp_dir: Path) -> Dict[str, Any]:
    """Test configuration with temporary paths"""
    config = TEST_CONFIG.copy()
    config.update({
        "temp_dir": temp_dir,
        "test_models_dir": temp_dir / "models",
        "test_data_dir": temp_dir / "data",
        "test_logs_dir": temp_dir / "logs",
    })
    
    # Create test directories
    for key, path in config.items():
        if key.endswith("_dir") and isinstance(path, Path):
            path.mkdir(parents=True, exist_ok=True)
    
    return config


# ============================================================================
# Mock Services
# ============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    mock.exists.return_value = False
    return mock


@pytest.fixture
def mock_database():
    """Mock database session"""
    mock = AsyncMock()
    mock.execute.return_value = Mock()
    mock.commit.return_value = None
    mock.rollback.return_value = None
    mock.close.return_value = None
    return mock


@pytest.fixture
def mock_ml_model():
    """Mock ML model for testing"""
    mock = Mock()
    mock.predict.return_value = {"result": "test_prediction"}
    mock.train.return_value = {"status": "completed"}
    mock.evaluate.return_value = {"accuracy": 0.95}
    return mock


@pytest.fixture
def mock_prometheus_client():
    """Mock Prometheus metrics client"""
    mock = Mock()
    mock.inc = Mock()
    mock.dec = Mock()
    mock.set = Mock()
    mock.observe = Mock()
    return mock


# ============================================================================
# API Testing Fixtures
# ============================================================================

@pytest.fixture
def mock_api_client():
    """Mock API client for testing endpoints"""
    from unittest.mock import AsyncMock
    
    client = AsyncMock()
    client.get.return_value.status_code = 200
    client.post.return_value.status_code = 201
    client.put.return_value.status_code = 200
    client.delete.return_value.status_code = 204
    
    return client


@pytest.fixture
def api_headers():
    """Common API headers for testing"""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "GameForge-Test-Client/1.0"
    }


# ============================================================================
# ML Platform Testing Fixtures
# ============================================================================

@pytest.fixture
def mock_experiment_tracker():
    """Mock experiment tracker"""
    tracker = Mock()
    tracker.create_experiment.return_value = "exp_123"
    tracker.log_metric.return_value = None
    tracker.log_artifact.return_value = None
    tracker.get_experiment.return_value = {
        "id": "exp_123",
        "name": "test_experiment",
        "status": "completed"
    }
    return tracker


@pytest.fixture
def mock_model_registry():
    """Mock model registry"""
    registry = Mock()
    registry.register_model.return_value = "model_123"
    registry.get_model.return_value = {
        "id": "model_123",
        "name": "test_model",
        "version": "1.0.0",
        "stage": "staging"
    }
    registry.promote_model.return_value = True
    return registry


@pytest.fixture
def sample_experiment_data():
    """Sample experiment data for testing"""
    return {
        "name": "test_experiment",
        "description": "Test experiment for unit testing",
        "parameters": {
            "learning_rate": 0.001,
            "batch_size": 32,
            "epochs": 10
        },
        "metrics": {
            "accuracy": 0.95,
            "loss": 0.05,
            "f1_score": 0.93
        },
        "artifacts": [
            "model.pkl",
            "config.json",
            "metrics.json"
        ]
    }


# ============================================================================
# Monitoring Testing Fixtures
# ============================================================================

@pytest.fixture
def mock_prometheus_metrics():
    """Mock Prometheus metrics data"""
    return {
        "status": "success",
        "data": {
            "result": [
                {
                    "metric": {
                        "__name__": "gameforge_requests_total",
                        "endpoint": "/api/ai/generate"
                    },
                    "values": [
                        [1694649600, "100"],
                        [1694649660, "105"],
                        [1694649720, "110"]
                    ]
                }
            ]
        }
    }


@pytest.fixture
def mock_grafana_dashboard():
    """Mock Grafana dashboard data"""
    return {
        "uid": "test_dashboard",
        "title": "GameForge Test Dashboard",
        "url": "http://grafana.local/d/test_dashboard",
        "tags": ["gameforge", "test"],
        "folder": "Test"
    }


# ============================================================================
# File System Testing Utilities
# ============================================================================

@pytest.fixture
def sample_model_file(temp_dir: Path):
    """Create a sample model file for testing"""
    model_path = temp_dir / "test_model.pkl"
    
    # Create a dummy model file
    import pickle
    dummy_model = {"type": "test_model", "version": "1.0.0"}
    with open(model_path, 'wb') as f:
        pickle.dump(dummy_model, f)
    
    return model_path


@pytest.fixture
def sample_dataset_file(temp_dir: Path):
    """Create a sample dataset file for testing"""
    dataset_path = temp_dir / "test_dataset.json"
    
    dataset_data = {
        "name": "test_dataset",
        "version": "1.0.0",
        "samples": [
            {"input": "test input 1", "output": "test output 1"},
            {"input": "test input 2", "output": "test output 2"}
        ]
    }
    
    import json
    with open(dataset_path, 'w') as f:
        json.dump(dataset_data, f)
    
    return dataset_path


# ============================================================================
# Security Testing Utilities
# ============================================================================

@pytest.fixture
def security_test_files(temp_dir: Path):
    """Create files with various security concerns for testing"""
    files = {}
    
    # File with potential secret
    secret_file = temp_dir / "config_with_secret.py"
    secret_file.write_text("""
# This is a test file with a fake secret
API_KEY = "sk-1234567890abcdef"  # This should be detected
DATABASE_URL = "postgresql://user:password@localhost/db"
    """)
    files["secret_file"] = secret_file
    
    # File with SQL injection vulnerability
    vuln_file = temp_dir / "vulnerable_code.py"
    vuln_file.write_text("""
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # SQL injection
    return execute_query(query)
    """)
    files["vuln_file"] = vuln_file
    
    return files


# ============================================================================
# Performance Testing Utilities
# ============================================================================

@pytest.fixture
def performance_timer():
    """Utility for measuring test performance"""
    import time
    
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, *args):
            self.end_time = time.time()
        
        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
    
    return Timer


# ============================================================================
# Network Testing Utilities
# ============================================================================

@pytest.fixture
def mock_http_responses():
    """Mock HTTP responses for network testing"""
    responses = {
        "prometheus_metrics": {
            "status_code": 200,
            "json": {
                "status": "success",
                "data": {"result": []}
            }
        },
        "grafana_dashboards": {
            "status_code": 200,
            "json": [
                {
                    "uid": "test",
                    "title": "Test Dashboard",
                    "tags": ["test"]
                }
            ]
        },
        "error_response": {
            "status_code": 500,
            "json": {"error": "Internal server error"}
        }
    }
    return responses


# ============================================================================
# Cleanup Utilities
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Automatic cleanup after each test"""
    yield
    
    # Clean up any temporary files or resources
    # This runs after each test
    import gc
    gc.collect()


def pytest_runtest_teardown(item, nextitem):
    """Clean up after each test"""
    # Additional cleanup if needed
    pass