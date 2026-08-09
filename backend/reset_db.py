import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from core.config import get_settings

# Alembic handles metadata
from sqlalchemy import MetaData
import logging


async def reset_db():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    # The models are not all imported here so we can't do Base.metadata.drop_all directly
    # Better to just drop the schema public cascade and recreate it.
    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO postgres;"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
    print("DB reset complete. Now Alembic can run cleanly.")


if __name__ == "__main__":
    asyncio.run(reset_db())
