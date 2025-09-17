#!/usr/bin/env python3
"""
Test OAuth user creation with fresh unique data
"""
import asyncio
import sys
import os
from datetime import datetime
import uuid

# Add the GameForge directory to Python path
gameforge_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, gameforge_path)

from gameforge.api.v1.auth import create_or_update_oauth_user


async def test_fresh_oauth_user():
    """Test OAuth user creation with completely fresh data"""
    print("🧪 Testing Fresh OAuth User Creation")
    print("=" * 50)
    
    # Create unique test data using timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    github_user_data = {
        'id': f'github_{timestamp}_{unique_id}',
        'email': f'fresh_test_{timestamp}@github.example.com',
        'login': f'github_user_{unique_id}',
        'name': f'Fresh GitHub User {timestamp}',
        'avatar_url': f'https://avatars.githubusercontent.com/u/{unique_id}'
    }
    
    try:
        print(f"📝 Testing with unique data:")
        print(f"   - GitHub ID: {github_user_data['id']}")
        print(f"   - Email: {github_user_data['email']}")
        print(f"   - Username: {github_user_data['login']}")
        
        # Test OAuth user creation
        user = await create_or_update_oauth_user(
            user_data=github_user_data,
            provider="github",
            client_ip="192.168.1.100"
        )
        
        print(f"\n✅ OAuth user created successfully!")
        print(f"   - Database ID: {user.id}")
        print(f"   - Username: {user.username}")
        print(f"   - Email: {user.email}")
        print(f"   - GitHub ID: {user.github_id}")
        print(f"   - Provider: {user.provider}")
        print(f"   - Is Verified: {user.is_verified}")
        print(f"   - Is Active: {user.is_active}")
        print(f"   - Password Hash: {user.password_hash}")
        
        # Test updating the same user
        print(f"\n🔄 Testing user update...")
        updated_data = github_user_data.copy()
        updated_data['name'] = f'Updated GitHub User {timestamp}'
        
        updated_user = await create_or_update_oauth_user(
            user_data=updated_data,
            provider="github",
            client_ip="192.168.1.101"
        )
        
        print(f"✅ OAuth user updated successfully!")
        print(f"   - Same Database ID: {user.id == updated_user.id}")
        print(f"   - Updated Name: {updated_user.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test runner"""
    print("🔐 Testing OAuth User Database Integration")
    print("=" * 60)
    print("Testing OAuth user creation and database persistence")
    print()
    
    success = await test_fresh_oauth_user()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 OAuth user database integration working perfectly!")
        print("✅ NEW ACCOUNTS REGISTERED VIA OAUTH CREATE DATABASE RECORDS")
    else:
        print("❌ OAuth user database integration test failed!")
    
    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)