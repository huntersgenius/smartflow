import asyncio
import logging
import logging.config
import sys
from pathlib import Path

import asyncpg


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings  # noqa: E402


logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "format": (
                        '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
                        '"logger":"%(name)s","message":"%(message)s"}'
                    )
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "json",
                }
            },
            "root": {
                "handlers": ["default"],
                "level": "INFO",
            },
        }
    )


async def apply_migrations() -> None:
    settings = get_settings()
    migration_dir = Path(__file__).resolve().parent
    sql_files = sorted(migration_dir.glob("*.sql"))

    pool = await asyncpg.create_pool(
        dsn=settings.DATABASE_URL,
        min_size=5,
        max_size=20,
    )
    try:
        async with pool.acquire() as connection:
            for sql_file in sql_files:
                logger.info("applying_migration", extra={"migration": sql_file.name})
                await connection.execute(sql_file.read_text(encoding="utf-8"))
                logger.info("migration_applied", extra={"migration": sql_file.name})
    finally:
        await pool.close()


def main() -> None:
    configure_logging()
    asyncio.run(apply_migrations())


if __name__ == "__main__":
    main()
