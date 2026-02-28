from celery import Celery
from celery.schedules import crontab

from vibehouse.config import settings

app = Celery(
    "vibehouse",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "vibehouse.tasks.vibe_tasks.*": {"queue": "vibe"},
        "vibehouse.tasks.vendor_tasks.*": {"queue": "vendors"},
        "vibehouse.tasks.trello_tasks.*": {"queue": "trello"},
        "vibehouse.tasks.report_tasks.*": {"queue": "reports"},
        "vibehouse.tasks.dispute_tasks.*": {"queue": "disputes"},
    },
    beat_schedule={
        "generate-daily-reports": {
            "task": "vibehouse.tasks.report_tasks.generate_all_daily_reports",
            "schedule": crontab(hour=6, minute=30),
        },
        "check-dispute-escalations": {
            "task": "vibehouse.tasks.dispute_tasks.check_all_escalations",
            "schedule": crontab(minute=0),  # every hour
        },
        "sync-trello-boards": {
            "task": "vibehouse.tasks.trello_tasks.sync_all_boards",
            "schedule": crontab(minute="*/15"),  # every 15 minutes
        },
    },
)

app.autodiscover_tasks(
    [
        "vibehouse.tasks.vibe_tasks",
        "vibehouse.tasks.vendor_tasks",
        "vibehouse.tasks.trello_tasks",
        "vibehouse.tasks.report_tasks",
        "vibehouse.tasks.dispute_tasks",
    ]
)
