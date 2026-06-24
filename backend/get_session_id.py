import asyncio
from db.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT id FROM sessions ORDER BY created_at DESC LIMIT 5"))
        for row in result:
            print(row[0])

asyncio.run(main())
