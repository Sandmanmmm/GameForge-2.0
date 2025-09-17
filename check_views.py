#!/usr/bin/env python3
"""Check database views that might cause dependency issues."""

import asyncio
import asyncpg

async def check_views():
    try:
        conn = await asyncpg.connect('postgresql://gameforge_user:gameforge_password@localhost:5432/gameforge_dev')
        views = await conn.fetch("""
            SELECT schemaname, viewname 
            FROM pg_views 
            WHERE schemaname = 'public'
            ORDER BY viewname
        """)
        print('Database views:')
        for view in views:
            print(f'  {view["viewname"]}')
        await conn.close()
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(check_views())