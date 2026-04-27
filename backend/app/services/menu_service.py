import json
from decimal import Decimal
from typing import Any

import asyncpg
from redis.asyncio import Redis


MENU_CACHE_TTL_SECONDS = 300


async def get_menu(branch_id: int, db: asyncpg.Connection, redis: Redis) -> dict[str, Any]:
    cache_key = f"menu:branch:{branch_id}"

    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    rows = await db.fetch(
        """
        SELECT
            c.id AS cat_id, c.name AS cat_name, c.description AS cat_desc,
            c.image_url AS cat_image, c.sort_order AS cat_sort,
            i.id AS item_id, i.name AS item_name, i.description AS item_desc,
            i.price, i.thumbnail_url, i.image_url AS item_image,
            i.available, i.sort_order AS item_sort
        FROM menu_categories c
        LEFT JOIN menu_items i ON i.category_id = c.id AND i.available = true
        WHERE c.branch_id = $1 AND c.active = true
        ORDER BY c.sort_order, i.sort_order
        """,
        branch_id,
    )

    menu = assemble_menu_tree(branch_id, rows)
    await redis.setex(cache_key, MENU_CACHE_TTL_SECONDS, json.dumps(menu, default=str))
    return menu


def assemble_menu_tree(branch_id: int, rows: list[asyncpg.Record]) -> dict[str, Any]:
    categories_by_id: dict[int, dict[str, Any]] = {}
    categories: list[dict[str, Any]] = []

    for row in rows:
        category = categories_by_id.get(row["cat_id"])
        if category is None:
            category = {
                "id": row["cat_id"],
                "name": row["cat_name"],
                "description": row["cat_desc"],
                "image_url": row["cat_image"],
                "sort_order": row["cat_sort"],
                "items": [],
            }
            categories_by_id[row["cat_id"]] = category
            categories.append(category)

        if row["item_id"] is None:
            continue

        price = row["price"]
        if isinstance(price, Decimal):
            price = f"{price:.2f}"
        else:
            price = str(price)

        category["items"].append(
            {
                "id": str(row["item_id"]),
                "name": row["item_name"],
                "description": row["item_desc"],
                "price": price,
                "thumbnail_url": row["thumbnail_url"],
                "image_url": row["item_image"],
                "available": row["available"],
                "sort_order": row["item_sort"],
            }
        )

    return {"branch_id": branch_id, "categories": categories}


async def invalidate_menu_cache(branch_id: int, redis: Redis) -> None:
    await redis.delete(f"menu:branch:{branch_id}")
