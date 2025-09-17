#!/usr/bin/env python3
"""
Quick test to check if users are being saved to the database
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gameforge.core.database import get_async_session
from gameforge.models.base import User
from sqlalchemy import select, func


async def check_database_users():
    """Check what users are currently in the database"""
    session_gen = get_async_session()
    session = await session_gen.__anext__()
    
    try:
        # Count total users
        result = await session.execute(select(func.count(User.id)))
        total_users = result.scalar()
        print(f"Total users in database: {total_users}")
        
        # Get recent users (last 10)
        result = await session.execute(
            select(User)
            .order_by(User.created_at.desc())
            .limit(10)
        )
        recent_users = result.scalars().all()
        
        print("\nRecent users:")
        for user in recent_users:
            print(f"  - ID: {user.id}")
            print(f"    Username: {user.username}")
            print(f"    Email: {user.email}")
            print(f"    Provider: {user.provider}")
            print(f"    GitHub ID: {user.github_id}")
            print(f"    Created: {user.created_at}")
            print()
            
        # Check for OAuth users specifically
        result = await session.execute(
            select(User).where(User.github_id.isnot(None))
        )
        github_users = result.scalars().all()
        
        print(f"GitHub OAuth users: {len(github_users)}")
        for user in github_users:
            print(f"  - {user.username} ({user.email}) - GitHub ID: {user.github_id}")
            
    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(check_database_users())