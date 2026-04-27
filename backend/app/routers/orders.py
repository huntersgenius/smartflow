from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.dependencies import require_guest_session
from app.models.requests import OrderCreateRequest
from app.models.responses import OrderCreateResponse, OrderDetailResponse
from app.redis_client import get_redis
from app.services.order_service import (
    EmptyOrderError,
    ItemUnavailableError,
    OrderForbiddenError,
    OrderNotFoundError,
    create_order,
    get_order_detail,
)
from app.services.realtime_service import redis_sse_stream


router = APIRouter(prefix="/orders", tags=["orders"])
guest_router = APIRouter(prefix="/guest/orders", tags=["orders"])


@router.post("", response_model=OrderCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_order_endpoint(
    request_data: OrderCreateRequest,
    idempotency_key_header: str | None = Header(default=None, alias="Idempotency-Key"),
    session: dict[str, Any] = Depends(require_guest_session),
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    idempotency_key = _parse_idempotency_key(idempotency_key_header)

    try:
        return await create_order(request_data, session, idempotency_key, db, redis)
    except EmptyOrderError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "items must not be empty", "code": "EMPTY_ORDER"},
        ) from exc
    except ItemUnavailableError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Item {exc.menu_item_id} not found or unavailable",
                "code": "ITEM_UNAVAILABLE",
            },
        ) from exc


@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order_endpoint(
    order_id: UUID,
    session: dict[str, Any] = Depends(require_guest_session),
    db=Depends(get_db),
) -> dict[str, Any]:
    try:
        return await get_order_detail(order_id, session, db)
    except OrderForbiddenError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Order does not belong to this session",
                "code": "ORDER_FORBIDDEN",
            },
        ) from exc
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "Order not found", "code": "ORDER_NOT_FOUND"},
        ) from exc


@guest_router.get("/{order_id}/stream", response_model=None)
async def guest_order_stream_endpoint(
    order_id: UUID,
    request: Request,
    session: dict[str, Any] = Depends(require_guest_session),
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> EventSourceResponse:
    try:
        await get_order_detail(order_id, session, db)
    except OrderForbiddenError as exc:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Order does not belong to this session",
                "code": "ORDER_FORBIDDEN",
            },
        ) from exc
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "Order not found", "code": "ORDER_NOT_FOUND"},
        ) from exc

    branch_id = int(session["branch_id"])
    return EventSourceResponse(
        redis_sse_stream(request, redis, f"order:{order_id}", branch_id),
        ping=15,
    )


def _parse_idempotency_key(value: str | None) -> UUID:
    if value is None or not value.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Idempotency-Key header is required",
                "code": "MISSING_IDEMPOTENCY_KEY",
            },
        )

    try:
        parsed = UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Idempotency-Key header must be a valid uuid4",
                "code": "INVALID_IDEMPOTENCY_KEY",
            },
        ) from exc

    if parsed.version != 4:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Idempotency-Key header must be a valid uuid4",
                "code": "INVALID_IDEMPOTENCY_KEY",
            },
        )

    return parsed
