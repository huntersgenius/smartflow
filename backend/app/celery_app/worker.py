import logging
import logging.config

from celery import Celery

from app.celery_app.beat_schedule import CELERYBEAT_SCHEDULE
from app.config import get_settings


settings = get_settings()


def configure_worker_logging(level: str) -> None:
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
                "level": level,
            },
        }
    )


configure_worker_logging(settings.LOG_LEVEL)

app = Celery(
    "smartflow",
    include=[
        "app.celery_app.tasks.cleanup",
        "app.celery_app.tasks.images",
        "app.celery_app.tasks.reports",
    ],
)

app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    beat_schedule=CELERYBEAT_SCHEDULE,
)
