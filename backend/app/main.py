import logging
import logging.config
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import close_db_pool, create_db_pool
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.session import SessionMiddleware
from app.redis_client import close_redis_pool, create_redis_pool
from app.routers import health, kitchen, menu, orders, sessions


logger = logging.getLogger(__name__)


def configure_logging(level: str) -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": (
                        '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
                        '"logger":"%(name)s","message":"%(message)s"}'
                    )
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                }
            },
            "root": {
                "handlers": ["default"],
                "level": level,
            },
        }
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)

    db_pool = None
    redis_client = None

    try:
        db_pool = await create_db_pool(settings)
        app.state.db_pool = db_pool
        redis_client = await create_redis_pool(settings)
        app.state.redis = redis_client
        logger.info("application_startup_complete")
        yield
    finally:
        await close_redis_pool(redis_client)
        await close_db_pool(db_pool)
        logger.info("application_shutdown_complete")


def error_envelope(message: str, code: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"error": message, "code": code}
    if extra:
        payload.update(extra)
    return payload


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail and "code" in exc.detail:
        payload = exc.detail
    else:
        payload = error_envelope(str(exc.detail), "HTTP_ERROR")
    return JSONResponse(status_code=exc.status_code, content=payload, headers=exc.headers)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_envelope("Request validation failed", "VALIDATION_ERROR"),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", extra={"path": request.url.path})
    return JSONResponse(
        status_code=500,
        content=error_envelope("Internal server error", "INTERNAL_SERVER_ERROR"),
    )


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SmartFlow API", lifespan=lifespan)

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health.router)
    app.include_router(sessions.router, prefix=settings.API_PREFIX)
    app.include_router(menu.router, prefix=settings.API_PREFIX)
    app.include_router(orders.router, prefix=settings.API_PREFIX)
    app.include_router(orders.guest_router, prefix=settings.API_PREFIX)
    app.include_router(kitchen.router, prefix=settings.API_PREFIX)

    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SessionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
