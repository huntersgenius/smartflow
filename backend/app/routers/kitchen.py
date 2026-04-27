from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from redis.asyncio import Redis
from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.dependencies import require_kitchen_role
from app.models.requests import OrderStatusUpdateRequest
from app.models.responses import KitchenOrdersResponse, OrderStatusUpdateResponse
from app.redis_client import get_redis
from app.services.order_service import (
    InvalidTransitionError,
    OrderNotFoundError,
    list_kitchen_orders,
    update_status,
)
from app.services.realtime_service import redis_sse_stream


KitchenStatusFilter = Literal["pending", "accepted", "preparing", "ready"]

router = APIRouter(prefix="/kitchen", tags=["kitchen"])


@router.get("/orders", response_model=KitchenOrdersResponse)
async def kitchen_orders_endpoint(
    status_filter: KitchenStatusFilter | None = Query(default=None, alias="status"),
    session: dict[str, Any] = Depends(require_kitchen_role),
    db=Depends(get_db),
) -> dict[str, Any]:
    return await list_kitchen_orders(
        int(session["branch_id"]),
        status_filter,
        db,
    )


@router.patch(
    "/orders/{order_id}/status",
    response_model=OrderStatusUpdateResponse,
)
async def update_order_status_endpoint(
    order_id: UUID,
    request_data: OrderStatusUpdateRequest,
    session: dict[str, Any] = Depends(require_kitchen_role),
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    try:
        return await update_status(
            order_id,
            request_data.status,
            request_data.note,
            session,
            db,
            redis,
        )
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Transition from {exc.old_status} to {exc.new_status} is not allowed",
                "code": "INVALID_TRANSITION",
            },
        ) from exc
    except OrderNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "Order not found", "code": "ORDER_NOT_FOUND"},
        ) from exc


@router.get("/stream", response_model=None)
async def kitchen_stream_endpoint(
    request: Request,
    session: dict[str, Any] = Depends(require_kitchen_role),
    redis: Redis = Depends(get_redis),
) -> EventSourceResponse:
    branch_id = int(session["branch_id"])
    return EventSourceResponse(
        redis_sse_stream(request, redis, f"kitchen:{branch_id}", branch_id),
        ping=15,
    )
