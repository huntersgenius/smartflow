from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis

from app.database import get_db
from app.dependencies import get_session
from app.models.responses import MenuResponse
from app.redis_client import get_redis
from app.services.menu_service import get_menu


router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("", response_model=MenuResponse)
async def menu_endpoint(
    branch_id: int = Query(gt=0),
    session: dict[str, Any] | None = Depends(get_session),
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    if session is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "Authentication required", "code": "AUTH_REQUIRED"},
        )

    if session.get("role") not in ("guest", "kitchen", "admin"):
        raise HTTPException(
            status_code=403,
            detail={"error": "Session is not allowed", "code": "SESSION_FORBIDDEN"},
        )

    if int(session["branch_id"]) != branch_id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Menu does not belong to this session branch",
                "code": "MENU_FORBIDDEN",
            },
        )

    return await get_menu(branch_id, db, redis)
