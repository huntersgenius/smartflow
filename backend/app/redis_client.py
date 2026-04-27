from collections.abc import AsyncIterator

import redis.asyncio as redis
from fastapi import Request

from app.config import Settings, get_settings


async def create_redis_pool(settings: Settings | None = None) -> redis.Redis:
    current_settings = settings or get_settings()
    client = redis.from_url(
        current_settings.REDIS_URL,
        decode_responses=True,
        health_check_interval=30,
    )
    await client.ping()
    return client


async def close_redis_pool(client: redis.Redis | None) -> None:
    if client is not None:
        await client.aclose()


async def get_redis(request: Request) -> AsyncIterator[redis.Redis]:
    yield request.app.state.redis
