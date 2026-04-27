import inspect
import json
import logging
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.requests import Request


logger = logging.getLogger(__name__)


def build_connected_event(branch_id: int) -> dict[str, Any]:
    timestamp = _format_timestamp(datetime.now(UTC))
    return build_event_envelope(
        "connected",
        branch_id,
        {
            "message": "Stream connected",
            "branch_id": branch_id,
            "timestamp": timestamp,
        },
    )


def build_event_envelope(
    event_type: str,
    branch_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": str(int(time.time() * 1000)),
        "timestamp": _format_timestamp(datetime.now(UTC)),
        "branch_id": branch_id,
        "payload": payload,
    }


async def redis_sse_stream(
    request: Request,
    redis: Redis,
    channel: str,
    branch_id: int,
) -> AsyncIterator[dict[str, str | int]]:
    pubsub = redis.pubsub()
    subscribed = False

    try:
        await pubsub.subscribe(channel)
        subscribed = True

        yield _to_sse_message(build_connected_event(branch_id))

        while True:
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )
            if message is None:
                continue

            raw_data = message.get("data")
            if not raw_data:
                continue

            try:
                event = json.loads(raw_data)
            except json.JSONDecodeError:
                logger.exception("sse_event_decode_failed", extra={"channel": channel})
                continue

            yield _to_sse_message(event)
    except RedisError:
        logger.exception("sse_redis_stream_failed", extra={"channel": channel})
    finally:
        if subscribed:
            try:
                await pubsub.unsubscribe(channel)
            except RedisError:
                logger.exception("sse_redis_unsubscribe_failed", extra={"channel": channel})
        await _close_pubsub(pubsub)


def _to_sse_message(event: dict[str, Any]) -> dict[str, str | int]:
    return {
        "id": str(event["event_id"]),
        "event": str(event["event_type"]),
        "data": json.dumps(event, default=str),
        "retry": 5000,
    }


async def _close_pubsub(pubsub: Any) -> None:
    close = getattr(pubsub, "aclose", None) or getattr(pubsub, "close", None)
    if close is None:
        return

    result = close()
    if inspect.isawaitable(result):
        await result


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
