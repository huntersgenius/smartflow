import logging

import asyncpg
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=None)
async def health_check(request: Request):
    checks = {
        "database": await _check_database(request),
        "redis": await _check_redis(request),
    }

    if all(value == "ok" for value in checks.values()):
        return {"status": "ok", "checks": checks}

    return JSONResponse(
        status_code=503,
        content={
            "error": "Health check failed",
            "code": "HEALTH_CHECK_FAILED",
            "checks": checks,
        },
    )

async def _check_database(request: Request) -> str:
    pool: asyncpg.Pool | None = getattr(request.app.state, "db_pool", None)
    if pool is None:
        return "missing"

    try:
        async with pool.acquire() as connection:
            value = await connection.fetchval("SELECT 1")
        return "ok" if value == 1 else "error"
    except asyncpg.PostgresError:
        logger.exception("health_database_check_failed")
        return "error"


async def _check_redis(request: Request) -> str:
    client: Redis | None = getattr(request.app.state, "redis", None)
    if client is None:
        return "missing"

    try:
        response = await client.ping()
        return "ok" if response else "error"
    except RedisError:
        logger.exception("health_redis_check_failed")
        return "error"
