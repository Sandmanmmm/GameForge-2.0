#!/usr/bin/env python3
"""
Test OAuth callback with real-looking GitHub data to check database persistence
"""
import asyncio
import httpx
import sys
from pathlib import Path
from urllib.parse import urlencode

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_oauth_callback_simulation():
    """Simulate a GitHub OAuth callback with real-looking data"""
    base_url = "http://localhost:8080"
    
    # This would be the callback URL GitHub would redirect to after authorization
    callback_params = {
        'code': 'test_authorization_code_from_github',
        'state': 'test_state_parameter'
    }
    
    callback_url = f"{base_url}/api/v1/auth/github/callback?{urlencode(callback_params)}"
    
    print(f"🔍 Testing OAuth callback with simulated GitHub authorization...")
    print(f"Callback URL: {callback_url}")
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        try:
            response = await client.get(callback_url)
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            
            if response.status_code == 302:
                redirect_url = response.headers.get('location', '')
                print(f"Redirect URL: {redirect_url}")
                
                # Check if this is a successful redirect or error redirect
                if 'error=' in redirect_url:
                    print("❌ OAuth callback returned an error")
                    # Extract error details
                    from urllib.parse import parse_qs, urlparse
                    parsed = urlparse(redirect_url)
                    params = parse_qs(parsed.query)
                    if 'error' in params:
                        print(f"Error: {params['error'][0]}")
                    if 'error_description' in params:
                        print(f"Error Description: {params['error_description'][0]}")
                else:
                    print("✅ OAuth callback appears successful")
            else:
                print(f"Response body: {response.text[:1000]}")
                
        except Exception as e:
            print(f"Error during OAuth callback test: {e}")

if __name__ == "__main__":
    asyncio.run(test_oauth_callback_simulation())