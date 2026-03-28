from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "scooby",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.ai", "app.tasks.pipeline"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.ai.*": {"queue": "ai_pipeline"},
        "app.tasks.image.*": {"queue": "image_gen"},
        "app.tasks.tts.*": {"queue": "tts_gen"},
        "app.tasks.video.*": {"queue": "video_render"},
        "app.tasks.cleanup.*": {"queue": "cleanup"},
    },
)
