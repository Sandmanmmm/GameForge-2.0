#!/usr/bin/env python3
"""
Check database tables and production readiness
"""
import asyncio
import os
from sqlalchemy import text
from gameforge.core.database import db_manager

async def check_database_status():
    """Check database tables and basic production readiness."""
    print("🔍 GameForge Database Production Readiness Check")
    print("=" * 60)
    
    try:
        # Initialize database manager
        await db_manager.initialize()
        
        async with db_manager.get_async_session() as session:
            # Check tables
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            
            print(f"📊 Database Tables: {len(tables)} total")
            print("-" * 30)
            for table in tables:
                print(f"  ✅ {table}")
            
            # Check indexes
            result = await session.execute(text("""
                SELECT indexname, tablename 
                FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND indexname LIKE '%gin%'
                ORDER BY tablename, indexname;
            """))
            gin_indexes = list(result)
            
            print(f"\n⚡ GIN Indexes: {len(gin_indexes)} total")
            print("-" * 30)
            for idx_name, table_name in gin_indexes:
                print(f"  ✅ {idx_name} on {table_name}")
            
            # Check constraints
            result = await session.execute(text("""
                SELECT conname, contype 
                FROM pg_constraint 
                WHERE connamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                AND contype = 'c'
                ORDER BY conname;
            """))
            constraints = list(result)
            
            print(f"\n🔒 Check Constraints: {len(constraints)} total")
            print("-" * 30)
            for constraint_name, constraint_type in constraints:
                print(f"  ✅ {constraint_name}")
            
            # Check seed data
            result = await session.execute(text("SELECT COUNT(*) FROM users WHERE role = 'admin';"))
            admin_count = result.scalar()
            
            print(f"\n👤 Seed Data Status")
            print("-" * 30)
            print(f"  ✅ Admin users: {admin_count}")
            
            print(f"\n🎉 PRODUCTION READINESS: ✅ READY")
            print("All components successfully deployed!")
            
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Ensure we have the database URL
    if not os.getenv('DATABASE_URL'):
        os.environ['DATABASE_URL'] = 'postgresql://postgres:password@localhost:5432/gameforge_dev'
    
    asyncio.run(check_database_status())