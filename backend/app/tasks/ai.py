from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_sync_session() -> Session:
    """Create a sync SQLAlchemy session for use in Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession

    engine = create_engine(settings.DATABASE_URL_SYNC)
    return SyncSession(engine)


@celery_app.task(name="app.tasks.ai.generate_scene_breakdown", bind=True, max_retries=2)
def generate_scene_breakdown_task(self, episode_id: str, story_text: str) -> dict:
    """Celery task: call Claude to break story into scenes, save to DB."""
    from app.models.episode import Episode
    from app.models.generation_job import GenerationJob
    from app.models.scene import Scene
    from app.services.ai.story_breakdown import (
        StoryBreakdownError,
        generate_scene_breakdown,
    )

    session = _get_sync_session()
    try:
        # Update job status
        job = session.execute(
            select(GenerationJob).where(
                GenerationJob.episode_id == episode_id,
                GenerationJob.job_type == "scene_breakdown",
                GenerationJob.status == "pending",
            )
        ).scalar_one_or_none()

        if job:
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            job.celery_task_id = self.request.id
            session.commit()

        # Call Claude
        breakdown = generate_scene_breakdown(story_text)

        # Save scenes
        episode = session.execute(select(Episode).where(Episode.id == episode_id)).scalar_one()

        episode.title = breakdown.title
        episode.target_duration_sec = int(breakdown.total_duration_sec)
        episode.status = "scenes_generated"

        for beat in breakdown.beats:
            scene = Scene(
                episode_id=episode_id,
                scene_order=beat.beat_number,
                beat_label=beat.beat_label,
                visual_description=beat.visual_description,
                narration_text=beat.narration_text,
                duration_sec=beat.duration_sec,
            )
            session.add(scene)

        if job:
            job.status = "completed"
            job.progress = 100
            job.stage = "Scene breakdown complete"
            job.completed_at = datetime.now(timezone.utc)

        session.commit()

        return {
            "episode_id": episode_id,
            "title": breakdown.title,
            "num_scenes": len(breakdown.beats),
            "total_duration": breakdown.total_duration_sec,
        }

    except StoryBreakdownError as e:
        logger.error("Scene breakdown failed: %s", e)
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
        raise self.retry(exc=e, countdown=5)

    except Exception as e:
        logger.exception("Unexpected error in scene breakdown")
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
        raise

    finally:
        session.close()
