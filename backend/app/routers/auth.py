from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from redis.asyncio import Redis

from app.database import get_db
from app.dependencies import require_staff_session
from app.models.requests import StaffLoginRequest
from app.models.responses import MessageResponse, StaffLoginResponse
from app.redis_client import get_redis
from app.services.session_service import (
    STAFF_SESSION_TTL_SECONDS,
    AccountDisabledError,
    InvalidCredentialsError,
    login_staff,
    logout_staff,
)


router = APIRouter(prefix="/auth/staff", tags=["auth"])


@router.post("/login", response_model=StaffLoginResponse)
async def staff_login_endpoint(
    request_data: StaffLoginRequest,
    response: Response,
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> StaffLoginResponse:
    try:
        session = await login_staff(request_data.email, request_data.password, db, redis)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid credentials", "code": "INVALID_CREDENTIALS"},
        ) from exc
    except AccountDisabledError as exc:
        raise HTTPException(
            status_code=403,
            detail={"error": "Account disabled", "code": "ACCOUNT_DISABLED"},
        ) from exc

    response.set_cookie(
        key="ssid",
        value=session["token"],
        max_age=STAFF_SESSION_TTL_SECONDS,
        httponly=True,
        secure=False,
        samesite="lax",
    )

    return StaffLoginResponse(
        user_id=session["user_id"],
        role=session["role"],
        branch_id=session["branch_id"],
    )


@router.post("/logout", response_model=MessageResponse)
async def staff_logout_endpoint(
    request: Request,
    response: Response,
    _session: dict[str, Any] = Depends(require_staff_session),
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    token = request.cookies.get("ssid") or request.headers.get("X-Session-Token")
    if token:
        await logout_staff(token, db, redis)

    response.delete_cookie(
        key="ssid",
        httponly=True,
        secure=False,
        samesite="strict",
    )

    return MessageResponse(message="Logged out")
