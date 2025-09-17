import asyncio
import sqlalchemy as sa
from gameforge.core.database import DatabaseManager

async def show_tables():
    db = DatabaseManager()
    await db.initialize()
    async with db.get_async_session() as session:
        result = await session.execute(sa.text("SELECT tablename FROM pg_tables WHERE schemaname='public';"))
        tables = result.fetchall()
        print('Current tables:')
        for table in tables:
            print(f'  - {table[0]}')

if __name__ == "__main__":
    asyncio.run(show_tables())