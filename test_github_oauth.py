#!/usr/bin/env python3
"""
Test script for GitHub OAuth integration
"""
import httpx
import asyncio


async def test_github_oauth():
    """Test the GitHub OAuth endpoints."""
    base_url = "http://localhost:8000"
    
    print("🔍 Testing GitHub OAuth Integration")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # Test health endpoint first
        try:
            response = await client.get(f"{base_url}/health")
            print(f"✅ Health endpoint: {response.status_code}")
        except Exception as e:
            print(f"❌ Health endpoint failed: {e}")
            return
        
        # Test GitHub OAuth endpoint
        try:
            response = await client.get(
                f"{base_url}/api/v1/auth/github",
                follow_redirects=False
            )
            print(f"🔐 GitHub OAuth endpoint: {response.status_code}")
            
            if response.status_code == 500:
                print("   ⚠️  Expected: GitHub OAuth not configured")
            elif response.status_code == 302:
                print("   ✅ Redirect to GitHub OAuth (credentials configured)")
                print(f"   📍 Redirect URL: {response.headers.get('location')}")
            else:
                print(f"   ❓ Unexpected response: {response.text}")
                
        except Exception as e:
            print(f"❌ GitHub OAuth endpoint failed: {e}")
        
        # Test regular auth endpoints
        try:
            response = await client.get(f"{base_url}/api/v1/auth/me")
            print(f"👤 Auth /me endpoint: {response.status_code}")
            if response.status_code == 401:
                print("   ✅ Expected: Unauthorized (no token provided)")
        except Exception as e:
            print(f"❌ Auth /me endpoint failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_github_oauth())