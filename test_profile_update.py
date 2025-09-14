#!/usr/bin/env python3
"""
Test script to verify that profile updates are working correctly.
This tests the backend API directly to ensure database persistence.
"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:8080"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "testpassword123"
NEW_DISPLAY_NAME = f"Updated Name {datetime.now().strftime('%H:%M:%S')}"

async def test_profile_update():
    """Test the complete profile update flow"""
    
    async with httpx.AsyncClient() as client:
        print("🧪 Testing Profile Update Flow")
        print("=" * 50)
        
        # Step 1: Login to get a token
        print("1. Logging in...")
        login_response = await client.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json={
                "username": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            
            # Try to register user if login fails
            print("2. Attempting to register user...")
            register_response = await client.post(
                f"{BACKEND_URL}/api/v1/auth/register",
                json={
                    "email": TEST_USER_EMAIL,
                    "password": TEST_USER_PASSWORD,
                    "name": "Test User"
                }
            )
            
            if register_response.status_code != 200:
                print(f"❌ Registration failed: {register_response.status_code}")
                print(f"Response: {register_response.text}")
                return
            
            print("✅ User registered successfully")
            
            # Try login again
            login_response = await client.post(
                f"{BACKEND_URL}/api/v1/auth/login",
                json={
                    "username": TEST_USER_EMAIL,
                    "password": TEST_USER_PASSWORD
                }
            )
        
        if login_response.status_code != 200:
            print(f"❌ Login still failed: {login_response.status_code}")
            return
        
        login_data = login_response.json()
        token = login_data.get("access_token")
        original_user = login_data.get("user", {})
        
        print(f"✅ Login successful")
        print(f"   Original name: {original_user.get('name', 'N/A')}")
        print(f"   User ID: {original_user.get('id', 'N/A')}")
        
        # Step 2: Get current profile
        print("\n3. Getting current profile...")
        profile_response = await client.get(
            f"{BACKEND_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if profile_response.status_code != 200:
            print(f"❌ Profile fetch failed: {profile_response.status_code}")
            print(f"Response: {profile_response.text}")
            return
        
        current_profile = profile_response.json()
        print(f"✅ Current profile retrieved")
        print(f"   Current name: {current_profile.get('name', 'N/A')}")
        
        # Step 3: Update profile
        print(f"\n4. Updating profile name to: {NEW_DISPLAY_NAME}")
        update_response = await client.patch(
            f"{BACKEND_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": NEW_DISPLAY_NAME}
        )
        
        if update_response.status_code != 200:
            print(f"❌ Profile update failed: {update_response.status_code}")
            print(f"Response: {update_response.text}")
            return
        
        update_data = update_response.json()
        updated_user = update_data.get("user", {})
        new_token = update_data.get("access_token")
        
        print(f"✅ Profile update successful")
        print(f"   Updated name: {updated_user.get('name', 'N/A')}")
        print(f"   New token received: {'Yes' if new_token else 'No'}")
        
        # Step 4: Verify persistence by fetching profile again with new token
        print("\n5. Verifying persistence (fetching profile with new token)...")
        verify_response = await client.get(
            f"{BACKEND_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        
        if verify_response.status_code != 200:
            print(f"❌ Profile verification failed: {verify_response.status_code}")
            print(f"Response: {verify_response.text}")
            return
        
        verified_profile = verify_response.json()
        verified_name = verified_profile.get("name")
        
        print(f"✅ Profile verification complete")
        print(f"   Verified name: {verified_name}")
        
        # Step 5: Check if the update was persisted
        if verified_name == NEW_DISPLAY_NAME:
            print(f"\n🎉 SUCCESS: Profile update persisted correctly!")
            print(f"   ✅ Name changed from '{original_user.get('name')}' to '{verified_name}'")
        else:
            print(f"\n❌ FAILURE: Profile update was not persisted")
            print(f"   Expected: {NEW_DISPLAY_NAME}")
            print(f"   Got: {verified_name}")
        
        # Step 6: Test with original token to ensure it still works
        print("\n6. Testing original token (should still work until expiry)...")
        old_token_response = await client.get(
            f"{BACKEND_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if old_token_response.status_code == 200:
            old_token_data = old_token_response.json()
            print(f"✅ Original token still valid")
            print(f"   Name from old token: {old_token_data.get('name', 'N/A')}")
        else:
            print(f"ℹ️  Original token expired or invalid: {old_token_response.status_code}")

if __name__ == "__main__":
    print("Starting GameForge Profile Update Test")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test Display Name: {NEW_DISPLAY_NAME}")
    print()
    
    asyncio.run(test_profile_update())