from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "grd_document_verf",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.autodiscover_tasks(["app.workers"])
celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "expire-quarantined-documents": {
            "task": "expire_quarantined_documents",
            "schedule": settings.document_expiry_sweep_seconds,
        }
    },
)
