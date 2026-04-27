from fastapi import APIRouter, Depends, HTTPException, Response
from redis.asyncio import Redis

from app.database import get_db
from app.models.requests import GuestSessionRequest
from app.models.responses import GuestSessionResponse
from app.redis_client import get_redis
from app.services.session_service import (
    GUEST_SESSION_TTL_SECONDS,
    TableNotFoundError,
    create_guest_session,
)


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/guest", response_model=GuestSessionResponse)
async def create_guest_session_endpoint(
    request_data: GuestSessionRequest,
    response: Response,
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> GuestSessionResponse:
    try:
        session = await create_guest_session(request_data.table_code, db, redis)
    except TableNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Table not found or inactive",
                "code": "TABLE_NOT_FOUND",
            },
        ) from exc

    response.set_cookie(
        key="gsid",
        value=session["token"],
        max_age=GUEST_SESSION_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="strict",
    )

    return GuestSessionResponse(
        session_id=session["session_id"],
        expires_in=session["expires_in"],
    )
