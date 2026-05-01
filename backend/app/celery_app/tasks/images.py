import asyncio
import io
import logging
from pathlib import PurePath
from typing import Any
from urllib.parse import quote
from uuid import UUID

from botocore.exceptions import BotoCoreError, ClientError

from app.celery_app.worker import app
from app.config import get_settings
from app.database import close_db_pool, create_db_pool
from app.services.storage_service import StorageService


logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 15 * 1024 * 1024
THUMBNAIL_SIZE = (512, 512)


@app.task(
    name="process_menu_image",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def process_menu_image(self, s3_key: str, menu_item_id: str) -> dict[str, Any]:
    storage = StorageService()
    try:
        result = _process_image_object(storage, s3_key, menu_item_id)
    except (BotoCoreError, ClientError, OSError, ValueError):
        logger.exception(
            "menu_image_processing_failed",
            extra={"s3_key": s3_key, "menu_item_id": menu_item_id},
        )
        raise

    asyncio.run(
        _update_menu_item_image_urls(
            menu_item_id=menu_item_id,
            image_url=result["image_url"],
            thumbnail_url=result["thumbnail_url"],
        )
    )
    logger.info(
        "menu_image_processing_complete",
        extra={
            "s3_key": s3_key,
            "menu_item_id": menu_item_id,
            "thumbnail_key": result["thumbnail_key"],
            "mode": result["mode"],
        },
    )
    return result


def _process_image_object(
    storage: StorageService,
    s3_key: str,
    menu_item_id: str,
) -> dict[str, Any]:
    head = storage.client.head_object(
        Bucket=storage.settings.S3_BUCKET_NAME,
        Key=s3_key,
    )
    content_type = head.get("ContentType") or "application/octet-stream"
    content_length = int(head.get("ContentLength") or 0)
    if not content_type.startswith("image/"):
        raise ValueError("S3 object is not an image")

    thumbnail_key = _thumbnail_key(s3_key, menu_item_id)
    mode = _try_resize_with_pillow(
        storage,
        s3_key=s3_key,
        thumbnail_key=thumbnail_key,
        content_type=content_type,
        content_length=content_length,
    )
    if mode is None:
        _copy_original_as_thumbnail(storage, s3_key, thumbnail_key, content_type)
        mode = "copy"

    return {
        "menu_item_id": menu_item_id,
        "s3_key": s3_key,
        "image_url": storage.get_url(s3_key),
        "thumbnail_key": thumbnail_key,
        "thumbnail_url": storage.get_url(thumbnail_key),
        "mode": mode,
    }


def _try_resize_with_pillow(
    storage: StorageService,
    *,
    s3_key: str,
    thumbnail_key: str,
    content_type: str,
    content_length: int,
) -> str | None:
    try:
        from PIL import Image
    except ImportError:
        return None

    if content_length <= 0 or content_length > MAX_IMAGE_BYTES:
        raise ValueError("Image is too large to resize safely")

    response = storage.client.get_object(
        Bucket=storage.settings.S3_BUCKET_NAME,
        Key=s3_key,
    )
    stream = response["Body"]
    try:
        body = stream.read(MAX_IMAGE_BYTES + 1)
    finally:
        stream.close()
    if len(body) > MAX_IMAGE_BYTES:
        raise ValueError("Image is too large to resize safely")

    with Image.open(io.BytesIO(body)) as image:
        image.thumbnail(THUMBNAIL_SIZE)
        output = io.BytesIO()
        output_format = "PNG" if content_type == "image/png" else "JPEG"
        save_kwargs: dict[str, Any] = {}
        if output_format == "JPEG":
            image = image.convert("RGB")
            save_kwargs.update({"quality": 85, "optimize": True})
        image.save(output, format=output_format, **save_kwargs)
        output.seek(0)

    storage.client.put_object(
        Bucket=storage.settings.S3_BUCKET_NAME,
        Key=thumbnail_key,
        Body=output.getvalue(),
        ContentType="image/png" if output_format == "PNG" else "image/jpeg",
    )
    return "resize"


def _copy_original_as_thumbnail(
    storage: StorageService,
    s3_key: str,
    thumbnail_key: str,
    content_type: str,
) -> None:
    storage.client.copy_object(
        Bucket=storage.settings.S3_BUCKET_NAME,
        CopySource={
            "Bucket": storage.settings.S3_BUCKET_NAME,
            "Key": s3_key,
        },
        Key=thumbnail_key,
        ContentType=content_type,
        MetadataDirective="REPLACE",
    )


async def _update_menu_item_image_urls(
    *,
    menu_item_id: str,
    image_url: str,
    thumbnail_url: str,
) -> None:
    settings = get_settings()
    db_pool = await create_db_pool(settings)
    try:
        async with db_pool.acquire() as db:
            row = await db.fetchrow(
                """
                UPDATE menu_items
                SET image_url = $2,
                    thumbnail_url = $3,
                    updated_at = now()
                WHERE id = $1
                RETURNING branch_id
                """,
                UUID(menu_item_id),
                image_url,
                thumbnail_url,
            )
            if row is None:
                raise ValueError("Menu item not found")
            branch_id = int(row["branch_id"])

        await _invalidate_menu_cache(settings.REDIS_URL, branch_id)
    finally:
        await close_db_pool(db_pool)


async def _invalidate_menu_cache(redis_url: str, branch_id: int) -> None:
    import redis.asyncio as redis

    client = redis.from_url(
        redis_url,
        decode_responses=True,
        health_check_interval=30,
    )
    try:
        await client.delete(f"menu:branch:{branch_id}")
    finally:
        await client.aclose()


def _thumbnail_key(s3_key: str, menu_item_id: str) -> str:
    suffix = PurePath(s3_key).suffix.lower() or ".jpg"
    return f"menu/items/{menu_item_id}/thumbs/{_quote_key_part(PurePath(s3_key).stem)}{suffix}"


def _quote_key_part(value: str) -> str:
    return quote(value, safe="")
