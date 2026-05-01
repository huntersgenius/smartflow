import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
import bcrypt
from redis.asyncio import Redis


GUEST_SESSION_TTL_SECONDS = 14400
STAFF_SESSION_TTL_SECONDS = 86400


class TableNotFoundError(Exception):
    """Raised when a submitted table code is missing or inactive."""


class InvalidCredentialsError(Exception):
    """Raised when staff login credentials do not match an active user."""


class AccountDisabledError(Exception):
    """Raised when staff credentials match a disabled account."""


async def create_guest_session(
    table_code: str,
    db: asyncpg.Connection,
    redis: Redis,
) -> dict[str, Any]:
    table = await db.fetchrow(
        """
        SELECT dt.id AS table_id, dt.branch_id
        FROM dining_tables dt
        JOIN branches b ON b.id = dt.branch_id
        WHERE dt.table_code = $1
          AND dt.active = true
          AND b.active = true
        """,
        table_code,
    )
    if table is None:
        raise TableNotFoundError()

    expires_at = datetime.now(UTC) + timedelta(seconds=GUEST_SESSION_TTL_SECONDS)
    token = ""
    session_id = None

    for _ in range(5):
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            session_id = await db.fetchval(
                """
                INSERT INTO guest_sessions (token_hash, table_id, branch_id, expires_at)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                token_hash,
                table["table_id"],
                table["branch_id"],
                expires_at,
            )
            break
        except asyncpg.UniqueViolationError:
            continue

    if session_id is None:
        raise RuntimeError("Unable to create a unique guest session")

    session_data = {
        "role": "guest",
        "session_id": str(session_id),
        "table_id": table["table_id"],
        "branch_id": table["branch_id"],
        "expires_at": expires_at.isoformat(),
    }
    await redis.setex(
        f"guest:{token}",
        GUEST_SESSION_TTL_SECONDS,
        json.dumps(session_data, default=str),
    )

    return {
        "token": token,
        "session_id": str(session_id),
        "expires_in": GUEST_SESSION_TTL_SECONDS,
        "table_id": table["table_id"],
        "branch_id": table["branch_id"],
    }


async def login_staff(
    email: str,
    password: str,
    db: asyncpg.Connection,
    redis: Redis,
) -> dict[str, Any]:
    user = await db.fetchrow(
        """
        SELECT id, branch_id, password_hash, role, active
        FROM staff_users
        WHERE lower(email) = lower($1)
        """,
        email,
    )
    if user is None:
        raise InvalidCredentialsError()

    if not _check_password(password, user["password_hash"]):
        raise InvalidCredentialsError()

    if not user["active"]:
        raise AccountDisabledError()

    expires_at = datetime.now(UTC) + timedelta(seconds=STAFF_SESSION_TTL_SECONDS)
    token = ""
    session_id = None

    for _ in range(5):
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            session_id = await db.fetchval(
                """
                INSERT INTO staff_sessions (token_hash, user_id, branch_id, role, expires_at)
                VALUES ($1, $2, $3, $4::staff_role, $5)
                RETURNING id
                """,
                token_hash,
                user["id"],
                user["branch_id"],
                str(user["role"]),
                expires_at,
            )
            break
        except asyncpg.UniqueViolationError:
            continue

    if session_id is None:
        raise RuntimeError("Unable to create a unique staff session")

    session_data = {
        "role": str(user["role"]),
        "session_id": str(session_id),
        "user_id": user["id"],
        "branch_id": user["branch_id"],
        "expires_at": expires_at.isoformat(),
    }
    await redis.setex(
        f"staff:{token}",
        STAFF_SESSION_TTL_SECONDS,
        json.dumps(session_data, default=str),
    )

    return {
        "token": token,
        "user_id": user["id"],
        "role": str(user["role"]),
        "branch_id": user["branch_id"],
        "expires_in": STAFF_SESSION_TTL_SECONDS,
    }


async def logout_staff(
    token: str,
    db: asyncpg.Connection,
    redis: Redis,
) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    await db.execute(
        """
        DELETE FROM staff_sessions
        WHERE token_hash = $1
        """,
        token_hash,
    )
    await redis.delete(f"staff:{token}")


def _check_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False
