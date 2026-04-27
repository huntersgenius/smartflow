from typing import Any

from fastapi import Depends, HTTPException, Request


async def get_session(request: Request) -> dict[str, Any] | None:
    """Returns session dict or None. Never raises."""
    return getattr(request.state, "session", None)


async def require_guest_session(
    session: dict[str, Any] | None = Depends(get_session),
) -> dict[str, Any]:
    """Raises 401 if no session. Raises 403 if role != 'guest'."""
    if session is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "Authentication required", "code": "AUTH_REQUIRED"},
        )
    if session.get("role") != "guest":
        raise HTTPException(
            status_code=403,
            detail={"error": "Guest session required", "code": "GUEST_SESSION_REQUIRED"},
        )
    return session


async def require_staff_session(
    session: dict[str, Any] | None = Depends(get_session),
) -> dict[str, Any]:
    """Raises 401 if no session. Raises 403 if role not in ('kitchen','admin')."""
    if session is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "Authentication required", "code": "AUTH_REQUIRED"},
        )
    if session.get("role") not in ("kitchen", "admin"):
        raise HTTPException(
            status_code=403,
            detail={"error": "Staff session required", "code": "STAFF_SESSION_REQUIRED"},
        )
    return session


async def require_kitchen_role(
    session: dict[str, Any] | None = Depends(get_session),
) -> dict[str, Any]:
    """Raises 401 if no session. Raises 403 if role not in ('kitchen','admin')."""
    if session is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "Authentication required", "code": "AUTH_REQUIRED"},
        )
    if session.get("role") not in ("kitchen", "admin"):
        raise HTTPException(
            status_code=403,
            detail={"error": "Kitchen role required", "code": "KITCHEN_ROLE_REQUIRED"},
        )
    return session


async def require_admin_role(
    session: dict[str, Any] | None = Depends(get_session),
) -> dict[str, Any]:
    """Raises 401 if no session. Raises 403 if role != 'admin'."""
    if session is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "Authentication required", "code": "AUTH_REQUIRED"},
        )
    if session.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail={"error": "Admin role required", "code": "ADMIN_ROLE_REQUIRED"},
        )
    return session
