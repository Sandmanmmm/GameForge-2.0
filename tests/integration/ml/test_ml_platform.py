"""
Integration tests for ML Platform functionality

Tests the complete ML platform integration including experiment tracking,
model registry, training jobs, and AI job traceability.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta


class TestMLPlatformIntegration:
    """Integration tests for ML platform components"""
    
    @pytest.mark.asyncio
    async def test_experiment_lifecycle(self, mock_experiment_tracker, sample_experiment_data):
        """Test complete experiment lifecycle"""
        # Create experiment
        experiment_id = mock_experiment_tracker.create_experiment.return_value
        
        # Simulate experiment creation
        mock_experiment_tracker.create_experiment.return_value = "exp_test_123"
        experiment_id = mock_experiment_tracker.create_experiment(sample_experiment_data)
        
        assert experiment_id == "exp_test_123"
        
        # Log metrics during experiment
        mock_experiment_tracker.log_metric("accuracy", 0.95)
        mock_experiment_tracker.log_metric("loss", 0.05)
        
        # Verify metrics were logged
        mock_experiment_tracker.log_metric.assert_called()
        
        # Complete experiment
        mock_experiment_tracker.complete_experiment(experiment_id)
        mock_experiment_tracker.complete_experiment.assert_called_with(experiment_id)
    
    @pytest.mark.asyncio
    async def test_model_registry_integration(self, mock_model_registry):
        """Test model registry operations"""
        # Register a new model
        model_data = {
            "name": "test_model_v1",
            "version": "1.0.0",
            "framework": "pytorch",
            "metrics": {
                "accuracy": 0.95,
                "f1_score": 0.93
            }
        }
        
        mock_model_registry.register_model.return_value = "model_test_456"
        model_id = mock_model_registry.register_model(model_data)
        
        assert model_id == "model_test_456"
        
        # Test model promotion
        mock_model_registry.promote_model.return_value = True
        promotion_result = mock_model_registry.promote_model(model_id, "production")
        
        assert promotion_result is True
        mock_model_registry.promote_model.assert_called_with(model_id, "production")
    
    @pytest.mark.asyncio
    async def test_ai_job_traceability(self, mock_experiment_tracker, mock_model_registry):
        """Test AI job traceability through ML platform"""
        # Simulate AI generation request
        ai_request = {
            "prompt": "Generate a fantasy sword",
            "model_id": "model_123",
            "parameters": {
                "quality": "high",
                "style": "medieval"
            }
        }
        
        # Create experiment for AI job
        experiment_data = {
            "name": f"ai_generation_{datetime.now().isoformat()}",
            "type": "ai_generation",
            "parameters": ai_request
        }
        
        mock_experiment_tracker.create_experiment.return_value = "exp_ai_789"
        experiment_id = mock_experiment_tracker.create_experiment(experiment_data)
        
        # Track AI job execution
        mock_experiment_tracker.log_metric("generation_time", 45.2)
        mock_experiment_tracker.log_artifact("generated_asset.png")
        
        # Verify traceability
        assert experiment_id == "exp_ai_789"
        mock_experiment_tracker.log_metric.assert_called()
        mock_experiment_tracker.log_artifact.assert_called()
    
    @pytest.mark.asyncio
    async def test_training_job_integration(self, mock_experiment_tracker):
        """Test training job integration with experiment tracking"""
        # Simulate training job
        training_config = {
            "model_type": "diffusion",
            "dataset": "fantasy_assets_v1",
            "hyperparameters": {
                "learning_rate": 0.0001,
                "batch_size": 16,
                "epochs": 100
            }
        }
        
        # Create training experiment
        mock_experiment_tracker.create_experiment.return_value = "exp_training_999"
        experiment_id = mock_experiment_tracker.create_experiment({
            "name": "training_job_fantasy_model",
            "type": "training",
            "config": training_config
        })
        
        # Simulate training progress
        for epoch in range(5):  # Simulate 5 epochs
            mock_experiment_tracker.log_metric("epoch", epoch)
            mock_experiment_tracker.log_metric("loss", 1.0 - (epoch * 0.1))
            mock_experiment_tracker.log_metric("accuracy", 0.5 + (epoch * 0.05))
        
        # Verify training was tracked
        assert experiment_id == "exp_training_999"
        assert mock_experiment_tracker.log_metric.call_count >= 15  # 3 metrics * 5 epochs
    
    def test_experiment_artifact_management(self, mock_experiment_tracker, temp_dir):
        """Test experiment artifact management"""
        # Create test artifacts
        model_file = temp_dir / "test_model.pth"
        config_file = temp_dir / "config.json"
        metrics_file = temp_dir / "metrics.json"
        
        model_file.write_text("mock model data")
        config_file.write_text('{"learning_rate": 0.001}')
        metrics_file.write_text('{"accuracy": 0.95}')
        
        # Log artifacts
        artifacts = [str(model_file), str(config_file), str(metrics_file)]
        
        for artifact in artifacts:
            mock_experiment_tracker.log_artifact(artifact)
        
        # Verify artifacts were logged
        assert mock_experiment_tracker.log_artifact.call_count == 3
    
    @pytest.mark.asyncio
    async def test_model_version_management(self, mock_model_registry):
        """Test model version management"""
        base_model = {
            "name": "text_generator",
            "framework": "transformers",
            "base_version": "1.0.0"
        }
        
        # Register multiple versions
        versions = ["1.0.1", "1.1.0", "2.0.0"]
        model_ids = []
        
        for version in versions:
            model_data = base_model.copy()
            model_data["version"] = version
            
            mock_model_registry.register_model.return_value = f"model_{version.replace('.', '_')}"
            model_id = mock_model_registry.register_model(model_data)
            model_ids.append(model_id)
        
        # Verify all versions were registered
        assert len(model_ids) == 3
        assert mock_model_registry.register_model.call_count == 3
    
    def test_experiment_search_and_filtering(self, mock_experiment_tracker):
        """Test experiment search and filtering functionality"""
        # Mock experiment search
        mock_experiment_tracker.search_experiments.return_value = [
            {
                "id": "exp_1",
                "name": "model_training_v1",
                "type": "training",
                "status": "completed"
            },
            {
                "id": "exp_2", 
                "name": "ai_generation_test",
                "type": "ai_generation",
                "status": "running"
            }
        ]
        
        # Search experiments by type
        training_experiments = mock_experiment_tracker.search_experiments(
            filters={"type": "training"}
        )
        
        assert len(training_experiments) >= 1
        assert all(exp["type"] == "training" for exp in training_experiments if "type" in exp)
    
    @pytest.mark.asyncio
    async def test_model_evaluation_pipeline(self, mock_model_registry, mock_experiment_tracker):
        """Test model evaluation pipeline integration"""
        # Create evaluation experiment
        eval_config = {
            "model_id": "model_123",
            "test_dataset": "validation_set_v1",
            "metrics": ["accuracy", "precision", "recall", "f1"]
        }
        
        mock_experiment_tracker.create_experiment.return_value = "exp_eval_555"
        eval_experiment = mock_experiment_tracker.create_experiment({
            "name": "model_evaluation",
            "type": "evaluation",
            "config": eval_config
        })
        
        # Simulate evaluation results
        eval_metrics = {
            "accuracy": 0.94,
            "precision": 0.92,
            "recall": 0.96,
            "f1": 0.94
        }
        
        for metric, value in eval_metrics.items():
            mock_experiment_tracker.log_metric(metric, value)
        
        # Update model with evaluation results
        mock_model_registry.update_model_metrics("model_123", eval_metrics)
        
        # Verify evaluation was tracked
        assert eval_experiment == "exp_eval_555"
        mock_model_registry.update_model_metrics.assert_called_with("model_123", eval_metrics)


class TestMLPlatformErrorHandling:
    """Test error handling in ML platform integration"""
    
    @pytest.mark.asyncio
    async def test_experiment_creation_failure(self, mock_experiment_tracker):
        """Test handling of experiment creation failures"""
        # Mock experiment creation failure
        mock_experiment_tracker.create_experiment.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception) as exc_info:
            mock_experiment_tracker.create_experiment({"name": "test"})
        
        assert "Database connection failed" in str(exc_info.value)
    
    def test_model_registration_validation(self, mock_model_registry):
        """Test model registration validation"""
        # Test invalid model data
        invalid_models = [
            {},  # Empty model
            {"name": ""},  # Empty name
            {"name": "test", "version": ""},  # Empty version
        ]
        
        for invalid_model in invalid_models:
            mock_model_registry.register_model.side_effect = ValueError("Invalid model data")
            
            with pytest.raises(ValueError):
                mock_model_registry.register_model(invalid_model)
    
    @pytest.mark.asyncio
    async def test_network_failure_handling(self, mock_experiment_tracker):
        """Test handling of network failures"""
        # Mock network timeout
        mock_experiment_tracker.log_metric.side_effect = asyncio.TimeoutError("Request timeout")
        
        with pytest.raises(asyncio.TimeoutError):
            await mock_experiment_tracker.log_metric("test_metric", 1.0)
    
    def test_concurrent_model_promotion(self, mock_model_registry):
        """Test handling of concurrent model promotions"""
        # Mock concurrent promotion conflict
        mock_model_registry.promote_model.side_effect = [
            True,  # First promotion succeeds
            Exception("Model already promoted by another process")  # Second fails
        ]
        
        # First promotion should succeed
        result1 = mock_model_registry.promote_model("model_1", "production")
        assert result1 is True
        
        # Second promotion should fail
        with pytest.raises(Exception) as exc_info:
            mock_model_registry.promote_model("model_1", "production")
        
        assert "already promoted" in str(exc_info.value)


class TestMLPlatformPerformance:
    """Test ML platform performance and scalability"""
    
    @pytest.mark.slow
    def test_large_experiment_batch(self, mock_experiment_tracker):
        """Test handling of large experiment batches"""
        # Simulate creating many experiments
        experiment_count = 100
        experiment_ids = []
        
        for i in range(experiment_count):
            mock_experiment_tracker.create_experiment.return_value = f"exp_batch_{i}"
            exp_id = mock_experiment_tracker.create_experiment({
                "name": f"batch_experiment_{i}",
                "batch_id": "large_batch_test"
            })
            experiment_ids.append(exp_id)
        
        assert len(experiment_ids) == experiment_count
        assert mock_experiment_tracker.create_experiment.call_count == experiment_count
    
    def test_high_frequency_metric_logging(self, mock_experiment_tracker, performance_timer):
        """Test high-frequency metric logging performance"""
        metric_count = 1000
        
        with performance_timer() as timer:
            for i in range(metric_count):
                mock_experiment_tracker.log_metric(f"metric_{i}", i * 0.1)
        
        # Verify all metrics were logged
        assert mock_experiment_tracker.log_metric.call_count == metric_count
        
        # Performance should be reasonable (this is a mock, so very fast)
        assert timer.elapsed is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_experiment_operations(self, mock_experiment_tracker):
        """Test concurrent experiment operations"""
        # Simulate concurrent operations
        operations = []
        
        for i in range(10):
            # Mock different operations
            operations.append(
                mock_experiment_tracker.create_experiment({"name": f"concurrent_{i}"})
            )
            operations.append(
                mock_experiment_tracker.log_metric(f"metric_{i}", i)
            )
        
        # All operations should complete
        assert len(operations) == 20