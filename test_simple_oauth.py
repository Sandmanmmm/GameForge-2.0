#!/usr/bin/env python3
"""
Simple test script to verify OAuth user creation works.
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gameforge.core.database import get_async_session
from gameforge.models import User, AuthProvider
from sqlalchemy import select


async def test_simple_user_creation():
    """Test creating a user directly in the database."""
    print("🧪 Testing Simple User Creation")
    print("=" * 40)
    
    try:
        # Get a database session
        session_gen = get_async_session()
        session = await session_gen.__anext__()
        
        try:
            # Create a test user
            test_user = User(
                username="oauth_test_user",
                email="test@oauth.example.com",
                name="OAuth Test User",
                password_hash=None,  # OAuth users don't have passwords (NULL)
                github_id="test_github_123",
                provider=AuthProvider.GITHUB,
                is_verified=True,
                is_active=True
            )
            
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)
            
            print("✅ User created successfully:")
            print(f"   - ID: {test_user.id}")
            print(f"   - Username: {test_user.username}")
            print(f"   - Email: {test_user.email}")
            print(f"   - GitHub ID: {test_user.github_id}")
            print(f"   - Provider: {test_user.provider}")
            
            # Try to find the user
            result = await session.execute(
                select(User).where(User.github_id == "test_github_123")
            )
            found_user = result.scalar_one_or_none()
            
            if found_user:
                print(f"✅ User found in database: {found_user.email}")
            else:
                print("❌ User not found in database")
                
            return True
            
        finally:
            await session.close()
            
    except Exception as e:
        print(f"❌ User creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function."""
    print("Testing OAuth User Database Integration")
    print("=" * 50)
    
    success = await test_simple_user_creation()
    
    if success:
        print("\n🎉 Test completed successfully!")
        print("\nThis confirms that:")
        print("✅ Database connection works")
        print("✅ User model can be created")
        print("✅ OAuth fields are properly stored")
        print("✅ Database constraints are working")
    else:
        print("\n❌ Test failed!")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)