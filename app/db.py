from __future__ import annotations
import asyncio
import asyncpg
import pathlib
import structlog
from .config import DATABASE_URL

log = structlog.get_logger(__name__)

async def get_pool() -> asyncpg.pool.Pool:
    return await asyncpg.create_pool(DATABASE_URL.replace("+asyncpg", ""))

MIGRATIONS = (pathlib.Path(__file__).parent / "migrations" / "001_init.sql").read_text()

async def apply_migrations(pool: asyncpg.pool.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(MIGRATIONS)
        log.info("db.migrated")

async def init() -> None:
    pool = await get_pool()
    await apply_migrations(pool)
    await pool.close()

if __name__ == "__main__":
    asyncio.run(init())
