import asyncio
import asyncpg
import uuid
import sys

async def main(session_id):
    conn = await asyncpg.connect('postgresql://postgres:Rushabh%40123@localhost:5432/talksense')
    
    print(f"=== SESSION {session_id} ===")
    rows = await conn.fetch('SELECT id, status, started_at, ended_at FROM sessions WHERE id = $1', uuid.UUID(session_id))
    for r in rows:
        print(dict(r))

    print("\n--- ALL SESSIONS RECENT ---")
    rows = await conn.fetch('SELECT id, status, started_at, ended_at FROM sessions ORDER BY started_at DESC LIMIT 5')
    for r in rows:
        print(dict(r))

    await conn.close()

if __name__ == '__main__':
    asyncio.run(main(sys.argv[1]))
