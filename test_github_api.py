#!/usr/bin/env python3
"""
Test GitHub API connectivity to diagnose OAuth issues
"""
import asyncio
import httpx
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gameforge.core.config import get_settings

async def test_github_api():
    """Test GitHub API connectivity and OAuth endpoints"""
    
    print("🔍 Testing GitHub API connectivity...")
    
    settings = get_settings()
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test 1: Check GitHub API general connectivity
            print("\n1. Testing GitHub API general access...")
            response = await client.get("https://api.github.com/")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ GitHub API accessible")
                print(f"   Rate limit: {data.get('rate_limit_url', 'unknown')}")
            else:
                print(f"   ❌ GitHub API not accessible: {response.text}")
                
            # Test 2: Test OAuth token endpoint (should fail without valid code)
            print("\n2. Testing GitHub OAuth token endpoint...")
            token_response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": "invalid_test_code"
                },
                headers={"Accept": "application/json"}
            )
            print(f"   Status: {token_response.status_code}")
            print(f"   Response: {token_response.text[:200]}")
            
            # This should fail with an error about bad verification code
            # which confirms the endpoint is working
            
            # Test 3: Check rate limiting
            print("\n3. Testing GitHub API rate limits...")
            rate_response = await client.get("https://api.github.com/rate_limit")
            if rate_response.status_code == 200:
                rate_data = rate_response.json()
                core_limit = rate_data.get('rate', {})
                print(f"   ✅ Rate limit info:")
                print(f"   - Limit: {core_limit.get('limit', 'unknown')}")
                print(f"   - Remaining: {core_limit.get('remaining', 'unknown')}")
                print(f"   - Reset: {core_limit.get('reset', 'unknown')}")
            else:
                print(f"   ❌ Could not get rate limit info")
                
        except Exception as e:
            print(f"❌ GitHub API test failed: {e}")
            print(f"   Error type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_github_api())