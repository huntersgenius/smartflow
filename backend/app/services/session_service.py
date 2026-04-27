import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg
from redis.asyncio import Redis


GUEST_SESSION_TTL_SECONDS = 14400


class TableNotFoundError(Exception):
    """Raised when a submitted table code is missing or inactive."""


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
