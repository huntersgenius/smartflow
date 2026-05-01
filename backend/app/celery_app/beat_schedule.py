from celery.schedules import crontab


CELERYBEAT_SCHEDULE = {
    "cleanup-expired-sessions": {
        "task": "app.celery_app.tasks.cleanup.cleanup_expired_sessions",
        "schedule": crontab(minute="*/15"),
    },
    "generate-daily-reports": {
        "task": "app.celery_app.tasks.reports.generate_daily_reports",
        "schedule": crontab(hour=1, minute=0),
    },
}
