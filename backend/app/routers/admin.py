import asyncio
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote
from uuid import UUID

import asyncpg
from celery import Celery
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from redis.asyncio import Redis

from app.config import get_settings
from app.database import get_db
from app.dependencies import require_admin_role
from app.redis_client import get_redis
from app.services.menu_service import invalidate_menu_cache
from app.services.storage_service import (
    StorageError,
    StorageService,
    build_menu_image_key,
)


router = APIRouter(prefix="/admin", tags=["admin"])


class CategoryCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    image_url: str | None = None
    sort_order: int = 0
    active: bool = True


class CategoryPatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    image_url: str | None = None
    sort_order: int | None = None
    active: bool | None = None


class MenuItemCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    price: Decimal = Field(ge=Decimal("0.00"), max_digits=10, decimal_places=2)
    image_url: str | None = None
    thumbnail_url: str | None = None
    available: bool = True
    sort_order: int = 0


class MenuItemPatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    image_url: str | None = None
    thumbnail_url: str | None = None
    available: bool | None = None
    sort_order: int | None = None


class TableCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    table_code: str = Field(min_length=1, max_length=50)
    label: str = Field(min_length=1, max_length=50)
    active: bool = True
    qr_image_url: str | None = None


class TablePatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    label: str | None = Field(default=None, min_length=1, max_length=50)
    active: bool | None = None


@router.get("/categories")
async def list_categories_endpoint(
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
) -> dict[str, Any]:
    rows = await db.fetch(
        """
        SELECT id, branch_id, name, description, image_url, sort_order, active, created_at
        FROM menu_categories
        WHERE branch_id = $1
        ORDER BY sort_order, id
        """,
        int(session["branch_id"]),
    )
    return {"categories": [_category_response(row) for row in rows]}


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category_endpoint(
    request_data: CategoryCreateRequest,
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    branch_id = int(session["branch_id"])
    row = await db.fetchrow(
        """
        INSERT INTO menu_categories
            (branch_id, name, description, image_url, sort_order, active)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, branch_id, name, description, image_url, sort_order, active, created_at
        """,
        branch_id,
        request_data.name,
        request_data.description,
        request_data.image_url,
        request_data.sort_order,
        request_data.active,
    )
    await invalidate_menu_cache(branch_id, redis)
    return _category_response(row)


@router.patch("/categories/{category_id}")
async def update_category_endpoint(
    category_id: int,
    request_data: CategoryPatchRequest,
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    branch_id = int(session["branch_id"])
    _reject_null_fields(request_data, {"name", "sort_order", "active"})

    values = _model_update_values(
        request_data,
        ("name", "description", "image_url", "sort_order", "active"),
    )
    if not values:
        row = await _fetch_category(category_id, branch_id, db)
        return _category_response(row)

    row = await _update_with_returning(
        db,
        table="menu_categories",
        values=values,
        where="id = ${id_param} AND branch_id = ${branch_param}",
        where_args=(category_id, branch_id),
        returning="id, branch_id, name, description, image_url, sort_order, active, created_at",
    )
    if row is None:
        raise _not_found("Category not found", "CATEGORY_NOT_FOUND")

    await invalidate_menu_cache(branch_id, redis)
    return _category_response(row)


@router.delete("/categories/{category_id}")
async def delete_category_endpoint(
    category_id: int,
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    branch_id = int(session["branch_id"])
    result = await db.execute(
        """
        UPDATE menu_categories
        SET active = false
        WHERE id = $1 AND branch_id = $2
        """,
        category_id,
        branch_id,
    )
    if _affected_rows(result) == 0:
        raise _not_found("Category not found", "CATEGORY_NOT_FOUND")

    await invalidate_menu_cache(branch_id, redis)
    return {"message": "Category deleted"}


@router.get("/menu-items")
async def list_menu_items_endpoint(
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
) -> dict[str, Any]:
    rows = await db.fetch(
        """
        SELECT
            mi.id,
            mi.category_id,
            mi.branch_id,
            mc.name AS category_name,
            mi.name,
            mi.description,
            mi.price,
            mi.image_url,
            mi.thumbnail_url,
            mi.available,
            mi.sort_order,
            mi.created_at,
            mi.updated_at
        FROM menu_items mi
        JOIN menu_categories mc ON mc.id = mi.category_id
        WHERE mi.branch_id = $1
        ORDER BY mc.sort_order, mi.sort_order, mi.created_at
        """,
        int(session["branch_id"]),
    )
    return {"items": [_menu_item_response(row) for row in rows]}


@router.post("/menu-items", status_code=status.HTTP_201_CREATED)
async def create_menu_item_endpoint(
    request_data: MenuItemCreateRequest,
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    branch_id = int(session["branch_id"])
    await _ensure_category_belongs_to_branch(request_data.category_id, branch_id, db)

    row = await db.fetchrow(
        """
        INSERT INTO menu_items
            (
                category_id,
                branch_id,
                name,
                description,
                price,
                image_url,
                thumbnail_url,
                available,
                sort_order
            )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING
            id,
            category_id,
            branch_id,
            NULL::varchar AS category_name,
            name,
            description,
            price,
            image_url,
            thumbnail_url,
            available,
            sort_order,
            created_at,
            updated_at
        """,
        request_data.category_id,
        branch_id,
        request_data.name,
        request_data.description,
        request_data.price,
        request_data.image_url,
        request_data.thumbnail_url,
        request_data.available,
        request_data.sort_order,
    )
    row = await _fetch_menu_item(row["id"], branch_id, db)
    await invalidate_menu_cache(branch_id, redis)
    return _menu_item_response(row)


@router.patch("/menu-items/{menu_item_id}")
async def update_menu_item_endpoint(
    menu_item_id: UUID,
    request_data: MenuItemPatchRequest,
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    branch_id = int(session["branch_id"])
    _reject_null_fields(
        request_data,
        {"category_id", "name", "price", "available", "sort_order"},
    )

    if "category_id" in request_data.model_fields_set and request_data.category_id is not None:
        await _ensure_category_belongs_to_branch(request_data.category_id, branch_id, db)

    values = _model_update_values(
        request_data,
        (
            "category_id",
            "name",
            "description",
            "price",
            "image_url",
            "thumbnail_url",
            "available",
            "sort_order",
        ),
    )
    if not values:
        row = await _fetch_menu_item(menu_item_id, branch_id, db)
        return _menu_item_response(row)

    values["updated_at"] = _RawSQL("now()")
    row = await _update_with_returning(
        db,
        table="menu_items",
        values=values,
        where="id = ${id_param} AND branch_id = ${branch_param}",
        where_args=(menu_item_id, branch_id),
        returning=(
            "id, category_id, branch_id, NULL::varchar AS category_name, name, "
            "description, price, image_url, thumbnail_url, available, sort_order, "
            "created_at, updated_at"
        ),
    )
    if row is None:
        raise _not_found("Menu item not found", "MENU_ITEM_NOT_FOUND")

    row = await _fetch_menu_item(menu_item_id, branch_id, db)
    await invalidate_menu_cache(branch_id, redis)
    return _menu_item_response(row)


@router.delete("/menu-items/{menu_item_id}")
async def delete_menu_item_endpoint(
    menu_item_id: UUID,
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    branch_id = int(session["branch_id"])
    result = await db.execute(
        """
        UPDATE menu_items
        SET available = false, updated_at = now()
        WHERE id = $1 AND branch_id = $2
        """,
        menu_item_id,
        branch_id,
    )
    if _affected_rows(result) == 0:
        raise _not_found("Menu item not found", "MENU_ITEM_NOT_FOUND")

    await invalidate_menu_cache(branch_id, redis)
    return {"message": "Menu item deleted"}


@router.post("/menu-items/{menu_item_id}/image")
async def upload_menu_item_image_endpoint(
    menu_item_id: UUID,
    file: UploadFile = File(...),
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, Any]:
    branch_id = int(session["branch_id"])
    await _fetch_menu_item(menu_item_id, branch_id, db)

    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail={"error": "Uploaded file must be an image", "code": "INVALID_IMAGE"},
        )

    s3_key = build_menu_image_key(str(menu_item_id), file.filename, content_type)
    storage = StorageService()
    try:
        await file.seek(0)
        uploaded = await storage.upload_fileobj(file.file, s3_key, content_type)
    except StorageError as exc:
        raise HTTPException(
            status_code=502,
            detail={"error": "Image upload failed", "code": "IMAGE_UPLOAD_FAILED"},
        ) from exc
    finally:
        await file.close()

    await db.execute(
        """
        UPDATE menu_items
        SET image_url = $2, updated_at = now()
        WHERE id = $1 AND branch_id = $3
        """,
        menu_item_id,
        uploaded.url,
        branch_id,
    )
    await invalidate_menu_cache(branch_id, redis)
    try:
        await _dispatch_process_menu_image(s3_key, str(menu_item_id))
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "Image processing dispatch failed",
                "code": "IMAGE_PROCESSING_DISPATCH_FAILED",
            },
        ) from exc

    return {
        "menu_item_id": str(menu_item_id),
        "s3_key": uploaded.s3_key,
        "image_url": uploaded.url,
        "presigned_url": uploaded.presigned_url,
    }


@router.get("/tables")
async def list_tables_endpoint(
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
) -> dict[str, Any]:
    rows = await db.fetch(
        """
        SELECT id, branch_id, table_code, label, active, qr_image_url, created_at
        FROM dining_tables
        WHERE branch_id = $1
        ORDER BY id
        """,
        int(session["branch_id"]),
    )
    return {"tables": [_table_response(row) for row in rows]}


@router.post("/tables", status_code=status.HTTP_201_CREATED)
async def create_table_endpoint(
    request_data: TableCreateRequest,
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
) -> dict[str, Any]:
    branch_id = int(session["branch_id"])
    qr_image_url = request_data.qr_image_url or _build_qr_image_url(request_data.table_code)
    try:
        row = await db.fetchrow(
            """
            INSERT INTO dining_tables (branch_id, table_code, label, active, qr_image_url)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, branch_id, table_code, label, active, qr_image_url, created_at
            """,
            branch_id,
            request_data.table_code,
            request_data.label,
            request_data.active,
            qr_image_url,
        )
    except asyncpg.UniqueViolationError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": "Table code already exists", "code": "TABLE_CODE_EXISTS"},
        ) from exc

    return _table_response(row)


@router.patch("/tables/{table_id}")
async def update_table_endpoint(
    table_id: int,
    request_data: TablePatchRequest,
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
) -> dict[str, Any]:
    branch_id = int(session["branch_id"])
    _reject_null_fields(request_data, {"label", "active"})

    values = _model_update_values(request_data, ("label", "active"))
    if not values:
        row = await _fetch_table(table_id, branch_id, db)
        return _table_response(row)

    row = await _update_with_returning(
        db,
        table="dining_tables",
        values=values,
        where="id = ${id_param} AND branch_id = ${branch_param}",
        where_args=(table_id, branch_id),
        returning="id, branch_id, table_code, label, active, qr_image_url, created_at",
    )
    if row is None:
        raise _not_found("Table not found", "TABLE_NOT_FOUND")

    return _table_response(row)


@router.get("/tables/{table_id}/qr")
async def get_table_qr_endpoint(
    table_id: int,
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
) -> dict[str, Any]:
    branch_id = int(session["branch_id"])
    table = await _fetch_table(table_id, branch_id, db)
    qr_image_url = table["qr_image_url"]
    if not qr_image_url:
        qr_image_url = _build_qr_image_url(table["table_code"])
        table = await db.fetchrow(
            """
            UPDATE dining_tables
            SET qr_image_url = $3
            WHERE id = $1 AND branch_id = $2
            RETURNING id, branch_id, table_code, label, active, qr_image_url, created_at
            """,
            table_id,
            branch_id,
            qr_image_url,
        )
    return {
        "table_id": table["id"],
        "table_code": table["table_code"],
        "qr_image_url": table["qr_image_url"],
    }


@router.get("/orders")
async def list_admin_orders_endpoint(
    date_filter: date = Query(alias="date"),
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
) -> dict[str, Any]:
    branch_id = int(session["branch_id"])
    start = datetime.combine(date_filter, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    rows = await db.fetch(
        """
        SELECT
            o.id AS order_id,
            o.branch_id,
            o.table_id,
            dt.table_code,
            o.status,
            o.total,
            o.note,
            o.created_at,
            o.updated_at,
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
          AND o.created_at >= $2
          AND o.created_at < $3
        ORDER BY o.created_at DESC, oi.id ASC
        """,
        branch_id,
        start,
        end,
    )
    return {"orders": _assemble_order_rows(rows)}


@router.get("/orders/{order_id}")
async def get_admin_order_endpoint(
    order_id: UUID,
    session: dict[str, Any] = Depends(require_admin_role),
    db=Depends(get_db),
) -> dict[str, Any]:
    return await _fetch_admin_order_detail(order_id, int(session["branch_id"]), db)


def _category_response(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": row["id"],
        "branch_id": row["branch_id"],
        "name": row["name"],
        "description": row["description"],
        "image_url": row["image_url"],
        "sort_order": row["sort_order"],
        "active": row["active"],
        "created_at": _format_timestamp(row["created_at"]),
    }


def _menu_item_response(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "category_id": row["category_id"],
        "branch_id": row["branch_id"],
        "category_name": row["category_name"],
        "name": row["name"],
        "description": row["description"],
        "price": _format_money(row["price"]),
        "image_url": row["image_url"],
        "thumbnail_url": row["thumbnail_url"],
        "available": row["available"],
        "sort_order": row["sort_order"],
        "created_at": _format_timestamp(row["created_at"]),
        "updated_at": _format_timestamp(row["updated_at"]),
    }


def _table_response(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": row["id"],
        "branch_id": row["branch_id"],
        "table_code": row["table_code"],
        "label": row["label"],
        "active": row["active"],
        "qr_image_url": row["qr_image_url"],
        "created_at": _format_timestamp(row["created_at"]),
    }


async def _fetch_category(category_id: int, branch_id: int, db) -> asyncpg.Record:
    row = await db.fetchrow(
        """
        SELECT id, branch_id, name, description, image_url, sort_order, active, created_at
        FROM menu_categories
        WHERE id = $1 AND branch_id = $2
        """,
        category_id,
        branch_id,
    )
    if row is None:
        raise _not_found("Category not found", "CATEGORY_NOT_FOUND")
    return row


async def _fetch_menu_item(menu_item_id: UUID, branch_id: int, db) -> asyncpg.Record:
    row = await db.fetchrow(
        """
        SELECT
            mi.id,
            mi.category_id,
            mi.branch_id,
            mc.name AS category_name,
            mi.name,
            mi.description,
            mi.price,
            mi.image_url,
            mi.thumbnail_url,
            mi.available,
            mi.sort_order,
            mi.created_at,
            mi.updated_at
        FROM menu_items mi
        JOIN menu_categories mc ON mc.id = mi.category_id
        WHERE mi.id = $1 AND mi.branch_id = $2
        """,
        menu_item_id,
        branch_id,
    )
    if row is None:
        raise _not_found("Menu item not found", "MENU_ITEM_NOT_FOUND")
    return row


async def _fetch_table(table_id: int, branch_id: int, db) -> asyncpg.Record:
    row = await db.fetchrow(
        """
        SELECT id, branch_id, table_code, label, active, qr_image_url, created_at
        FROM dining_tables
        WHERE id = $1 AND branch_id = $2
        """,
        table_id,
        branch_id,
    )
    if row is None:
        raise _not_found("Table not found", "TABLE_NOT_FOUND")
    return row


async def _ensure_category_belongs_to_branch(category_id: int, branch_id: int, db) -> None:
    exists = await db.fetchval(
        """
        SELECT true
        FROM menu_categories
        WHERE id = $1 AND branch_id = $2
        """,
        category_id,
        branch_id,
    )
    if not exists:
        raise HTTPException(
            status_code=400,
            detail={"error": "Category not found", "code": "CATEGORY_NOT_FOUND"},
        )


async def _fetch_admin_order_detail(
    order_id: UUID,
    branch_id: int,
    db,
) -> dict[str, Any]:
    order_row = await db.fetchrow(
        """
        SELECT
            o.id AS order_id,
            o.branch_id,
            o.table_id,
            dt.table_code,
            o.session_id,
            o.idempotency_key,
            o.status,
            o.total,
            o.note,
            o.created_at,
            o.updated_at
        FROM orders o
        JOIN dining_tables dt ON dt.id = o.table_id
        WHERE o.id = $1 AND o.branch_id = $2
        """,
        order_id,
        branch_id,
    )
    if order_row is None:
        raise _not_found("Order not found", "ORDER_NOT_FOUND")

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

    detail = _base_order_response(order_row)
    detail["session_id"] = str(order_row["session_id"])
    detail["idempotency_key"] = str(order_row["idempotency_key"])
    detail["items"] = [
        {
            "menu_item_id": str(row["menu_item_id"]),
            "name": row["name"],
            "quantity": row["quantity"],
            "unit_price": _format_money(row["unit_price"]),
            "notes": row["notes"],
        }
        for row in item_rows
    ]
    detail["history"] = [
        {
            "status": str(row["status"]),
            "changed_by": row["changed_by"],
            "changed_at": _format_timestamp(row["changed_at"]),
            "note": row["note"],
        }
        for row in history_rows
    ]
    return detail


def _assemble_order_rows(rows: list[asyncpg.Record]) -> list[dict[str, Any]]:
    orders_by_id: dict[UUID, dict[str, Any]] = {}
    orders: list[dict[str, Any]] = []

    for row in rows:
        order = orders_by_id.get(row["order_id"])
        if order is None:
            order = _base_order_response(row)
            order["items"] = []
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

    return orders


def _base_order_response(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "order_id": str(row["order_id"]),
        "branch_id": row["branch_id"],
        "table_id": row["table_id"],
        "table_code": row["table_code"],
        "status": str(row["status"]),
        "total": _format_money(row["total"]),
        "note": row["note"],
        "created_at": _format_timestamp(row["created_at"]),
        "updated_at": _format_timestamp(row["updated_at"]),
    }


class _RawSQL:
    def __init__(self, expression: str) -> None:
        self.expression = expression


async def _update_with_returning(
    db,
    *,
    table: str,
    values: dict[str, Any],
    where: str,
    where_args: tuple[Any, ...],
    returning: str,
) -> asyncpg.Record | None:
    args: list[Any] = []
    set_clauses: list[str] = []

    for column, value in values.items():
        if isinstance(value, _RawSQL):
            set_clauses.append(f"{column} = {value.expression}")
            continue
        args.append(value)
        set_clauses.append(f"{column} = ${len(args)}")

    id_param = len(args) + 1
    branch_param = len(args) + 2
    sql = (
        f"UPDATE {table} "
        f"SET {', '.join(set_clauses)} "
        f"WHERE {where.format(id_param=id_param, branch_param=branch_param)} "
        f"RETURNING {returning}"
    )
    args.extend(where_args)
    return await db.fetchrow(sql, *args)


def _model_update_values(model: BaseModel, fields: tuple[str, ...]) -> dict[str, Any]:
    return {
        field: getattr(model, field)
        for field in fields
        if field in model.model_fields_set
    }


def _reject_null_fields(model: BaseModel, field_names: set[str]) -> None:
    for field_name in field_names:
        if field_name in model.model_fields_set and getattr(model, field_name) is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"{field_name} must not be null",
                    "code": "INVALID_REQUEST",
                },
            )


async def _dispatch_process_menu_image(s3_key: str, menu_item_id: str) -> None:
    settings = get_settings()

    def send_task() -> None:
        celery = Celery(
            "smartflow_admin_dispatch",
            broker=settings.REDIS_URL,
            backend=settings.REDIS_URL,
        )
        celery.send_task("process_menu_image", args=[s3_key, menu_item_id])

    await asyncio.to_thread(send_task)


def _build_qr_image_url(table_code: str) -> str:
    settings = get_settings()
    return f"{settings.MEDIA_BASE_URL.rstrip('/')}/qr/{quote(table_code, safe='')}.png"


def _affected_rows(command_status: str) -> int:
    try:
        return int(command_status.rsplit(" ", 1)[-1])
    except ValueError:
        return 0


def _not_found(message: str, code: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"error": message, "code": code})


def _format_money(value: Decimal) -> str:
    return f"{value:.2f}"


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
