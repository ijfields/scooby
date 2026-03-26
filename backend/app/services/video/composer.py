"""Build Remotion composition JSON from episode data."""

from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.episode import Episode
from app.models.scene import Scene
from app.models.style_preset import StylePreset
from app.models.video_asset import VideoAsset


def build_composition_json(session: Session, episode_id: str) -> dict:
    """Build the composition JSON spec for Remotion rendering."""
    episode = session.execute(
        select(Episode).where(Episode.id == episode_id)
    ).scalar_one()

    scenes = list(
        session.execute(
            select(Scene)
            .where(Scene.episode_id == episode_id)
            .order_by(Scene.scene_order)
        )
        .scalars()
        .all()
    )

    fps = 30
    current_frame = 0
    scene_specs = []

    for scene in scenes:
        duration_sec = float(scene.duration_sec or 10)
        duration_frames = int(duration_sec * fps)

        # Get assets for this scene
        image_asset = session.execute(
            select(VideoAsset).where(
                VideoAsset.scene_id == scene.id,
                VideoAsset.asset_type == "image",
                VideoAsset.is_active.is_(True),
            )
        ).scalar_one_or_none()

        vo_asset = session.execute(
            select(VideoAsset).where(
                VideoAsset.scene_id == scene.id,
                VideoAsset.asset_type == "voiceover",
                VideoAsset.is_active.is_(True),
            )
        ).scalar_one_or_none()

        scene_spec: dict = {
            "sceneId": str(scene.id),
            "beatLabel": scene.beat_label,
            "startFrame": current_frame,
            "durationFrames": duration_frames,
            "image": {
                "url": image_asset.file_url if image_asset else "",
                "animation": {
                    "type": "ken_burns",
                    "startScale": 1.0,
                    "endScale": round(random.uniform(1.08, 1.18), 2),
                    "startX": 0,
                    "startY": 0,
                    "endX": random.randint(-25, 25),
                    "endY": random.randint(-15, 15),
                },
            },
            "captions": [],
            "transition": {"type": "crossfade", "durationFrames": 15},
        }

        if vo_asset:
            scene_spec["voiceover"] = {
                "url": vo_asset.file_url,
                "startOffsetFrames": 15,
                "volume": 1.0,
            }

        if scene.narration_text:
            scene_spec["captions"].append(
                {
                    "text": scene.narration_text,
                    "startFrame": 15,
                    "endFrame": duration_frames - 5,
                    "style": "dramatic_center",
                }
            )

        scene_specs.append(scene_spec)
        current_frame += duration_frames

    # Music bed
    music_bed = None
    if episode.music_style_id:
        music_preset = session.execute(
            select(StylePreset).where(StylePreset.id == episode.music_style_id)
        ).scalar_one_or_none()
        if music_preset and music_preset.config.get("track_url"):
            music_bed = {
                "url": music_preset.config["track_url"],
                "volume": music_preset.config.get("volume", 0.15),
                "fadeInFrames": int(music_preset.config.get("fade_in_seconds", 2) * fps),
                "fadeOutFrames": int(
                    music_preset.config.get("fade_out_seconds", 3) * fps
                ),
            }

    composition = {
        "episodeId": str(episode.id),
        "title": episode.title or "Untitled",
        "fps": fps,
        "width": 1080,
        "height": 1920,
        "totalDurationFrames": current_frame,
        "scenes": scene_specs,
    }
    if music_bed:
        composition["musicBed"] = music_bed

    return composition
