import hashlib
import json
import logging
from typing import Any, Literal

import asyncpg
from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


logger = logging.getLogger(__name__)

GUEST_TTL_SECONDS = 14400
STAFF_TTL_SECONDS = 86400

SKIP_PATHS = {
    "/api/v1/sessions/guest",
    "/api/v1/auth/staff/login",
    "/health",
    "/docs",
    "/openapi.json",
    "/",
}

SessionPrefix = Literal["guest:", "staff:"]


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.session = None

        if self._should_skip(request.url.path):
            return await call_next(request)

        token, prefix = self._extract_token(request)
        if token is None:
            return await call_next(request)

        session: dict[str, Any] | None = None
        if prefix is not None:
            session = await self._load_prefixed_session(request, token, prefix)
        else:
            session = await self._load_header_session(request, token)

        request.state.session = session
        return await call_next(request)

    def _should_skip(self, path: str) -> bool:
        return path in SKIP_PATHS or path.startswith("/static/")

    def _extract_token(self, request: Request) -> tuple[str | None, SessionPrefix | None]:
        guest_token = request.cookies.get("gsid")
        if guest_token:
            return guest_token, "guest:"

        staff_token = request.cookies.get("ssid")
        if staff_token:
            return staff_token, "staff:"

        header_token = request.headers.get("X-Session-Token")
        if header_token:
            return header_token, None

        return None, None

    async def _load_prefixed_session(
        self, request: Request, token: str, prefix: SessionPrefix
    ) -> dict[str, Any] | None:
        cache_key = f"{prefix}{token}"
        session = await self._load_from_redis(request, cache_key, self._ttl_for_prefix(prefix))
        if session is not None:
            return session

        session = await self._load_from_database(request, token, prefix)
        if session is not None:
            await self._store_in_redis(request, cache_key, session, self._ttl_for_prefix(prefix))
        return session

    async def _load_header_session(self, request: Request, token: str) -> dict[str, Any] | None:
        for prefix in ("guest:", "staff:"):
            session = await self._load_from_database(request, token, prefix)
            if session is not None:
                await self._store_in_redis(
                    request, f"{prefix}{token}", session, self._ttl_for_prefix(prefix)
                )
                return session
        return None

    async def _load_from_redis(
        self, request: Request, cache_key: str, ttl_seconds: int
    ) -> dict[str, Any] | None:
        client: Redis | None = getattr(request.app.state, "redis", None)
        if client is None:
            return None

        try:
            cached = await client.get(cache_key)
            if not cached:
                return None
            await client.expire(cache_key, ttl_seconds)
            return json.loads(cached)
        except (RedisError, json.JSONDecodeError):
            logger.exception("session_redis_lookup_failed")
            return None

    async def _store_in_redis(
        self, request: Request, cache_key: str, session: dict[str, Any], ttl_seconds: int
    ) -> None:
        client: Redis | None = getattr(request.app.state, "redis", None)
        if client is None:
            return

        try:
            await client.setex(cache_key, ttl_seconds, json.dumps(session, default=str))
        except RedisError:
            logger.exception("session_redis_store_failed")

    async def _load_from_database(
        self, request: Request, token: str, prefix: SessionPrefix
    ) -> dict[str, Any] | None:
        pool: asyncpg.Pool | None = getattr(request.app.state, "db_pool", None)
        if pool is None:
            return None

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            async with pool.acquire() as connection:
                if prefix == "guest:":
                    row = await connection.fetchrow(
                        """
                        SELECT id, table_id, branch_id, expires_at
                        FROM guest_sessions
                        WHERE token_hash = $1 AND expires_at > now()
                        """,
                        token_hash,
                    )
                    if row is None:
                        return None
                    return {
                        "role": "guest",
                        "session_id": str(row["id"]),
                        "table_id": row["table_id"],
                        "branch_id": row["branch_id"],
                        "expires_at": row["expires_at"].isoformat(),
                    }

                row = await connection.fetchrow(
                    """
                    SELECT
                        ss.id, ss.user_id, ss.branch_id, ss.role, ss.expires_at
                    FROM staff_sessions ss
                    JOIN staff_users su ON su.id = ss.user_id
                    WHERE ss.token_hash = $1
                      AND ss.expires_at > now()
                      AND su.active = true
                    """,
                    token_hash,
                )
                if row is None:
                    return None
                return {
                    "role": row["role"],
                    "session_id": str(row["id"]),
                    "user_id": row["user_id"],
                    "branch_id": row["branch_id"],
                    "expires_at": row["expires_at"].isoformat(),
                }
        except asyncpg.PostgresError:
            logger.exception("session_database_lookup_failed")
            return None

    def _ttl_for_prefix(self, prefix: SessionPrefix) -> int:
        if prefix == "guest:":
            return GUEST_TTL_SECONDS
        return STAFF_TTL_SECONDS
