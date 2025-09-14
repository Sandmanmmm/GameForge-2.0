"""
Monitoring Dashboard API for Frontend Integration

Provides real-time monitoring data, Grafana dashboard proxying,
and Prometheus metrics exposition for GameForge frontend.
"""

import asyncio
import json
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# Configuration
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://localhost:3000")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY", "")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except:
                # Remove stale connections
                self.active_connections.remove(connection)


manager = ConnectionManager()


# ============================================================================
# Pydantic Models
# ============================================================================

class MetricValue(BaseModel):
    """Single metric value with timestamp"""
    timestamp: datetime
    value: float


class TimeSeriesMetric(BaseModel):
    """Time series metric data"""
    metric_name: str
    labels: Dict[str, str]
    values: List[MetricValue]


class DashboardInfo(BaseModel):
    """Grafana dashboard information"""
    uid: str
    title: str
    url: str
    tags: List[str]
    folder: str


class AlertInfo(BaseModel):
    """Alert information"""
    id: str
    name: str
    state: str
    severity: str
    message: str
    started_at: datetime
    labels: Dict[str, str]


class SystemStatus(BaseModel):
    """Overall system status"""
    status: str
    uptime: float
    active_models: int
    total_experiments: int
    alerts_count: int
    last_updated: datetime


# ============================================================================
# Prometheus Integration
# ============================================================================

@router.get("/metrics/prometheus", response_model=List[TimeSeriesMetric])
async def get_prometheus_metrics(
    query: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    step: str = "1m"
):
    """Query Prometheus metrics"""
    
    if not start:
        start = datetime.utcnow() - timedelta(hours=1)
    if not end:
        end = datetime.utcnow()
    
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "query": query,
                "start": start.isoformat() + "Z",
                "end": end.isoformat() + "Z",
                "step": step
            }
            
            async with session.get(
                f"{PROMETHEUS_URL}/api/v1/query_range",
                params=params
            ) as response:
                
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"Prometheus query failed: {await response.text()}"
                    )
                
                data = await response.json()
                
                if data["status"] != "success":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Prometheus query error: {data.get('error', 'Unknown error')}"
                    )
                
                # Convert to our format
                result = []
                for series in data["data"]["result"]:
                    metric_name = series["metric"].get("__name__", "unknown")
                    labels = {k: v for k, v in series["metric"].items() if k != "__name__"}
                    
                    values = []
                    for timestamp, value in series["values"]:
                        values.append(MetricValue(
                            timestamp=datetime.fromtimestamp(float(timestamp)),
                            value=float(value)
                        ))
                    
                    result.append(TimeSeriesMetric(
                        metric_name=metric_name,
                        labels=labels,
                        values=values
                    ))
                
                return result
                
    except aiohttp.ClientError as e:
        logger.error(f"Failed to query Prometheus: {e}")
        raise HTTPException(
            status_code=503,
            detail="Prometheus service unavailable"
        )
    except Exception as e:
        logger.error(f"Error querying Prometheus: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/instant")
async def get_instant_metrics():
    """Get instant metric values for dashboard"""
    
    metrics_queries = {
        "models_total": "gameforge_models_total",
        "models_production": "gameforge_models_production",
        "experiments_active": "gameforge_experiments_active",
        "requests_per_second": "rate(gameforge_ai_requests_total[1m])",
        "error_rate": "rate(gameforge_ai_errors_total[1m])",
        "latency_p95": "histogram_quantile(0.95, gameforge_ai_latency_seconds)",
        "memory_usage": "gameforge_memory_usage_bytes",
        "cpu_usage": "gameforge_cpu_usage_percent"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            results = {}
            
            for metric_name, query in metrics_queries.items():
                try:
                    async with session.get(
                        f"{PROMETHEUS_URL}/api/v1/query",
                        params={"query": query}
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            if data["status"] == "success" and data["data"]["result"]:
                                value = float(data["data"]["result"][0]["value"][1])
                                results[metric_name] = value
                            else:
                                results[metric_name] = 0.0
                        else:
                            results[metric_name] = 0.0
                            
                except Exception as e:
                    logger.warning(f"Failed to get metric {metric_name}: {e}")
                    results[metric_name] = 0.0
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": results
            }
            
    except Exception as e:
        logger.error(f"Failed to get instant metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Grafana Integration
# ============================================================================

@router.get("/dashboards", response_model=List[DashboardInfo])
async def list_grafana_dashboards():
    """List available Grafana dashboards"""
    
    if not GRAFANA_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Grafana integration not configured"
        )
    
    try:
        headers = {
            "Authorization": f"Bearer {GRAFANA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GRAFANA_URL}/api/search",
                headers=headers,
                params={"type": "dash-db"}
            ) as response:
                
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to fetch Grafana dashboards"
                    )
                
                dashboards_data = await response.json()
                
                dashboards = []
                for dashboard in dashboards_data:
                    dashboards.append(DashboardInfo(
                        uid=dashboard["uid"],
                        title=dashboard["title"],
                        url=f"{GRAFANA_URL}/d/{dashboard['uid']}/{dashboard['uri'].replace('db/', '')}",
                        tags=dashboard.get("tags", []),
                        folder=dashboard.get("folderTitle", "General")
                    ))
                
                return dashboards
                
    except aiohttp.ClientError as e:
        logger.error(f"Failed to connect to Grafana: {e}")
        raise HTTPException(
            status_code=503,
            detail="Grafana service unavailable"
        )
    except Exception as e:
        logger.error(f"Error fetching dashboards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboards/{dashboard_uid}/embed")
async def get_dashboard_embed_url(dashboard_uid: str):
    """Get Grafana dashboard embed URL"""
    
    embed_url = f"{GRAFANA_URL}/d-solo/{dashboard_uid}"
    
    return {
        "embed_url": embed_url,
        "iframe_url": f"{embed_url}?orgId=1&theme=light&panelId=1",
        "full_url": f"{GRAFANA_URL}/d/{dashboard_uid}"
    }


# ============================================================================
# Alerts Integration
# ============================================================================

@router.get("/alerts", response_model=List[AlertInfo])
async def get_active_alerts():
    """Get active alerts from Grafana"""
    
    if not GRAFANA_API_KEY:
        return []  # Return empty if not configured
    
    try:
        headers = {
            "Authorization": f"Bearer {GRAFANA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GRAFANA_URL}/api/alerts",
                headers=headers,
                params={"state": "alerting"}
            ) as response:
                
                if response.status != 200:
                    logger.warning(f"Failed to fetch alerts: {response.status}")
                    return []
                
                alerts_data = await response.json()
                
                alerts = []
                for alert in alerts_data:
                    alerts.append(AlertInfo(
                        id=str(alert["id"]),
                        name=alert["name"],
                        state=alert["state"],
                        severity=alert.get("executionError", "medium"),
                        message=alert.get("message", ""),
                        started_at=datetime.fromisoformat(
                            alert["newStateDate"].replace("Z", "+00:00")
                        ),
                        labels=alert.get("evalData", {}).get("evalMatches", [{}])[0].get("tags", {})
                    ))
                
                return alerts
                
    except Exception as e:
        logger.warning(f"Failed to get alerts: {e}")
        return []


# ============================================================================
# System Status
# ============================================================================

@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get overall system status"""
    
    try:
        # Get metrics from Prometheus
        metrics = await get_instant_metrics()
        metric_values = metrics["metrics"]
        
        # Determine overall status
        error_rate = metric_values.get("error_rate", 0)
        cpu_usage = metric_values.get("cpu_usage", 0)
        
        if error_rate > 0.1 or cpu_usage > 90:
            status = "critical"
        elif error_rate > 0.05 or cpu_usage > 80:
            status = "warning"
        else:
            status = "healthy"
        
        # Get alerts count
        alerts = await get_active_alerts()
        alerts_count = len(alerts)
        
        return SystemStatus(
            status=status,
            uptime=3600.0,  # Mock uptime
            active_models=int(metric_values.get("models_production", 0)),
            total_experiments=int(metric_values.get("experiments_active", 0)),
            alerts_count=alerts_count,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return SystemStatus(
            status="unknown",
            uptime=0.0,
            active_models=0,
            total_experiments=0,
            alerts_count=0,
            last_updated=datetime.utcnow()
        )


# ============================================================================
# Real-time WebSocket Endpoints
# ============================================================================

@router.websocket("/ws/metrics")
async def metrics_websocket(websocket: WebSocket):
    """WebSocket for real-time metrics updates"""
    
    await manager.connect(websocket)
    
    try:
        while True:
            # Send metrics every 5 seconds
            try:
                metrics = await get_instant_metrics()
                await websocket.send_json({
                    "type": "metrics_update",
                    "data": metrics
                })
            except Exception as e:
                logger.error(f"Failed to send metrics: {e}")
            
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@router.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    """WebSocket for real-time alert updates"""
    
    await manager.connect(websocket)
    
    try:
        while True:
            try:
                alerts = await get_active_alerts()
                await websocket.send_json({
                    "type": "alerts_update",
                    "data": [alert.dict() for alert in alerts]
                })
            except Exception as e:
                logger.error(f"Failed to send alerts: {e}")
            
            await asyncio.sleep(10)  # Check alerts every 10 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ============================================================================
# Dashboard Data for Frontend
# ============================================================================

@router.get("/dashboard-data")
async def get_dashboard_data():
    """Get combined dashboard data for frontend"""
    
    try:
        # Get all data in parallel
        metrics_task = get_instant_metrics()
        status_task = get_system_status()
        alerts_task = get_active_alerts()
        
        metrics, status, alerts = await asyncio.gather(
            metrics_task, status_task, alerts_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(metrics, Exception):
            logger.error(f"Failed to get metrics: {metrics}")
            metrics = {"timestamp": datetime.utcnow().isoformat(), "metrics": {}}
        
        if isinstance(status, Exception):
            logger.error(f"Failed to get status: {status}")
            status = SystemStatus(
                status="unknown", uptime=0.0, active_models=0,
                total_experiments=0, alerts_count=0, last_updated=datetime.utcnow()
            )
        
        if isinstance(alerts, Exception):
            logger.error(f"Failed to get alerts: {alerts}")
            alerts = []
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system_status": status.dict(),
            "metrics": metrics,
            "alerts": [alert.dict() for alert in alerts],
            "quick_stats": {
                "models_total": metrics["metrics"].get("models_total", 0),
                "requests_per_second": round(metrics["metrics"].get("requests_per_second", 0), 2),
                "error_rate_percent": round(metrics["metrics"].get("error_rate", 0) * 100, 2),
                "latency_p95_ms": round(metrics["metrics"].get("latency_p95", 0) * 1000, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check for monitoring systems"""
    
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check Prometheus
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{PROMETHEUS_URL}/-/healthy", timeout=5) as response:
                health["services"]["prometheus"] = "healthy" if response.status == 200 else "unhealthy"
    except:
        health["services"]["prometheus"] = "unreachable"
    
    # Check Grafana
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{GRAFANA_URL}/api/health", timeout=5) as response:
                health["services"]["grafana"] = "healthy" if response.status == 200 else "unhealthy"
    except:
        health["services"]["grafana"] = "unreachable"
    
    # Overall status
    if any(status != "healthy" for status in health["services"].values()):
        health["status"] = "degraded"
    
    return health