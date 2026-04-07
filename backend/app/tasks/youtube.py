"""Celery tasks for the YouTube-to-Series pipeline."""

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


@celery_app.task(
    name="app.tasks.youtube.fetch_and_plan",
    bind=True,
    max_retries=1,
)
def fetch_and_plan_task(
    self,
    story_id: str,
    youtube_url: str,
    relationship: str,
) -> dict:
    """Fetch YouTube transcript, clean it, plan a series via Claude.

    Steps:
    1. Fetch transcript + metadata from YouTube
    2. Clean transcript
    3. Store transcript as Story.raw_text, metadata as Story.source_meta
    4. Call AI Series Planner to generate episode outlines
    5. Store plan in Story.source_meta["series_plan"]
    6. Set Story.status = "plan_ready"
    """
    from app.models.story import Story
    from app.services.ai.series_planner import SeriesPlanError, generate_series_plan
    from app.services.youtube.transcript import fetch_full_transcript

    session = _get_sync_session()
    try:
        story = session.execute(select(Story).where(Story.id == story_id)).scalar_one()
        story.status = "importing"
        session.commit()

        # Step 1-2: Fetch and clean transcript
        logger.info("Fetching transcript for %s", youtube_url)
        result = fetch_full_transcript(youtube_url)

        # Step 3: Store transcript and metadata
        story.raw_text = result.clean_transcript
        story.word_count = result.word_count
        story.title = result.title
        story.source_meta = {
            "channel": result.channel,
            "video_title": result.title,
            "youtube_url": youtube_url,
            "video_id": result.video_id,
            "duration_sec": result.duration_sec,
            "relationship": relationship,
            "fair_use_acknowledged_at": datetime.now(timezone.utc).isoformat(),
        }
        session.commit()

        # Step 4: Plan series via Claude
        logger.info("Planning series for '%s' (%d words)", result.title, result.word_count)
        story.status = "planning"
        session.commit()

        plan = generate_series_plan(
            transcript=result.clean_transcript,
            video_title=result.title,
            channel=result.channel,
            duration_sec=result.duration_sec,
        )

        # Step 5: Store plan in source_meta
        meta = dict(story.source_meta)
        meta["series_plan"] = plan.model_dump()
        story.source_meta = meta
        story.status = "plan_ready"
        session.commit()

        logger.info(
            "Series plan ready: '%s' — %d episodes",
            plan.series_title,
            plan.total_episodes,
        )
        return {
            "story_id": story_id,
            "series_title": plan.series_title,
            "total_episodes": plan.total_episodes,
        }

    except SeriesPlanError as e:
        logger.error("Series planning failed: %s", e)
        story.status = "plan_failed"
        story.source_meta = {**(story.source_meta or {}), "error": str(e)}
        session.commit()
        raise self.retry(exc=e, countdown=10)

    except Exception as e:
        logger.exception("Unexpected error in fetch_and_plan")
        story.status = "import_failed"
        story.source_meta = {**(story.source_meta or {}), "error": str(e)}
        session.commit()
        raise

    finally:
        session.close()


@celery_app.task(
    name="app.tasks.youtube.approve_series",
    bind=True,
)
def approve_series_task(
    self,
    story_id: str,
    approved_episodes: list[dict] | None = None,
) -> dict:
    """Create Episode rows from the approved series plan and dispatch breakdowns.

    Args:
        story_id: The Story containing the series plan.
        approved_episodes: Optional list of edits (title/angle overrides, removals).
            If None, uses the plan as-is.
    """
    from app.models.episode import Episode
    from app.models.generation_job import GenerationJob
    from app.models.story import Story
    from app.tasks.ai import generate_scene_breakdown_task

    session = _get_sync_session()
    try:
        story = session.execute(select(Story).where(Story.id == story_id)).scalar_one()

        if story.status != "plan_ready":
            raise ValueError(f"Story status is '{story.status}', expected 'plan_ready'")

        plan_data = story.source_meta.get("series_plan")
        if not plan_data:
            raise ValueError("No series plan found in source_meta")

        episodes_plan = plan_data["episodes"]

        # Apply edits if provided
        if approved_episodes:
            edits_by_num = {e["episode_number"]: e for e in approved_episodes}
            filtered = []
            for ep in episodes_plan:
                edit = edits_by_num.get(ep["episode_number"])
                if edit and edit.get("remove"):
                    continue
                if edit:
                    if edit.get("title"):
                        ep["title"] = edit["title"]
                    if edit.get("angle"):
                        ep["angle"] = edit["angle"]
                filtered.append(ep)
            episodes_plan = filtered

        # Create Episode rows and dispatch breakdowns
        story.status = "processing"
        session.commit()

        created_episodes = []
        for ep_plan in episodes_plan:
            episode = Episode(
                story_id=story_id,
                title=ep_plan["title"],
                episode_number=ep_plan["episode_number"],
                series_angle=ep_plan["angle"],
                target_duration_sec=ep_plan.get("target_duration_sec", 75),
                status="draft",
            )
            session.add(episode)
            session.flush()  # Get the episode ID

            # Create a generation job for tracking
            job = GenerationJob(
                episode_id=episode.id,
                job_type="scene_breakdown",
                status="pending",
            )
            session.add(job)
            session.commit()

            # Dispatch the EXISTING scene breakdown task
            generate_scene_breakdown_task.delay(
                str(episode.id),
                ep_plan["key_content"],
            )

            created_episodes.append({
                "episode_id": str(episode.id),
                "episode_number": ep_plan["episode_number"],
                "title": ep_plan["title"],
            })

        logger.info(
            "Series approved: %d episodes created for story %s",
            len(created_episodes),
            story_id,
        )
        return {
            "story_id": story_id,
            "episodes_created": len(created_episodes),
            "episodes": created_episodes,
        }

    except Exception as e:
        logger.exception("Error approving series")
        raise

    finally:
        session.close()
