#!/usr/bin/env python3
"""
Test GitHub OAuth flow to see what's happening
"""
import asyncio
import httpx
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_oauth_endpoints():
    """Test the OAuth endpoints"""
    base_url = "http://localhost:8080"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test 1: Check if OAuth initiate endpoint is working
            print("🔍 Testing GitHub OAuth initiate endpoint...")
            response = await client.get(f"{base_url}/api/v1/auth/github")
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            if response.status_code == 302:
                print(f"Redirect URL: {response.headers.get('location')}")
            else:
                print(f"Response: {response.text[:500]}")
            
            print("\n" + "="*50 + "\n")
            
            # Test 2: Check server health
            print("🔍 Testing server health...")
            health_response = await client.get(f"{base_url}/health")
            print(f"Health Status: {health_response.status_code}")
            if health_response.status_code == 200:
                print(f"Health Response: {health_response.json()}")
            
            print("\n" + "="*50 + "\n")
            
            # Test 3: Check OAuth callback endpoint (should return error without params)
            print("🔍 Testing GitHub OAuth callback endpoint...")
            callback_response = await client.get(f"{base_url}/api/v1/auth/github/callback")
            print(f"Callback Status: {callback_response.status_code}")
            print(f"Callback Response: {callback_response.text[:500]}")
            
        except Exception as e:
            print(f"Error testing OAuth endpoints: {e}")

if __name__ == "__main__":
    asyncio.run(test_oauth_endpoints())