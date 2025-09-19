import asyncio
import sys
sys.path.insert(0, 'd:/GameForge 2.0/GameForge-2.0')

from gameforge.core.database import get_async_session
from gameforge.models.users import User
from sqlalchemy import text
import uuid

async def test_database_sync():
    print('🧪 Testing Database Synchronization')
    print('=' * 50)
    
    try:
        # Test database connection and check users table
        async for session in get_async_session():
            # Check if users table exists and has correct columns
            query = text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position")
            result = await session.execute(query)
            columns = result.fetchall()
            
            print('👥 Users table structure:')
            for col_name, data_type in columns:
                print(f'   - {col_name}: {data_type}')
            
            # Check if username column exists
            username_exists = any(col[0] == 'username' for col in columns)
            print(f'\n✅ Username column exists: {username_exists}')
            
            if not username_exists:
                print('❌ Username column missing from database!')
                return
            
            # Test creating a user with username
            test_user = User(
                id=str(uuid.uuid4()),
                email='test_sync@example.com',
                username='test_sync_user',
                name='Test Sync User',
                password_hash='test_hash'
            )
            
            session.add(test_user)
            await session.commit()
            print(f'✅ Created test user: {test_user.username}')
            
            # Test updating username
            original_username = test_user.username
            test_user.username = 'updated_sync_user'
            test_user.name = 'Updated Name'
            await session.commit()
            print(f'✅ Updated user from {original_username} to {test_user.username}')
            
            # Verify the update persisted by refreshing from database
            await session.refresh(test_user)
            print(f'✅ Database verification: username={test_user.username}, name={test_user.name}')
            
            # Clean up
            await session.delete(test_user)
            await session.commit()
            print('✅ Cleaned up test user')
            
            print('\n🎉 Database synchronization test PASSED!')
            print('   ✓ Username column exists in users table')
            print('   ✓ Can create users with username')
            print('   ✓ Can update username and name fields')
            print('   ✓ Updates persist correctly to database')
            
    except Exception as e:
        print(f'❌ Database test failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_database_sync())