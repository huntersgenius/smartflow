import json
import logging
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import asyncpg
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.models.requests import OrderCreateRequest
from app.services.menu_service import get_menu


logger = logging.getLogger(__name__)

IDEMPOTENCY_TTL_SECONDS = 86400

ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["accepted", "cancelled"],
    "accepted": ["preparing", "cancelled"],
    "preparing": ["ready", "cancelled"],
    "ready": ["served"],
    "served": [],
    "cancelled": [],
}
ACTIVE_KITCHEN_STATUSES = ("pending", "accepted", "preparing", "ready")


class EmptyOrderError(Exception):
    """Raised when an order has no line items."""


class ItemUnavailableError(Exception):
    """Raised when a submitted menu item is missing or unavailable."""

    def __init__(self, menu_item_id: UUID) -> None:
        self.menu_item_id = menu_item_id
        super().__init__(str(menu_item_id))


class OrderNotFoundError(Exception):
    """Raised when an order does not exist."""


class OrderForbiddenError(Exception):
    """Raised when a guest session does not own the requested order."""


class InvalidTransitionError(Exception):
    """Raised when an order status transition is not allowed."""

    def __init__(self, old_status: str, new_status: str) -> None:
        self.old_status = old_status
        self.new_status = new_status
        super().__init__(f"Transition from {old_status} to {new_status} is not allowed")


async def create_order(
    request_data: OrderCreateRequest,
    session: dict[str, Any],
    idempotency_key: UUID,
    db: asyncpg.Connection,
    redis: Redis,
) -> dict[str, Any]:
    if not request_data.items:
        raise EmptyOrderError()

    idem_key = f"idem:{idempotency_key}"
    cached_result = await redis.get(idem_key)
    if cached_result:
        return json.loads(cached_result)

    menu = await get_menu(int(session["branch_id"]), db, redis)
    item_map = {
        str(item["id"]): item
        for category in menu["categories"]
        for item in category["items"]
    }

    total = Decimal("0.00")
    order_items: list[tuple[UUID, int, Decimal, str | None]] = []
    for item in request_data.items:
        menu_item = item_map.get(str(item.menu_item_id))
        if menu_item is None:
            raise ItemUnavailableError(item.menu_item_id)

        unit_price = Decimal(str(menu_item["price"]))
        total += unit_price * item.quantity
        order_items.append((item.menu_item_id, item.quantity, unit_price, item.notes))

    branch_id = int(session["branch_id"])
    table_id = int(session["table_id"])
    session_id = UUID(str(session["session_id"]))
    table_code = await _get_table_code(table_id, branch_id, db)
    order_id = uuid4()
    created_new_order = False
    created_at = ""
    result: dict[str, Any]

    async with db.transaction():
        order_row = await db.fetchrow(
            """
            INSERT INTO orders
                (id, branch_id, table_id, session_id, idempotency_key, status, total, note)
            VALUES ($1, $2, $3, $4, $5, 'pending', $6, $7)
            ON CONFLICT (session_id, idempotency_key) DO NOTHING
            RETURNING id, status, total, created_at
            """,
            order_id,
            branch_id,
            table_id,
            session_id,
            idempotency_key,
            total,
            request_data.note,
        )

        if order_row is None:
            order_row = await db.fetchrow(
                """
                SELECT id, status, total, created_at
                FROM orders
                WHERE session_id = $1 AND idempotency_key = $2
                """,
                session_id,
                idempotency_key,
            )
            if order_row is None:
                raise RuntimeError("Unable to resolve idempotent order")
        else:
            created_new_order = True
            await db.executemany(
                """
                INSERT INTO order_items (order_id, menu_item_id, quantity, unit_price, notes)
                VALUES ($1, $2, $3, $4, $5)
                """,
                [
                    (order_row["id"], menu_item_id, quantity, unit_price, notes)
                    for menu_item_id, quantity, unit_price, notes in order_items
                ],
            )
            await db.execute(
                """
                INSERT INTO order_status_history (order_id, status, changed_by)
                VALUES ($1, 'pending', 'guest')
                """,
                order_row["id"],
            )

        created_at = _format_timestamp(order_row["created_at"])
        result = {
            "order_id": str(order_row["id"]),
            "status": str(order_row["status"]),
            "total": _format_money(order_row["total"]),
        }

    if created_new_order:
        event = _build_new_order_event(
            order_id=result["order_id"],
            branch_id=branch_id,
            table_id=table_id,
            table_code=table_code,
            request_data=request_data,
            item_map=item_map,
            total=result["total"],
            created_at=created_at,
        )
        await _publish_json(redis, f"kitchen:{branch_id}", event)

    await _cache_idempotency_result(redis, idem_key, result)
    return result


async def get_order_detail(
    order_id: UUID,
    session: dict[str, Any],
    db: asyncpg.Connection,
) -> dict[str, Any]:
    order_row = await db.fetchrow(
        """
        SELECT id, session_id, status, total, created_at
        FROM orders
        WHERE id = $1
        """,
        order_id,
    )
    if order_row is None:
        raise OrderNotFoundError()

    if str(order_row["session_id"]) != str(session["session_id"]):
        raise OrderForbiddenError()

    item_rows = await db.fetch(
        """
        SELECT
            oi.menu_item_id,
            mi.name,
            oi.quantity,
            oi.unit_price,
            oi.notes
        FROM order_items oi
        JOIN menu_items mi ON mi.id = oi.menu_item_id
        WHERE oi.order_id = $1
        ORDER BY oi.id
        """,
        order_id,
    )
    history_rows = await db.fetch(
        """
        SELECT status, changed_by, changed_at, note
        FROM order_status_history
        WHERE order_id = $1
        ORDER BY changed_at, id
        """,
        order_id,
    )

    return {
        "order_id": str(order_row["id"]),
        "status": str(order_row["status"]),
        "total": _format_money(order_row["total"]),
        "items": [
            {
                "menu_item_id": str(row["menu_item_id"]),
                "name": row["name"],
                "quantity": row["quantity"],
                "unit_price": _format_money(row["unit_price"]),
                "notes": row["notes"],
            }
            for row in item_rows
        ],
        "created_at": _format_timestamp(order_row["created_at"]),
        "history": [
            {
                "status": str(row["status"]),
                "changed_by": row["changed_by"],
                "changed_at": _format_timestamp(row["changed_at"]),
                "note": row["note"],
            }
            for row in history_rows
        ],
    }


async def list_kitchen_orders(
    branch_id: int,
    status_filter: str | None,
    db: asyncpg.Connection,
) -> dict[str, Any]:
    statuses = [status_filter] if status_filter else list(ACTIVE_KITCHEN_STATUSES)
    rows = await db.fetch(
        """
        SELECT
            o.id AS order_id,
            dt.table_code,
            o.status,
            o.total,
            o.created_at,
            oi.id AS order_item_id,
            oi.menu_item_id,
            mi.name AS item_name,
            oi.quantity,
            oi.unit_price,
            oi.notes
        FROM orders o
        JOIN dining_tables dt ON dt.id = o.table_id
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN menu_items mi ON mi.id = oi.menu_item_id
        WHERE o.branch_id = $1
          AND o.status::text = ANY($2::text[])
        ORDER BY o.created_at ASC, oi.id ASC
        """,
        branch_id,
        statuses,
    )

    orders_by_id: dict[UUID, dict[str, Any]] = {}
    orders: list[dict[str, Any]] = []

    for row in rows:
        order = orders_by_id.get(row["order_id"])
        if order is None:
            order = {
                "order_id": str(row["order_id"]),
                "table_code": row["table_code"],
                "status": str(row["status"]),
                "total": _format_money(row["total"]),
                "items": [],
                "created_at": _format_timestamp(row["created_at"]),
            }
            orders_by_id[row["order_id"]] = order
            orders.append(order)

        if row["order_item_id"] is None:
            continue

        order["items"].append(
            {
                "menu_item_id": str(row["menu_item_id"]),
                "name": row["item_name"],
                "quantity": row["quantity"],
                "unit_price": _format_money(row["unit_price"]),
                "notes": row["notes"],
            }
        )

    return {"orders": orders}


async def update_status(
    order_id: UUID,
    new_status: str,
    note: str | None,
    session: dict[str, Any],
    db: asyncpg.Connection,
    redis: Redis,
) -> dict[str, Any]:
    branch_id = int(session["branch_id"])
    changed_by = f"staff:{session.get('user_id', 'unknown')}"
    event: dict[str, Any] | None = None
    result: dict[str, Any]

    async with db.transaction():
        order_row = await db.fetchrow(
            """
            SELECT
                o.id,
                o.status,
                o.branch_id,
                o.table_id,
                dt.table_code
            FROM orders o
            JOIN dining_tables dt ON dt.id = o.table_id
            WHERE o.id = $1 AND o.branch_id = $2
            FOR UPDATE OF o
            """,
            order_id,
            branch_id,
        )
        if order_row is None:
            raise OrderNotFoundError()

        old_status = str(order_row["status"])
        if new_status not in ALLOWED_TRANSITIONS.get(old_status, []):
            raise InvalidTransitionError(old_status, new_status)

        await db.execute(
            """
            UPDATE orders
            SET status = $2::order_status, updated_at = now()
            WHERE id = $1
            """,
            order_id,
            new_status,
        )
        history_row = await db.fetchrow(
            """
            INSERT INTO order_status_history (order_id, status, changed_by, note)
            VALUES ($1, $2::order_status, $3, $4)
            RETURNING changed_at
            """,
            order_id,
            new_status,
            changed_by,
            note,
        )

        result = {
            "order_id": str(order_id),
            "old_status": old_status,
            "new_status": new_status,
        }
        event = _build_status_event(
            order_id=str(order_id),
            branch_id=branch_id,
            table_code=order_row["table_code"],
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            changed_at=_format_timestamp(history_row["changed_at"]),
        )

    if event is not None:
        await _publish_json(redis, f"kitchen:{branch_id}", event)
        await _publish_json(redis, f"order:{order_id}", event)

    return result


async def _get_table_code(table_id: int, branch_id: int, db: asyncpg.Connection) -> str:
    table_code = await db.fetchval(
        """
        SELECT table_code
        FROM dining_tables
        WHERE id = $1 AND branch_id = $2
        """,
        table_id,
        branch_id,
    )
    if table_code is None:
        raise RuntimeError("Order table not found")
    return table_code


async def _publish_json(redis: Redis, channel: str, event: dict[str, Any]) -> None:
    try:
        await redis.publish(channel, json.dumps(event, default=str))
    except RedisError:
        logger.exception("order_event_publish_failed", extra={"channel": channel})


async def _cache_idempotency_result(
    redis: Redis,
    cache_key: str,
    result: dict[str, Any],
) -> None:
    try:
        await redis.setex(cache_key, IDEMPOTENCY_TTL_SECONDS, json.dumps(result))
    except RedisError:
        logger.exception("order_idempotency_cache_failed", extra={"cache_key": cache_key})


def _build_new_order_event(
    *,
    order_id: str,
    branch_id: int,
    table_id: int,
    table_code: str,
    request_data: OrderCreateRequest,
    item_map: dict[str, dict[str, Any]],
    total: str,
    created_at: str,
) -> dict[str, Any]:
    return _event_envelope(
        "new_order",
        branch_id,
        {
            "order_id": order_id,
            "table_code": table_code,
            "table_id": table_id,
            "total": total,
            "items": [
                {
                    "name": item_map[str(item.menu_item_id)]["name"],
                    "qty": item.quantity,
                    "notes": item.notes,
                }
                for item in request_data.items
            ],
            "note": request_data.note,
            "created_at": created_at,
        },
    )


def _build_status_event(
    *,
    order_id: str,
    branch_id: int,
    table_code: str,
    old_status: str,
    new_status: str,
    changed_by: str,
    changed_at: str,
) -> dict[str, Any]:
    event_type = "order_status_changed"
    if new_status == "ready":
        event_type = "order_ready"
    elif new_status == "cancelled":
        event_type = "order_cancelled"

    return _event_envelope(
        event_type,
        branch_id,
        {
            "order_id": order_id,
            "table_code": table_code,
            "old_status": old_status,
            "new_status": new_status,
            "changed_by": changed_by,
            "changed_at": changed_at,
        },
    )


def _event_envelope(event_type: str, branch_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "event_id": str(int(time.time() * 1000)),
        "timestamp": _format_timestamp(datetime.now(UTC)),
        "branch_id": branch_id,
        "payload": payload,
    }


def _format_money(value: Decimal) -> str:
    return f"{value:.2f}"


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
