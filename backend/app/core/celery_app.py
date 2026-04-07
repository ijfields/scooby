from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "scooby",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.ai", "app.tasks.pipeline", "app.tasks.youtube"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.ai.*": {"queue": "ai_pipeline"},
        "app.tasks.pipeline.generate_images": {"queue": "image_gen"},
        "app.tasks.pipeline.generate_voiceovers": {"queue": "tts_gen"},
        "app.tasks.pipeline.compose_and_render": {"queue": "video_render"},
        "app.tasks.pipeline.run_full_pipeline": {"queue": "ai_pipeline"},
        "app.tasks.youtube.*": {"queue": "ai_pipeline"},
        "app.tasks.cleanup.*": {"queue": "cleanup"},
    },
)
