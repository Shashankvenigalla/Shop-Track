"""
Celery configuration for background task processing.
"""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery = Celery(
    "shoptrack",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"]
)

# Celery configuration
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
    beat_schedule={
        "update-rush-predictions": {
            "task": "app.worker.tasks.update_rush_predictions",
            "schedule": 3600.0,  # Every hour
        },
        "cleanup-expired-alerts": {
            "task": "app.worker.tasks.cleanup_expired_alerts",
            "schedule": 1800.0,  # Every 30 minutes
        },
        "retrain-ml-model": {
            "task": "app.worker.tasks.retrain_ml_model",
            "schedule": 86400.0,  # Every 24 hours
        },
        "generate-daily-report": {
            "task": "app.worker.tasks.generate_daily_report",
            "schedule": 86400.0,  # Every 24 hours
        }
    }
)

if __name__ == "__main__":
    celery.start() 