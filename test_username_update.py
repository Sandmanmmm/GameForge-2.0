#!/usr/bin/env python3
"""
Test script to verify that username updates are working correctly.
This tests the backend API directly to ensure database persistence and uniqueness validation.
"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuration
BACKEND_URL = "http://localhost:8080"
TEST_USER_EMAIL = "username_test@example.com"
TEST_USER_PASSWORD = "testpassword123"
NEW_USERNAME = f"testuser_{datetime.now().strftime('%H%M%S')}"
NEW_DISPLAY_NAME = f"Updated Name {datetime.now().strftime('%H:%M:%S')}"

async def test_username_update():
    """Test the complete username update flow"""
    
    async with httpx.AsyncClient() as client:
        print("🧪 Testing Username Update Flow")
        print("=" * 50)
        
        # Step 1: Register a new test user
        print("1. Registering test user...")
        register_response = await client.post(
            f"{BACKEND_URL}/api/v1/auth/register",
            json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "username": f"original_{datetime.now().strftime('%H%M%S')}",
                "name": "Original Test User"
            }
        )
        
        if register_response.status_code != 200:
            print(f"❌ Registration failed: {register_response.status_code}")
            print(f"Response: {register_response.text}")
            return
        
        register_data = register_response.json()
        token = register_data.get("access_token")
        original_user = register_data.get("user", {})
        
        print(f"✅ User registered successfully")
        print(f"   Original username: {original_user.get('username', 'N/A')}")
        print(f"   Original name: {original_user.get('name', 'N/A')}")
        print(f"   User ID: {original_user.get('id', 'N/A')}")
        
        # Step 2: Get current profile
        print("\\n2. Getting current profile...")
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
        print(f"   Current username: {current_profile.get('username', 'N/A')}")
        print(f"   Current name: {current_profile.get('name', 'N/A')}")
        
        # Step 3: Update username and name
        print(f"\\n3. Updating username to: {NEW_USERNAME}")
        print(f"   Updating name to: {NEW_DISPLAY_NAME}")
        update_response = await client.patch(
            f"{BACKEND_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": NEW_USERNAME,
                "name": NEW_DISPLAY_NAME
            }
        )
        
        if update_response.status_code != 200:
            print(f"❌ Profile update failed: {update_response.status_code}")
            print(f"Response: {update_response.text}")
            return
        
        update_data = update_response.json()
        updated_user = update_data.get("user", {})
        new_token = update_data.get("access_token")
        
        print(f"✅ Profile update successful")
        print(f"   Updated username: {updated_user.get('username', 'N/A')}")
        print(f"   Updated name: {updated_user.get('name', 'N/A')}")
        print(f"   New token received: {'Yes' if new_token else 'No'}")
        
        # Step 4: Verify persistence by fetching profile again with new token
        print("\\n4. Verifying persistence (fetching profile with new token)...")
        verify_response = await client.get(
            f"{BACKEND_URL}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        
        if verify_response.status_code != 200:
            print(f"❌ Profile verification failed: {verify_response.status_code}")
            print(f"Response: {verify_response.text}")
            return
        
        verified_profile = verify_response.json()
        verified_username = verified_profile.get("username")
        verified_name = verified_profile.get("name")
        
        print(f"✅ Profile verification complete")
        print(f"   Verified username: {verified_username}")
        print(f"   Verified name: {verified_name}")
        
        # Step 5: Check if the updates were persisted
        if verified_username == NEW_USERNAME and verified_name == NEW_DISPLAY_NAME:
            print(f"\\n🎉 SUCCESS: Profile updates persisted correctly!")
            print(f"   ✅ Username changed to '{verified_username}'")
            print(f"   ✅ Name changed to '{verified_name}'")
        else:
            print(f"\\n❌ FAILURE: Profile updates were not persisted correctly")
            print(f"   Expected username: {NEW_USERNAME}, Got: {verified_username}")
            print(f"   Expected name: {NEW_DISPLAY_NAME}, Got: {verified_name}")
        
        # Step 6: Test username uniqueness validation
        print("\\n5. Testing username uniqueness validation...")
        
        # Try to register another user with the same username
        duplicate_response = await client.post(
            f"{BACKEND_URL}/api/v1/auth/register",
            json={
                "email": f"duplicate_{TEST_USER_EMAIL}",
                "password": TEST_USER_PASSWORD,
                "username": NEW_USERNAME,  # Same username as updated user
                "name": "Duplicate User"
            }
        )
        
        if duplicate_response.status_code == 409 or "already exists" in duplicate_response.text.lower():
            print(f"✅ Username uniqueness validation working correctly")
            print(f"   Registration correctly rejected duplicate username")
        else:
            print(f"❌ Username uniqueness validation failed")
            print(f"   Duplicate registration should have been rejected")
            print(f"   Status: {duplicate_response.status_code}")
            print(f"   Response: {duplicate_response.text}")
        
        # Step 7: Test updating to an existing username
        print("\\n6. Testing update to existing username...")
        
        # Register another user first
        another_user_response = await client.post(
            f"{BACKEND_URL}/api/v1/auth/register",
            json={
                "email": f"another_{TEST_USER_EMAIL}",
                "password": TEST_USER_PASSWORD,
                "username": f"another_{datetime.now().strftime('%H%M%S')}",
                "name": "Another User"
            }
        )
        
        if another_user_response.status_code == 200:
            another_user_data = another_user_response.json()
            another_token = another_user_data.get("access_token")
            
            # Try to update this user's username to the first user's username
            conflict_response = await client.patch(
                f"{BACKEND_URL}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {another_token}"},
                json={"username": NEW_USERNAME}  # Same as first user
            )
            
            if conflict_response.status_code == 409:
                print(f"✅ Username conflict validation working correctly")
                print(f"   Update correctly rejected conflicting username")
            else:
                print(f"❌ Username conflict validation failed")
                print(f"   Update should have been rejected")
                print(f"   Status: {conflict_response.status_code}")
                print(f"   Response: {conflict_response.text}")

if __name__ == "__main__":
    print("Starting GameForge Username Update Test")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test Username: {NEW_USERNAME}")
    print(f"Test Display Name: {NEW_DISPLAY_NAME}")
    print()
    
    asyncio.run(test_username_update())