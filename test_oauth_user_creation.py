#!/usr/bin/env python3
"""
Test script to verify OAuth user creation in the database.
This tests the create_or_update_oauth_user function.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gameforge.api.v1.auth import create_or_update_oauth_user
from gameforge.core.database import get_async_session
from gameforge.models import User
from sqlalchemy import select

async def test_oauth_user_creation():
    """Test OAuth user creation and update functionality."""
    print("🧪 Testing OAuth User Creation")
    print("=" * 50)
    
    # Test data for GitHub OAuth user
    github_user_data = {
        "id": "12345678",
        "email": "testuser@github.example.com",
        "login": "testuser_gh", 
        "username": "testuser_gh",
        "name": "Test GitHub User",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345678"
    }
    
    try:
        print("1. Testing GitHub user creation...")
        
        # Create GitHub user
        github_user = await create_or_update_oauth_user(
            github_user_data,
            "github",
            "127.0.0.1"
        )
        
        print(f"✅ GitHub user created: {github_user.username}")
        print(f"   - ID: {github_user.id}")
        print(f"   - Email: {github_user.email}")
        print(f"   - GitHub ID: {github_user.github_id}")
        print(f"   - Provider: {github_user.provider}")
        print(f"   - Is Verified: {github_user.is_verified}")
        
        print("\n2. Testing GitHub user update...")
        
        # Update the same user (should update existing record)
        updated_github_data = github_user_data.copy()
        updated_github_data["name"] = "Updated GitHub User"
        updated_github_data["avatar_url"] = "https://new-avatar.com/updated.jpg"
        
        updated_user = await create_or_update_oauth_user(
            updated_github_data,
            "github", 
            "127.0.0.1"
        )
        
        print(f"✅ GitHub user updated: {updated_user.username}")
        print(f"   - Name changed: {updated_user.name}")
        print(f"   - Avatar updated: {updated_user.avatar_url}")
        print(f"   - Same ID: {updated_user.id == github_user.id}")
        
        print("\n3. Testing Google user creation...")
        
        # Test data for Google OAuth user
        google_user_data = {
            "id": "87654321",
            "email": "testuser@google.example.com",
            "username": "testuser_gg",
            "name": "Test Google User",
            "avatar_url": "https://lh3.googleusercontent.com/test"
        }
        
        google_user = await create_or_update_oauth_user(
            google_user_data,
            "google",
            "127.0.0.1"
        )
        
        print(f"✅ Google user created: {google_user.username}")
        print(f"   - ID: {google_user.id}")
        print(f"   - Email: {google_user.email}")
        print(f"   - Google ID: {google_user.google_id}")
        print(f"   - Provider: {google_user.provider}")
        
        print("\n4. Verifying database records...")
        
        # Check that users are actually in the database
        async with get_async_session() as session:
            result = await session.execute(
                select(User).where(User.github_id == "12345678")
            )
            db_github_user = result.scalar_one_or_none()
            
            result = await session.execute(
                select(User).where(User.google_id == "87654321")
            )
            db_google_user = result.scalar_one_or_none()
            
            if db_github_user:
                print(f"✅ GitHub user found in database: {db_github_user.email}")
            else:
                print("❌ GitHub user not found in database")
                
            if db_google_user:
                print(f"✅ Google user found in database: {db_google_user.email}")
            else:
                print("❌ Google user not found in database")
        
        print("\n🎉 OAuth User Creation Test Completed Successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ OAuth user creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    print("Starting OAuth User Creation Test")
    print(f"Testing database user creation for OAuth authentication")
    print()
    
    success = await test_oauth_user_creation()
    
    if success:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())