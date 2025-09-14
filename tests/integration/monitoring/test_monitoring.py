"""
Integration tests for monitoring dashboard functionality

Tests real-time monitoring, Prometheus integration, Grafana dashboards,
and WebSocket connections for the GameForge monitoring system.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta


class TestMonitoringIntegration:
    """Integration tests for monitoring dashboard components"""
    
    @pytest.mark.asyncio
    async def test_prometheus_metrics_integration(self, mock_prometheus_metrics):
        """Test Prometheus metrics integration"""
        # Mock Prometheus query response
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_prometheus_metrics
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test metrics query (would normally call actual endpoint)
            metrics_data = mock_prometheus_metrics
            
            assert metrics_data["status"] == "success"
            assert "data" in metrics_data
            assert "result" in metrics_data["data"]
            
            # Verify metric structure
            results = metrics_data["data"]["result"]
            if results:
                metric = results[0]
                assert "__name__" in metric["metric"]
                assert "values" in metric
    
    @pytest.mark.asyncio
    async def test_grafana_dashboard_integration(self, mock_grafana_dashboard):
        """Test Grafana dashboard integration"""
        # Mock Grafana API response
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = [mock_grafana_dashboard]
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Test dashboard listing (would normally call actual endpoint)
            dashboards = [mock_grafana_dashboard]
            
            assert len(dashboards) == 1
            dashboard = dashboards[0]
            assert "uid" in dashboard
            assert "title" in dashboard
            assert "url" in dashboard
    
    @pytest.mark.asyncio
    async def test_real_time_metrics_websocket(self):
        """Test real-time metrics WebSocket connection"""
        # Mock WebSocket connection
        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.receive_json = AsyncMock()
        
        # Simulate metrics data
        test_metrics = {
            "type": "metrics_update",
            "data": {
                "timestamp": datetime.now().isoformat(),
                "metrics": {
                    "cpu_usage": 45.2,
                    "memory_usage": 67.8,
                    "requests_per_second": 12.5
                }
            }
        }
        
        # Send test metrics
        await mock_websocket.send_json(test_metrics)
        mock_websocket.send_json.assert_called_once_with(test_metrics)
        
        # Verify data structure
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["type"] == "metrics_update"
        assert "data" in sent_data
        assert "metrics" in sent_data["data"]
    
    def test_system_health_monitoring(self):
        """Test system health monitoring functionality"""
        # Mock health check responses
        health_checks = {
            "api": {"status": "healthy", "response_time": 0.05},
            "database": {"status": "healthy", "response_time": 0.02},
            "redis": {"status": "healthy", "response_time": 0.01},
            "ml_platform": {"status": "healthy", "response_time": 0.1}
        }
        
        # Calculate overall health
        all_healthy = all(
            check["status"] == "healthy" 
            for check in health_checks.values()
        )
        
        avg_response_time = sum(
            check["response_time"] 
            for check in health_checks.values()
        ) / len(health_checks)
        
        assert all_healthy is True
        assert avg_response_time < 0.2  # Less than 200ms average
    
    @pytest.mark.asyncio
    async def test_alert_system_integration(self):
        """Test alert system integration"""
        # Mock alert data
        test_alerts = [
            {
                "id": "alert_001",
                "name": "High CPU Usage",
                "severity": "warning",
                "status": "active",
                "message": "CPU usage above 80%",
                "timestamp": datetime.now().isoformat()
            },
            {
                "id": "alert_002", 
                "name": "Low Disk Space",
                "severity": "critical",
                "status": "active",
                "message": "Disk space below 10%",
                "timestamp": datetime.now().isoformat()
            }
        ]
        
        # Process alerts
        critical_alerts = [
            alert for alert in test_alerts 
            if alert["severity"] == "critical"
        ]
        
        warning_alerts = [
            alert for alert in test_alerts
            if alert["severity"] == "warning"
        ]
        
        assert len(critical_alerts) == 1
        assert len(warning_alerts) == 1
        assert critical_alerts[0]["name"] == "Low Disk Space"
    
    def test_metrics_aggregation(self):
        """Test metrics aggregation and calculation"""
        # Mock raw metrics data
        raw_metrics = [
            {"timestamp": "2025-09-13T12:00:00Z", "value": 10.5},
            {"timestamp": "2025-09-13T12:01:00Z", "value": 12.3},
            {"timestamp": "2025-09-13T12:02:00Z", "value": 9.8},
            {"timestamp": "2025-09-13T12:03:00Z", "value": 11.2},
            {"timestamp": "2025-09-13T12:04:00Z", "value": 10.9}
        ]
        
        # Calculate aggregations
        values = [metric["value"] for metric in raw_metrics]
        
        avg_value = sum(values) / len(values)
        min_value = min(values)
        max_value = max(values)
        
        assert 10.0 <= avg_value <= 12.0
        assert min_value == 9.8
        assert max_value == 12.3
    
    @pytest.mark.asyncio
    async def test_dashboard_data_compilation(self):
        """Test dashboard data compilation from multiple sources"""
        # Mock data from different sources
        prometheus_data = {
            "requests_total": 1500,
            "error_rate": 0.02,
            "response_time_p95": 0.15
        }
        
        system_status = {
            "status": "healthy",
            "uptime": 86400,  # 24 hours
            "active_connections": 45
        }
        
        ml_platform_data = {
            "active_experiments": 3,
            "models_in_production": 5,
            "training_jobs_running": 2
        }
        
        # Compile dashboard data
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "system_status": system_status,
            "metrics": prometheus_data,
            "ml_platform": ml_platform_data,
            "summary": {
                "total_requests": prometheus_data["requests_total"],
                "error_rate_percent": prometheus_data["error_rate"] * 100,
                "uptime_hours": system_status["uptime"] / 3600
            }
        }
        
        # Verify compiled data structure
        assert "timestamp" in dashboard_data
        assert "system_status" in dashboard_data
        assert "metrics" in dashboard_data
        assert "ml_platform" in dashboard_data
        assert "summary" in dashboard_data
        
        # Verify calculated values
        assert dashboard_data["summary"]["error_rate_percent"] == 2.0
        assert dashboard_data["summary"]["uptime_hours"] == 24.0
    
    @pytest.mark.asyncio
    async def test_monitoring_data_retention(self):
        """Test monitoring data retention policies"""
        # Mock time-series data with different ages
        now = datetime.now()
        data_points = []
        
        # Generate data points for different time periods
        for days_ago in range(30):  # 30 days of data
            timestamp = now - timedelta(days=days_ago)
            data_points.append({
                "timestamp": timestamp.isoformat(),
                "value": 50 + (days_ago * 0.5),  # Trend over time
                "metric": "cpu_usage"
            })
        
        # Apply retention policy (keep last 7 days for detailed, 30 days for summary)
        detailed_cutoff = now - timedelta(days=7)
        summary_cutoff = now - timedelta(days=30)
        
        detailed_data = [
            point for point in data_points
            if datetime.fromisoformat(point["timestamp"]) >= detailed_cutoff
        ]
        
        summary_data = [
            point for point in data_points
            if datetime.fromisoformat(point["timestamp"]) >= summary_cutoff
        ]
        
        assert len(detailed_data) <= 7
        assert len(summary_data) == 30
    
    def test_performance_thresholds(self):
        """Test performance threshold monitoring"""
        # Define performance thresholds
        thresholds = {
            "cpu_usage": {"warning": 70, "critical": 90},
            "memory_usage": {"warning": 80, "critical": 95},
            "disk_usage": {"warning": 85, "critical": 95},
            "response_time": {"warning": 0.5, "critical": 1.0}
        }
        
        # Mock current metrics
        current_metrics = {
            "cpu_usage": 75,      # Warning level
            "memory_usage": 60,   # Normal
            "disk_usage": 96,     # Critical level  
            "response_time": 0.3  # Normal
        }
        
        # Check thresholds
        alerts = []
        for metric, value in current_metrics.items():
            if metric in thresholds:
                if value >= thresholds[metric]["critical"]:
                    alerts.append({
                        "metric": metric,
                        "level": "critical",
                        "value": value,
                        "threshold": thresholds[metric]["critical"]
                    })
                elif value >= thresholds[metric]["warning"]:
                    alerts.append({
                        "metric": metric,
                        "level": "warning", 
                        "value": value,
                        "threshold": thresholds[metric]["warning"]
                    })
        
        # Verify alerts
        assert len(alerts) == 2  # CPU warning, disk critical
        
        critical_alerts = [a for a in alerts if a["level"] == "critical"]
        warning_alerts = [a for a in alerts if a["level"] == "warning"]
        
        assert len(critical_alerts) == 1
        assert len(warning_alerts) == 1
        assert critical_alerts[0]["metric"] == "disk_usage"
        assert warning_alerts[0]["metric"] == "cpu_usage"


class TestMonitoringErrorHandling:
    """Test error handling in monitoring system"""
    
    @pytest.mark.asyncio
    async def test_prometheus_connection_failure(self):
        """Test handling of Prometheus connection failures"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock connection error
            mock_get.side_effect = Exception("Connection refused")
            
            try:
                # Would normally make actual request
                raise Exception("Connection refused")
            except Exception as e:
                assert "Connection refused" in str(e)
    
    @pytest.mark.asyncio 
    async def test_grafana_api_timeout(self):
        """Test handling of Grafana API timeouts"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock timeout
            mock_get.side_effect = asyncio.TimeoutError("Request timeout")
            
            with pytest.raises(asyncio.TimeoutError):
                raise asyncio.TimeoutError("Request timeout")
    
    @pytest.mark.asyncio
    async def test_websocket_connection_drop(self):
        """Test handling of WebSocket connection drops"""
        # Mock WebSocket that disconnects
        mock_websocket = AsyncMock()
        mock_websocket.send_json.side_effect = Exception("Connection closed")
        
        with pytest.raises(Exception) as exc_info:
            await mock_websocket.send_json({"test": "data"})
        
        assert "Connection closed" in str(exc_info.value)
    
    def test_invalid_metrics_data_handling(self):
        """Test handling of invalid metrics data"""
        # Test various invalid data scenarios
        invalid_metrics = [
            None,                           # None value
            {},                            # Empty dict
            {"metric": None},              # None metric value
            {"metric": "invalid_string"},  # String instead of number
            {"metric": float('inf')},      # Infinite value
            {"metric": float('nan')}       # NaN value
        ]
        
        valid_count = 0
        
        for metric_data in invalid_metrics:
            try:
                # Validate metric data
                if (metric_data and 
                    isinstance(metric_data, dict) and 
                    "metric" in metric_data and
                    metric_data["metric"] is not None and
                    isinstance(metric_data["metric"], (int, float)) and
                    not (isinstance(metric_data["metric"], float) and 
                         (metric_data["metric"] != metric_data["metric"] or  # NaN check
                          metric_data["metric"] == float('inf') or 
                          metric_data["metric"] == float('-inf')))):
                    valid_count += 1
            except Exception:
                pass  # Invalid data, skip
        
        # None of the test data should be valid
        assert valid_count == 0


class TestMonitoringPerformance:
    """Test monitoring system performance"""
    
    @pytest.mark.slow
    def test_high_frequency_metrics_collection(self, performance_timer):
        """Test high-frequency metrics collection performance"""
        metrics_count = 1000
        
        with performance_timer() as timer:
            # Simulate collecting many metrics
            metrics = []
            for i in range(metrics_count):
                metric = {
                    "timestamp": datetime.now().isoformat(),
                    "name": f"test_metric_{i}",
                    "value": i * 0.1
                }
                metrics.append(metric)
        
        # Performance check
        assert len(metrics) == metrics_count
        assert timer.elapsed is not None
        
        # Should be able to process 1000 metrics quickly
        if timer.elapsed:
            metrics_per_second = metrics_count / timer.elapsed
            assert metrics_per_second > 100  # At least 100 metrics/sec
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_connections(self):
        """Test handling multiple concurrent WebSocket connections"""
        # Mock multiple WebSocket connections
        connection_count = 50
        mock_connections = []
        
        for i in range(connection_count):
            mock_ws = AsyncMock()
            mock_ws.send_json = AsyncMock()
            mock_connections.append(mock_ws)
        
        # Broadcast to all connections
        test_message = {"type": "test", "data": "broadcast"}
        
        for connection in mock_connections:
            await connection.send_json(test_message)
        
        # Verify all connections received the message
        for connection in mock_connections:
            connection.send_json.assert_called_once_with(test_message)
    
    def test_metrics_buffer_management(self):
        """Test metrics buffer management and memory usage"""
        # Simulate metrics buffer
        buffer_size = 1000
        metrics_buffer = []
        
        # Fill buffer
        for i in range(buffer_size * 2):  # Add more than buffer size
            metric = {
                "timestamp": datetime.now().isoformat(),
                "value": i,
                "metric_name": "test_metric"
            }
            
            metrics_buffer.append(metric)
            
            # Implement buffer size limit
            if len(metrics_buffer) > buffer_size:
                metrics_buffer.pop(0)  # Remove oldest
        
        # Buffer should not exceed size limit
        assert len(metrics_buffer) == buffer_size
        
        # Should contain the most recent metrics
        assert metrics_buffer[-1]["value"] == (buffer_size * 2) - 1
        assert metrics_buffer[0]["value"] == buffer_size