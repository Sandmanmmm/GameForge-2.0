#!/usr/bin/env python3
"""
GameForge RTX 4090 Deployment Verification Tool
Tests all possible connection methods and provides status
"""

import requests
import time
import json
from datetime import datetime

def test_deployment_status():
    """Comprehensive deployment status check."""
    
    print("🔍 GAMEFORGE RTX 4090 DEPLOYMENT STATUS")
    print("=" * 60)
    print(f"⏰ Check time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test endpoints
    endpoints = [
        {
            "name": "Cloudflare Tunnel (Primary)",
            "url": "https://moisture-simply-arab-fires.trycloudflare.com/health",
            "timeout": 10
        },
        {
            "name": "Direct IP Port 8000",
            "url": "http://172.97.240.138:8000/health", 
            "timeout": 5
        },
        {
            "name": "Direct IP Port 8080",
            "url": "http://172.97.240.138:8080/health",
            "timeout": 5
        },
        {
            "name": "Direct IP Port 6006 (TensorBoard)",
            "url": "http://172.97.240.138:6006",
            "timeout": 5
        }
    ]
    
    working_endpoints = []
    
    for endpoint in endpoints:
        print(f"\n🔗 Testing: {endpoint['name']}")
        print(f"   URL: {endpoint['url']}")
        
        try:
            response = requests.get(endpoint['url'], timeout=endpoint['timeout'])
            
            if response.status_code == 200:
                print(f"   ✅ SUCCESS! Status: {response.status_code}")
                
                try:
                    data = response.json()
                    print(f"   📊 Server: {data.get('server', 'Unknown')}")
                    print(f"   🎮 GPU: {data.get('gpu', {}).get('name', 'Unknown')}")
                    print(f"   🔥 CUDA: {data.get('gpu', {}).get('available', False)}")
                    print(f"   🔧 Instance: {data.get('instance_id', 'Unknown')}")
                    
                    working_endpoints.append({
                        "endpoint": endpoint,
                        "data": data
                    })
                    
                except json.JSONDecodeError:
                    print(f"   ⚠️ Non-JSON response: {response.text[:100]}")
                    
            else:
                print(f"   ❌ HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"   ⏳ Timeout ({endpoint['timeout']}s)")
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Connection failed")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Summary
    print(f"\n📊 DEPLOYMENT SUMMARY:")
    print("=" * 40)
    
    if working_endpoints:
        print(f"✅ DEPLOYMENT SUCCESSFUL!")
        print(f"   Working endpoints: {len(working_endpoints)}")
        
        for i, result in enumerate(working_endpoints, 1):
            endpoint = result['endpoint']
            data = result['data']
            print(f"\n{i}. {endpoint['name']}")
            print(f"   🔗 {endpoint['url']}")
            print(f"   🎮 GPU: {data.get('gpu', {}).get('name', 'Unknown')}")
            print(f"   🔥 CUDA: {data.get('gpu', {}).get('available', False)}")
        
        print(f"\n🎯 VS CODE INTEGRATION READY!")
        print(f"   Use this endpoint in magic commands:")
        print(f"   {working_endpoints[0]['endpoint']['url']}")
        
    else:
        print(f"❌ NO SERVERS RESPONDING")
        print(f"   Server needs to be started manually")
        print(f"\n💡 SOLUTIONS:")
        print(f"   1. Use Vast.ai web interface:")
        print(f"      https://console.vast.ai/instances/")
        print(f"   2. In terminal run: python3 /workspace/gameforge_server.py 8000 &")
        print(f"   3. Wait 30 seconds and run this script again")
    
    return len(working_endpoints) > 0

def monitor_deployment(duration=60, interval=10):
    """Monitor deployment attempts for a specified duration."""
    
    print(f"\n🔄 MONITORING DEPLOYMENT...")
    print(f"   Duration: {duration} seconds")
    print(f"   Check interval: {interval} seconds")
    
    start_time = time.time()
    attempts = 0
    
    while time.time() - start_time < duration:
        attempts += 1
        print(f"\n--- Attempt {attempts} ---")
        
        if test_deployment_status():
            print(f"\n🎉 DEPLOYMENT DETECTED!")
            return True
        
        print(f"\n⏳ Waiting {interval} seconds before next check...")
        time.sleep(interval)
    
    print(f"\n⏰ Monitoring completed after {attempts} attempts")
    return False

if __name__ == "__main__":
    print("🚀 GameForge RTX 4090 Deployment Verification")
    
    # Initial status check
    if test_deployment_status():
        print(f"\n🎉 Deployment is working! Ready for VS Code integration.")
    else:
        print(f"\n🔄 Starting deployment monitoring...")
        
        # Ask user if they want to monitor
        monitor = input("Monitor for deployment? (y/n): ").lower().startswith('y')
        
        if monitor:
            success = monitor_deployment(duration=120, interval=15)
            
            if success:
                print(f"\n🎊 DEPLOYMENT SUCCESSFUL!")
            else:
                print(f"\n💡 Try starting server manually and run this script again")
        else:
            print(f"\n💡 Run this script again after starting the server manually")
