from collections.abc import AsyncIterator

import asyncpg
from fastapi import Request

from app.config import Settings, get_settings


async def create_db_pool(settings: Settings | None = None) -> asyncpg.Pool:
    current_settings = settings or get_settings()
    return await asyncpg.create_pool(
        dsn=current_settings.DATABASE_URL,
        min_size=5,
        max_size=20,
        command_timeout=60,
    )


async def close_db_pool(pool: asyncpg.Pool | None) -> None:
    if pool is not None:
        await pool.close()


async def get_db(request: Request) -> AsyncIterator[asyncpg.Connection]:
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as connection:
        yield connection
