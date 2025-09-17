import asyncio
import sqlalchemy as sa
from gameforge.core.database import DatabaseManager

async def reset_database():
    db = DatabaseManager()
    await db.initialize()
    
    async with db.get_async_session() as session:
        # Drop all tables in cascade mode to handle foreign key dependencies
        print("Dropping all existing tables...")
        result = await session.execute(sa.text("SELECT tablename FROM pg_tables WHERE schemaname='public';"))
        tables = result.fetchall()
        
        for table in tables:
            table_name = table[0]
            if table_name != 'alembic_version':  # Keep alembic version table
                print(f"  Dropping table: {table_name}")
                await session.execute(sa.text(f"DROP TABLE IF EXISTS {table_name} CASCADE;"))
        
        await session.commit()
        print("✅ All tables dropped successfully")

if __name__ == "__main__":
    asyncio.run(reset_database())