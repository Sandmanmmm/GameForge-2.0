#!/usr/bin/env python3
"""
Test script for monitoring dashboard integration.

Tests all monitoring endpoints and validates data format for frontend.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

async def test_endpoint(session: aiohttp.ClientSession, endpoint: str, method: str = "GET", 
                       data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Test a single endpoint"""
    url = f"{API_BASE}{endpoint}"
    
    try:
        if method == "GET":
            async with session.get(url) as response:
                result = {
                    "endpoint": endpoint,
                    "status": response.status,
                    "success": response.status < 400,
                    "response": None,
                    "error": None
                }
                
                if response.status < 400:
                    try:
                        result["response"] = await response.json()
                    except:
                        result["response"] = await response.text()
                else:
                    result["error"] = await response.text()
                
                return result
        
        elif method == "POST":
            async with session.post(url, json=data) as response:
                result = {
                    "endpoint": endpoint,
                    "status": response.status,
                    "success": response.status < 400,
                    "response": None,
                    "error": None
                }
                
                if response.status < 400:
                    try:
                        result["response"] = await response.json()
                    except:
                        result["response"] = await response.text()
                else:
                    result["error"] = await response.text()
                
                return result
    
    except Exception as e:
        return {
            "endpoint": endpoint,
            "status": 0,
            "success": False,
            "response": None,
            "error": str(e)
        }


async def run_monitoring_tests():
    """Run comprehensive monitoring integration tests"""
    
    print("🧪 Starting Monitoring Dashboard Integration Tests")
    print("=" * 60)
    
    test_results = []
    
    async with aiohttp.ClientSession() as session:
        
        # Test 1: Health Check
        print("\n1. Testing health check endpoint...")
        result = await test_endpoint(session, "/monitoring/health")
        test_results.append(result)
        print(f"   Status: {result['status']} - {'✅ PASS' if result['success'] else '❌ FAIL'}")
        
        # Test 2: System Status
        print("\n2. Testing system status endpoint...")
        result = await test_endpoint(session, "/monitoring/status")
        test_results.append(result)
        print(f"   Status: {result['status']} - {'✅ PASS' if result['success'] else '❌ FAIL'}")
        if result['success'] and result['response']:
            status_data = result['response']
            print(f"   System Status: {status_data.get('status', 'unknown')}")
            print(f"   Active Models: {status_data.get('active_models', 0)}")
            print(f"   Total Experiments: {status_data.get('total_experiments', 0)}")
        
        # Test 3: Instant Metrics
        print("\n3. Testing instant metrics endpoint...")
        result = await test_endpoint(session, "/monitoring/metrics/instant")
        test_results.append(result)
        print(f"   Status: {result['status']} - {'✅ PASS' if result['success'] else '❌ FAIL'}")
        if result['success'] and result['response']:
            metrics = result['response'].get('metrics', {})
            print(f"   Available metrics: {len(metrics)} entries")
            for key, value in list(metrics.items())[:3]:
                print(f"   - {key}: {value}")
        
        # Test 4: Dashboard Data
        print("\n4. Testing dashboard data endpoint...")
        result = await test_endpoint(session, "/monitoring/dashboard-data")
        test_results.append(result)
        print(f"   Status: {result['status']} - {'✅ PASS' if result['success'] else '❌ FAIL'}")
        if result['success'] and result['response']:
            data = result['response']
            print(f"   Quick Stats Available: {'quick_stats' in data}")
            if 'quick_stats' in data:
                stats = data['quick_stats']
                print(f"   - Models Total: {stats.get('models_total', 0)}")
                print(f"   - RPS: {stats.get('requests_per_second', 0)}")
                print(f"   - Error Rate: {stats.get('error_rate_percent', 0)}%")
        
        # Test 5: Prometheus Metrics Query
        print("\n5. Testing Prometheus metrics query...")
        result = await test_endpoint(session, "/monitoring/metrics/prometheus?query=up")
        test_results.append(result)
        print(f"   Status: {result['status']} - {'✅ PASS' if result['success'] else '❌ FAIL'}")
        if not result['success'] and result['status'] == 503:
            print("   Note: Expected if Prometheus not running")
        
        # Test 6: Grafana Dashboards
        print("\n6. Testing Grafana dashboards endpoint...")
        result = await test_endpoint(session, "/monitoring/dashboards")
        test_results.append(result)
        print(f"   Status: {result['status']} - {'✅ PASS' if result['success'] else '❌ FAIL'}")
        if not result['success'] and result['status'] == 503:
            print("   Note: Expected if Grafana not configured")
        
        # Test 7: Alerts
        print("\n7. Testing alerts endpoint...")
        result = await test_endpoint(session, "/monitoring/alerts")
        test_results.append(result)
        print(f"   Status: {result['status']} - {'✅ PASS' if result['success'] else '❌ FAIL'}")
        if result['success']:
            alerts = result['response'] or []
            print(f"   Active alerts: {len(alerts)}")
        
        # Test 8: ML Platform Integration
        print("\n8. Testing ML platform experiment tracking...")
        result = await test_endpoint(session, "/ml-platform/experiments")
        test_results.append(result)
        print(f"   Status: {result['status']} - {'✅ PASS' if result['success'] else '❌ FAIL'}")
        
        # Test 9: AI Job Traceability
        print("\n9. Testing AI job traceability...")
        result = await test_endpoint(session, "/ml-platform/ai-jobs")
        test_results.append(result)
        print(f"   Status: {result['status']} - {'✅ PASS' if result['success'] else '❌ FAIL'}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in test_results if r['success'])
    total = len(test_results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    # Detailed failures
    failures = [r for r in test_results if not r['success']]
    if failures:
        print(f"\n❌ FAILED TESTS ({len(failures)}):")
        for failure in failures:
            print(f"   {failure['endpoint']}: {failure['status']} - {failure['error']}")
    
    # Frontend integration status
    print(f"\n🎯 FRONTEND INTEGRATION STATUS:")
    
    monitoring_endpoints = [
        "/monitoring/health",
        "/monitoring/status", 
        "/monitoring/dashboard-data",
        "/monitoring/metrics/instant"
    ]
    
    monitoring_success = all(
        r['success'] for r in test_results 
        if any(r['endpoint'] == ep for ep in monitoring_endpoints)
    )
    
    ml_platform_endpoints = [
        "/ml-platform/experiments",
        "/ml-platform/ai-jobs"
    ]
    
    ml_platform_success = all(
        r['success'] for r in test_results 
        if any(r['endpoint'] == ep for ep in ml_platform_endpoints)
    )
    
    print(f"   Monitoring Dashboards: {'✅ READY' if monitoring_success else '❌ ISSUES'}")
    print(f"   ML Platform Integration: {'✅ READY' if ml_platform_success else '❌ ISSUES'}")
    print(f"   AI Job Traceability: {'✅ READY' if ml_platform_success else '❌ ISSUES'}")
    
    if monitoring_success and ml_platform_success:
        print(f"\n🎉 ALL FRONTEND INTEGRATION REQUIREMENTS MET!")
        print(f"   - Monitoring dashboards exposed to frontend ✅")
        print(f"   - Experiment results accessible via API ✅") 
        print(f"   - AI job traceability implemented ✅")
        print(f"   - Real-time metrics available ✅")
    else:
        print(f"\n⚠️  Some integration requirements need attention")
    
    return test_results


async def test_websocket_monitoring():
    """Test WebSocket endpoints for real-time monitoring"""
    
    print(f"\n🔌 Testing WebSocket Monitoring...")
    
    try:
        import websockets
        
        # Test metrics WebSocket
        uri = f"ws://localhost:8000/api/v1/monitoring/ws/metrics"
        
        async with websockets.connect(uri) as websocket:
            print("   Metrics WebSocket connected ✅")
            
            # Wait for a message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(message)
                print(f"   Received metrics update: {data.get('type', 'unknown')}")
                print("   Real-time metrics working ✅")
            except asyncio.TimeoutError:
                print("   No message received in 10s (expected if no data)")
        
    except ImportError:
        print("   WebSocket testing requires 'websockets' package")
        print("   Install with: pip install websockets")
    except Exception as e:
        print(f"   WebSocket test failed: {e}")
        print("   Note: Expected if server not running")


if __name__ == "__main__":
    print("🚀 GameForge Monitoring Integration Test Suite")
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now()}")
    
    try:
        # Run HTTP endpoint tests
        results = asyncio.run(run_monitoring_tests())
        
        # Run WebSocket tests
        asyncio.run(test_websocket_monitoring())
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n💥 Test suite failed: {e}")
    
    print(f"\nCompleted at: {datetime.now()}")