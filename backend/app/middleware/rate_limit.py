import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


logger = logging.getLogger(__name__)

RATE_LIMIT_WINDOW_SECONDS = 60
INCREMENT_WITH_TTL_SCRIPT = """
local current = redis.call("INCR", KEYS[1])
if current == 1 then
  redis.call("EXPIRE", KEYS[1], ARGV[1])
end
return current
"""


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rule = self._rule_for_request(request)
        client: Redis | None = getattr(request.app.state, "redis", None)

        if client is None:
            return await call_next(request)

        identity = self._identity_for_request(request, rule["identity"])
        key = f"rl:{identity}:{rule['route_key']}"

        try:
            count = await client.eval(
                INCREMENT_WITH_TTL_SCRIPT,
                1,
                key,
                RATE_LIMIT_WINDOW_SECONDS,
            )
            if int(count) > int(rule["limit"]):
                ttl = await client.ttl(key)
                retry_after = ttl if ttl and ttl > 0 else RATE_LIMIT_WINDOW_SECONDS
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "code": "RATE_LIMITED",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )
        except RedisError:
            logger.exception("rate_limit_redis_failed")
            return await call_next(request)

        return await call_next(request)

    def _rule_for_request(self, request: Request) -> dict[str, int | str]:
        method = request.method.upper()
        path = request.url.path

        if method == "POST" and path == "/api/v1/sessions/guest":
            return {"limit": 10, "identity": "ip", "route_key": "sessions_guest"}

        if method == "POST" and path == "/api/v1/auth/staff/login":
            return {"limit": 5, "identity": "ip", "route_key": "staff_login"}

        if method == "POST" and path == "/api/v1/orders":
            return {"limit": 5, "identity": "session", "route_key": "orders"}

        route_key = f"{method}:{path}".replace("/", "_").strip("_") or "root"
        return {"limit": 120, "identity": "ip", "route_key": route_key}

    def _identity_for_request(self, request: Request, identity_type: int | str) -> str:
        if identity_type == "session":
            session = getattr(request.state, "session", None)
            if session and session.get("session_id"):
                return str(session["session_id"])
            token = request.cookies.get("gsid") or request.headers.get("X-Session-Token")
            if token:
                return token
        return self._client_ip(request)

    def _client_ip(self, request: Request) -> str:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
        if request.client:
            return request.client.host
        return "unknown"
