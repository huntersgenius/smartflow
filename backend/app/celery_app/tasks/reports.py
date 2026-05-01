import asyncio
import json
import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from app.celery_app.worker import app
from app.config import Settings, get_settings
from app.database import close_db_pool, create_db_pool
from app.services.storage_service import StorageService


logger = logging.getLogger(__name__)


@app.task(name="app.celery_app.tasks.reports.generate_daily_reports")
def generate_daily_reports(report_date: str | None = None) -> dict[str, Any]:
    return asyncio.run(_generate_daily_reports(report_date))


async def _generate_daily_reports(report_date: str | None) -> dict[str, Any]:
    settings = get_settings()
    target_date = _parse_report_date(report_date)
    report = await _build_daily_report(settings, target_date)

    storage_key: str | None = None
    storage_error: str | None = None
    if _storage_is_configured(settings):
        try:
            storage_key = await asyncio.to_thread(_store_report, settings, report)
        except (BotoCoreError, ClientError, OSError) as exc:
            storage_error = exc.__class__.__name__
            logger.exception(
                "daily_report_storage_failed",
                extra={"report_date": target_date.isoformat()},
            )

    result = {
        "report_date": target_date.isoformat(),
        "branches": report["branches"],
        "storage_key": storage_key,
        "storage_error": storage_error,
    }
    logger.info(
        "daily_report_generation_complete",
        extra={
            "report_date": target_date.isoformat(),
            "branch_count": len(report["branches"]),
            "storage_key": storage_key,
        },
    )
    return result


async def _build_daily_report(settings: Settings, target_date: date) -> dict[str, Any]:
    start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=UTC)
    end = start + timedelta(days=1)
    db_pool = await create_db_pool(settings)
    try:
        async with db_pool.acquire() as db:
            rows = await db.fetch(
                """
                SELECT
                    b.id AS branch_id,
                    b.name AS branch_name,
                    count(o.id) AS order_count,
                    coalesce(sum(o.total), 0)::numeric(10, 2) AS gross_total,
                    count(o.id) FILTER (WHERE o.status = 'served') AS served_count,
                    count(o.id) FILTER (WHERE o.status = 'cancelled') AS cancelled_count,
                    count(o.id) FILTER (
                        WHERE o.status NOT IN ('served', 'cancelled')
                    ) AS active_count
                FROM branches b
                LEFT JOIN orders o
                  ON o.branch_id = b.id
                 AND o.created_at >= $1
                 AND o.created_at < $2
                GROUP BY b.id, b.name
                ORDER BY b.id
                """,
                start,
                end,
            )
    finally:
        await close_db_pool(db_pool)

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="milliseconds").replace(
            "+00:00",
            "Z",
        ),
        "report_date": target_date.isoformat(),
        "branches": [
            {
                "branch_id": row["branch_id"],
                "branch_name": row["branch_name"],
                "order_count": row["order_count"],
                "gross_total": _format_money(row["gross_total"]),
                "served_count": row["served_count"],
                "cancelled_count": row["cancelled_count"],
                "active_count": row["active_count"],
            }
            for row in rows
        ],
    }


def _store_report(settings: Settings, report: dict[str, Any]) -> str:
    storage = StorageService(settings)
    report_date = report["report_date"]
    key = f"reports/daily/{report_date}.json"
    storage.client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=json.dumps(report, separators=(",", ":"), default=str).encode("utf-8"),
        ContentType="application/json",
    )
    return key


def _parse_report_date(value: str | None) -> date:
    if value:
        return date.fromisoformat(value)
    return datetime.now(UTC).date() - timedelta(days=1)


def _storage_is_configured(settings: Settings) -> bool:
    return all(
        (
            settings.S3_ENDPOINT_URL,
            settings.S3_BUCKET_NAME,
            settings.S3_ACCESS_KEY,
            settings.S3_SECRET_KEY,
            settings.MEDIA_BASE_URL,
        )
    ) and not any(
        placeholder in settings.S3_ENDPOINT_URL
        or placeholder in settings.S3_ACCESS_KEY
        or placeholder in settings.S3_SECRET_KEY
        for placeholder in ("example.com", "your_", "change_me")
    )


def _format_money(value: Decimal) -> str:
    return f"{value:.2f}"
