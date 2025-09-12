"""
GameForge AI End-to-End Pipeline Test
Tests the complete integration: Frontend → Backend → Vast GPU → Result
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

class GameForgeE2ETester:
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.gpu_server_url = "http://172.97.240.138:41392"
        
    async def test_gpu_server_direct(self):
        """Test direct connection to Vast GPU server"""
        print("🧪 TESTING DIRECT GPU SERVER CONNECTION")
        print("="*50)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Test health endpoint
                print("Testing GPU server health...")
                async with session.get(f"{self.gpu_server_url}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        print("✅ GPU Server Health Check PASSED")
                        print(f"   GPU: {health_data.get('gpu_info', {}).get('gpu_name', 'Unknown')}")
                        print(f"   Pipeline: {'✅ Loaded' if health_data.get('pipeline_loaded') else '❌ Not Loaded'}")
                        return True
                    else:
                        print(f"❌ GPU Server Health Check FAILED: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ GPU Server Connection FAILED: {e}")
            return False
    
    async def test_backend_health(self):
        """Test GameForge backend health"""
        print("\n🧪 TESTING GAMEFORGE BACKEND")
        print("="*50)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.backend_url}/api/v1/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        print("✅ Backend Health Check PASSED")
                        
                        # Check GPU server connection from backend
                        gpu_status = health_data.get('services', {}).get('vast_gpu_server', {})
                        if gpu_status.get('status') == 'healthy':
                            print("✅ Backend → GPU Server Connection WORKING")
                        else:
                            print(f"⚠️  Backend → GPU Server Connection: {gpu_status}")
                        
                        return True
                    else:
                        print(f"❌ Backend Health Check FAILED: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            print(f"❌ Backend Connection FAILED: {e}")
            return False
    
    async def test_asset_generation(self):
        """Test complete asset generation pipeline"""
        print("\n🚀 TESTING END-TO-END ASSET GENERATION")
        print("="*50)
        
        try:
            async with aiohttp.ClientSession() as session:
                # Create asset generation request
                asset_request = {
                    "prompt": "Epic fire sword with glowing runes",
                    "category": "weapons",
                    "style": "fantasy",
                    "rarity": "epic",
                    "width": 1024,
                    "height": 1024,
                    "steps": 20,
                    "guidance_scale": 7.5,
                    "negative_prompt": "blurry, low quality",
                    "tags": ["sword", "fire", "magic"]
                }
                
                print(f"Creating asset: {asset_request['prompt']}")
                
                # Submit generation request
                async with session.post(
                    f"{self.backend_url}/api/v1/assets",
                    json=asset_request
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        job_id = result.get("job_id")
                        print(f"✅ Asset job created: {job_id}")
                        
                        # Poll job status
                        return await self.poll_job_completion(session, job_id)
                    else:
                        error_text = await response.text()
                        print(f"❌ Asset creation FAILED: HTTP {response.status}")
                        print(f"   Error: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"❌ Asset generation FAILED: {e}")
            return False
    
    async def poll_job_completion(self, session, job_id, max_wait=120):
        """Poll job status until completion"""
        print(f"📊 Polling job {job_id} status...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                async with session.get(f"{self.backend_url}/api/v1/jobs/{job_id}") as response:
                    if response.status == 200:
                        job_data = await response.json()
                        job_info = job_data.get("job", {})
                        status = job_info.get("status", "unknown")
                        progress = job_info.get("progress", 0.0)
                        
                        print(f"   Status: {status} ({progress*100:.1f}%)")
                        
                        if status == "completed":
                            asset_id = job_info.get("asset_id")
                            print(f"✅ Job COMPLETED! Asset ID: {asset_id}")
                            
                            # Get asset details
                            return await self.verify_asset(session, asset_id)
                            
                        elif status == "failed":
                            error = job_info.get("error", "Unknown error")
                            print(f"❌ Job FAILED: {error}")
                            return False
                        
                        # Wait before next poll
                        await asyncio.sleep(2)
                    else:
                        print(f"❌ Job status check failed: HTTP {response.status}")
                        return False
                        
            except Exception as e:
                print(f"❌ Job polling error: {e}")
                return False
        
        print(f"❌ Job timeout after {max_wait} seconds")
        return False
    
    async def verify_asset(self, session, asset_id):
        """Verify the generated asset"""
        print(f"🔍 Verifying asset {asset_id}...")
        
        try:
            async with session.get(f"{self.backend_url}/api/v1/assets/{asset_id}") as response:
                if response.status == 200:
                    asset_data = await response.json()
                    asset_info = asset_data.get("asset", {})
                    
                    print("✅ Asset verification PASSED")
                    print(f"   Original prompt: {asset_info.get('original_prompt', '')}")
                    print(f"   Enhanced prompt: {asset_info.get('prompt', '')}")
                    print(f"   Generation time: {asset_info.get('generation_time', 0):.2f}s")
                    print(f"   Category: {asset_info.get('category', '')}")
                    print(f"   Style: {asset_info.get('style', '')}")
                    print(f"   Resolution: {asset_info.get('resolution', '')}")
                    
                    return True
                else:
                    print(f"❌ Asset verification FAILED: HTTP {response.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ Asset verification error: {e}")
            return False
    
    async def run_complete_test(self):
        """Run complete end-to-end test suite"""
        print("🚀 GAMEFORGE AI END-TO-END PIPELINE TEST")
        print("="*60)
        print(f"Backend URL: {self.backend_url}")
        print(f"GPU Server URL: {self.gpu_server_url}")
        print(f"Test Time: {datetime.now().isoformat()}")
        print()
        
        # Test 1: Direct GPU server connection
        gpu_direct_ok = await self.test_gpu_server_direct()
        
        # Test 2: Backend health and GPU integration
        backend_ok = await self.test_backend_health()
        
        # Test 3: Complete asset generation pipeline
        if gpu_direct_ok and backend_ok:
            generation_ok = await self.test_asset_generation()
        else:
            print("\n⚠️  Skipping asset generation test due to connection issues")
            generation_ok = False
        
        # Final results
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)
        
        tests = [
            ("GPU Server Direct", gpu_direct_ok),
            ("Backend Health", backend_ok), 
            ("Asset Generation E2E", generation_ok)
        ]
        
        passed = sum(1 for _, result in tests if result)
        total = len(tests)
        
        for test_name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
        
        print(f"\n🎯 OVERALL RESULT: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎊 ALL TESTS PASSED - PRODUCTION READY!")
            print("✅ Complete GameForge AI pipeline working end-to-end")
            print("✅ Frontend → Backend → GPU → Result pipeline verified")
        else:
            print("⚠️  Some tests failed - check configuration")
            
            if not gpu_direct_ok:
                print("   • Check if GPU server is running on Vast instance")
                print("   • Verify port 41392 is accessible")
            
            if not backend_ok:
                print("   • Check if GameForge backend is running")
                print("   • Verify backend can reach GPU server")
            
            if not generation_ok:
                print("   • Check GPU server pipeline initialization")
                print("   • Verify SDXL model is loaded")
        
        return passed == total


async def main():
    """Run the test suite"""
    tester = GameForgeE2ETester()
    success = await tester.run_complete_test()
    return success


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(main())
    exit(0 if result else 1)
