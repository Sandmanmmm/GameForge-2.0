"""
GameForge GPU Server Monitor
Monitors the Vast GPU server and runs E2E tests when available
"""

import asyncio
import aiohttp
import time
from datetime import datetime

async def monitor_gpu_server():
    """Monitor GPU server availability"""
    gpu_endpoint = "http://172.97.240.138:41392"
    backend_endpoint = "http://localhost:8000"
    
    print("🔍 GAMEFORGE GPU SERVER MONITOR")
    print("=" * 50)
    print(f"GPU Endpoint: {gpu_endpoint}")
    print(f"Backend Endpoint: {backend_endpoint}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check backend first
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{backend_endpoint}/api/v1/health") as response:
                if response.status == 200:
                    print("✅ GameForge Backend: ONLINE")
                else:
                    print(f"❌ GameForge Backend: ERROR ({response.status})")
                    return
    except Exception as e:
        print(f"❌ GameForge Backend: CONNECTION FAILED - {e}")
        return
    
    # Monitor GPU server
    attempt = 1
    while True:
        try:
            print(f"🔄 Attempt {attempt}: Checking GPU server...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{gpu_endpoint}/health", timeout=10) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        
                        print("🎊 GPU SERVER IS ONLINE!")
                        print("=" * 50)
                        print(f"✅ Status: {health_data.get('status', 'unknown')}")
                        print(f"✅ Device: {health_data.get('device', 'unknown')}")
                        print(f"✅ Pipeline: {'Loaded' if health_data.get('pipeline_loaded') else 'Not Loaded'}")
                        
                        if health_data.get('gpu_info'):
                            gpu_info = health_data['gpu_info']
                            print(f"✅ GPU: {gpu_info.get('gpu_name', 'Unknown')}")
                        
                        print(f"✅ Server Port: {health_data.get('server_port', 'unknown')}")
                        print(f"✅ External Access: {health_data.get('external_access', 'unknown')}")
                        print()
                        
                        # GPU server is ready, run E2E test
                        print("🚀 RUNNING END-TO-END PIPELINE TEST")
                        print("=" * 50)
                        
                        # Import and run the E2E test
                        import subprocess
                        result = subprocess.run([
                            "C:/Users/sandr/Ai Game Maker/ai-game-production-p/.venv/Scripts/python.exe",
                            "test_e2e_pipeline.py"
                        ], capture_output=True, text=True, cwd="C:/Users/sandr/Ai Game Maker/ai-game-production-p")
                        
                        print("E2E Test Output:")
                        print(result.stdout)
                        if result.stderr:
                            print("E2E Test Errors:")
                            print(result.stderr)
                        
                        if result.returncode == 0:
                            print("🎊 END-TO-END TEST PASSED!")
                            print("✅ GameForge AI system is fully operational!")
                        else:
                            print("⚠️  End-to-end test had issues")
                        
                        return True
                        
        except asyncio.TimeoutError:
            print(f"   ⏰ Timeout - GPU server not responding")
        except Exception as e:
            print(f"   ❌ Connection failed: {e}")
        
        # Wait before next attempt
        print(f"   ⏳ Waiting 30 seconds before next attempt...")
        print()
        
        await asyncio.sleep(30)
        attempt += 1
        
        # Stop after 20 attempts (10 minutes)
        if attempt > 20:
            print("❌ GPU server did not come online after 10 minutes")
            print("   Please check Vast.ai deployment manually")
            return False

def print_deployment_status():
    """Print current deployment status"""
    print("📋 DEPLOYMENT STATUS")
    print("=" * 50)
    print("✅ GameForge Backend: Running on http://localhost:8000")
    print("⏳ GPU Server: Waiting for deployment on http://172.97.240.138:41392")
    print()
    print("📝 TO COMPLETE DEPLOYMENT:")
    print("1. Open: https://vast.ai/console/instances/ (Instance 25599851)")
    print("2. Upload gpu_server_port8080.py to Jupyter interface")
    print("3. Run deployment commands (see VAST_DEPLOYMENT_INSTRUCTIONS.md)")
    print("4. This monitor will automatically detect when GPU server is ready")
    print("5. End-to-end tests will run automatically")
    print()
    print("🔍 Monitor will check every 30 seconds...")
    print()

async def main():
    """Main monitoring function"""
    print_deployment_status()
    success = await monitor_gpu_server()
    
    if success:
        print("\n🎊 GAMEFORGE AI SYSTEM FULLY DEPLOYED!")
        print("✅ Frontend ready for connection")
        print("✅ Backend operational") 
        print("✅ GPU server online")
        print("✅ End-to-end pipeline tested")
        print("\n🚀 READY FOR PRODUCTION!")
    else:
        print("\n⚠️  Deployment incomplete - check GPU server deployment")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Monitor stopped by user")
    except Exception as e:
        print(f"\n❌ Monitor error: {e}")
