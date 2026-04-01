"""Full video generation pipeline Celery tasks."""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as SyncSession

from app.core.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_sync_session() -> SyncSession:
    engine = create_engine(settings.DATABASE_URL_SYNC)
    return SyncSession(engine)


@celery_app.task(name="app.tasks.pipeline.generate_images", bind=True, max_retries=2)
def generate_images_task(self, episode_id: str) -> dict:
    """Generate images for all scenes in an episode."""
    from app.models.episode import Episode
    from app.models.scene import Scene
    from app.models.style_preset import StylePreset
    from app.models.video_asset import VideoAsset
    from app.services.image.generator import generate_image

    session = _get_sync_session()
    try:
        episode = session.execute(select(Episode).where(Episode.id == episode_id)).scalar_one()

        scenes = list(
            session.execute(
                select(Scene).where(Scene.episode_id == episode_id).order_by(Scene.scene_order)
            )
            .scalars()
            .all()
        )

        # Get visual style config
        style_config = {}
        if episode.visual_style_id:
            preset = session.execute(
                select(StylePreset).where(StylePreset.id == episode.visual_style_id)
            ).scalar_one_or_none()
            if preset:
                style_config = preset.config

        for i, scene in enumerate(scenes):
            logger.info("Generating image %d/%d for episode %s", i + 1, len(scenes), episode_id)
            try:
                image_bytes = generate_image(
                    prompt=scene.visual_description,
                    style_suffix=style_config.get("style_prompt_suffix", ""),
                    negative_prompt=style_config.get("negative_prompt", ""),
                    cfg_scale=style_config.get("cfg_scale", 7),
                )

                # Store image bytes directly in database
                asset = VideoAsset(
                    scene_id=scene.id,
                    asset_type="image",
                    file_data=image_bytes,
                    file_size_bytes=len(image_bytes),
                    mime_type="image/png",
                    metadata_={"provider": "stability-ai"},
                )
                session.add(asset)

                # Set image prompt on scene
                scene.image_prompt = (
                    f"{scene.visual_description}, {style_config.get('style_prompt_suffix', '')}"
                )

            except Exception as e:
                logger.error("Failed to generate image for scene %s: %s", scene.id, e)
                raise

        session.commit()
        return {"episode_id": episode_id, "images_generated": len(scenes)}

    finally:
        session.close()


@celery_app.task(name="app.tasks.pipeline.generate_voiceovers", bind=True, max_retries=2)
def generate_voiceovers_task(self, episode_id: str) -> dict:
    """Generate voiceovers for all scenes in an episode.

    Non-fatal: if TTS fails (bad API key, quota exceeded, etc.),
    the pipeline continues without voiceovers. Images are more
    important for the preview experience.
    """
    from app.models.episode import Episode
    from app.models.scene import Scene
    from app.models.style_preset import StylePreset
    from app.models.video_asset import VideoAsset
    from app.services.tts.generator import generate_voiceover

    session = _get_sync_session()
    try:
        episode = session.execute(select(Episode).where(Episode.id == episode_id)).scalar_one()

        scenes = list(
            session.execute(
                select(Scene).where(Scene.episode_id == episode_id).order_by(Scene.scene_order)
            )
            .scalars()
            .all()
        )

        # Get voice config
        voice_config = {}
        if episode.voice_style_id:
            preset = session.execute(
                select(StylePreset).where(StylePreset.id == episode.voice_style_id)
            ).scalar_one_or_none()
            if preset:
                voice_config = preset.config

        generated = 0
        skipped = 0
        for i, scene in enumerate(scenes):
            text = scene.narration_text or scene.dialogue_text
            if not text:
                continue

            logger.info(
                "Generating voiceover %d/%d for episode %s",
                i + 1,
                len(scenes),
                episode_id,
            )
            try:
                audio_bytes = generate_voiceover(
                    text=text,
                    voice_id=voice_config.get("voice_id", "EXAVITQu4vr4xnSDxMaL"),
                    stability=voice_config.get("stability", 0.5),
                    similarity_boost=voice_config.get("similarity_boost", 0.75),
                    style=voice_config.get("style", 0.3),
                )

                # Store audio bytes directly in database
                asset = VideoAsset(
                    scene_id=scene.id,
                    asset_type="voiceover",
                    file_data=audio_bytes,
                    file_size_bytes=len(audio_bytes),
                    mime_type="audio/mpeg",
                    metadata_={"provider": "elevenlabs"},
                )
                session.add(asset)
                generated += 1

            except Exception as e:
                logger.error("Failed to generate voiceover for scene %s: %s", scene.id, e)
                skipped += 1

        session.commit()

        if skipped > 0:
            logger.warning(
                "Episode %s: %d voiceovers generated, %d skipped due to errors",
                episode_id, generated, skipped,
            )

        return {"episode_id": episode_id, "voiceovers_generated": generated, "voiceovers_skipped": skipped}

    finally:
        session.close()


@celery_app.task(name="app.tasks.pipeline.compose_and_render", bind=True)
def compose_and_render_task(self, episode_id: str) -> dict:
    """Build composition JSON and render final video via Remotion."""
    from app.models.episode import Episode
    from app.services.video.composer import build_composition_json
    from app.services.video.renderer import render_video

    session = _get_sync_session()
    try:
        composition = build_composition_json(session, episode_id)

        episode = session.execute(select(Episode).where(Episode.id == episode_id)).scalar_one()
        episode.composition_json = composition

        output_dir = os.path.join(tempfile.gettempdir(), "scooby", str(episode_id))
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "final.mp4")

        render_video(composition, output_path)

        episode.final_video_url = output_path
        episode.status = "preview_ready"
        fps = composition.get("fps", 30)
        total_frames = composition.get("totalDurationFrames", 0)
        episode.final_video_duration_sec = round(total_frames / fps, 2) if fps else 0

        session.commit()
        return {"episode_id": episode_id, "video_path": output_path}

    finally:
        session.close()


@celery_app.task(name="app.tasks.pipeline.run_full_pipeline", bind=True)
def run_full_pipeline_task(self, episode_id: str) -> dict:
    """Orchestrate the full video generation pipeline."""
    from app.models.episode import Episode
    from app.models.generation_job import GenerationJob

    session = _get_sync_session()
    try:
        episode = session.execute(select(Episode).where(Episode.id == episode_id)).scalar_one()
        episode.status = "generating"

        job = GenerationJob(
            episode_id=episode_id,
            job_type="full_pipeline",
            status="running",
            celery_task_id=self.request.id,
            started_at=datetime.now(timezone.utc),
            stage="Starting pipeline",
        )
        session.add(job)
        session.commit()

        # Step 1: Generate images
        job.stage = "Generating images"
        job.progress = 10
        session.commit()
        generate_images_task(episode_id)

        # Step 2: Generate voiceovers (non-fatal — continues if TTS fails)
        job.stage = "Generating voiceovers"
        job.progress = 50
        session.commit()
        try:
            vo_result = generate_voiceovers_task(episode_id)
            vo_skipped = vo_result.get("voiceovers_skipped", 0)
        except Exception as e:
            logger.warning("Voiceover generation failed for episode %s, continuing: %s", episode_id, e)
            vo_skipped = -1  # all failed

        # Step 3: Compose and render (skip if Remotion not available)
        job.stage = "Rendering video"
        job.progress = 80
        session.commit()
        try:
            compose_and_render_task(episode_id)
        except Exception as e:
            logger.warning("Video render skipped for episode %s (Remotion not ready): %s", episode_id, e)

        # Done — mark completed even without video render
        # The slideshow preview works with just images + optional audio
        job.status = "completed"
        job.progress = 100
        job.stage = "Video ready"
        job.completed_at = datetime.now(timezone.utc)

        warnings = []
        if vo_skipped != 0:
            warnings.append("Some or all voiceovers could not be generated (check ElevenLabs API key)")
        if job.metadata_ is None:
            job.metadata_ = {}
        if warnings:
            job.metadata_["warnings"] = warnings

        session.commit()

        return {"episode_id": episode_id, "status": "completed"}

    except Exception as e:
        logger.exception("Pipeline failed for episode %s", episode_id)
        session.rollback()
        job_result = session.execute(
            select(GenerationJob).where(
                GenerationJob.episode_id == episode_id,
                GenerationJob.job_type == "full_pipeline",
                GenerationJob.status == "running",
            )
        ).scalar_one_or_none()
        if job_result:
            job_result.status = "failed"
            job_result.error_message = str(e)
            job_result.completed_at = datetime.now(timezone.utc)

        ep = session.execute(select(Episode).where(Episode.id == episode_id)).scalar_one_or_none()
        if ep:
            ep.status = "draft"

        session.commit()
        raise

    finally:
        session.close()
