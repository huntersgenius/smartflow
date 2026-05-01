import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis

from app.celery_app.worker import app
from app.config import get_settings
from app.database import close_db_pool, create_db_pool


logger = logging.getLogger(__name__)


@app.task(name="app.celery_app.tasks.cleanup.cleanup_expired_sessions")
def cleanup_expired_sessions() -> dict[str, Any]:
    return asyncio.run(_cleanup_expired_sessions())


async def _cleanup_expired_sessions() -> dict[str, Any]:
    settings = get_settings()
    db_pool = await create_db_pool(settings)
    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        health_check_interval=30,
    )
    try:
        async with db_pool.acquire() as db:
            staff_rows = await db.fetch(
                """
                DELETE FROM staff_sessions
                WHERE expires_at <= now()
                RETURNING id
                """
            )
            guest_rows = await db.fetch(
                """
                DELETE FROM guest_sessions gs
                WHERE gs.expires_at <= now()
                  AND NOT EXISTS (
                      SELECT 1
                      FROM orders o
                      WHERE o.session_id = gs.id
                  )
                RETURNING id
                """
            )

        stale_redis_keys = await _delete_expired_session_cache(redis_client)
        result = {
            "guest_sessions_deleted": len(guest_rows),
            "staff_sessions_deleted": len(staff_rows),
            "redis_keys_deleted": stale_redis_keys,
        }
        logger.info("expired_session_cleanup_complete", extra=result)
        return result
    finally:
        await redis_client.aclose()
        await close_db_pool(db_pool)


async def _delete_expired_session_cache(redis_client: redis.Redis) -> int:
    deleted = 0
    now = datetime.now(UTC)
    for pattern in ("guest:*", "staff:*"):
        async for key in redis_client.scan_iter(match=pattern, count=100):
            cached = await redis_client.get(key)
            if not cached:
                continue

            try:
                session = json.loads(cached)
                expires_at = _parse_expiry(session.get("expires_at"))
            except (json.JSONDecodeError, TypeError, ValueError):
                await redis_client.delete(key)
                deleted += 1
                continue

            if expires_at <= now:
                await redis_client.delete(key)
                deleted += 1

    return deleted


def _parse_expiry(value: str | None) -> datetime:
    if not value:
        raise ValueError("expires_at is missing")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
