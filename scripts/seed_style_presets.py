"""Seed the style_presets table with default visual, voice, and music presets."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.base import Base
from app.models.style_preset import StylePreset

PRESETS = [
    # Visual styles
    {
        "name": "Soft Realistic",
        "category": "visual",
        "description": "Warm, soft-focus photorealistic imagery with natural lighting",
        "config": {
            "model": "stability-ai/sdxl",
            "style_prompt_suffix": "soft focus, warm natural lighting, photorealistic, cinematic depth of field",
            "negative_prompt": "cartoon, anime, harsh lighting, oversaturated",
            "cfg_scale": 7,
            "aspect_ratio": "9:16",
        },
        "sort_order": 1,
    },
    {
        "name": "Moody Graphic Novel",
        "category": "visual",
        "description": "High contrast, ink-style shadows with dramatic noir feel",
        "config": {
            "model": "stability-ai/sdxl",
            "style_prompt_suffix": "graphic novel style, high contrast, ink shadows, dramatic noir lighting",
            "negative_prompt": "photorealistic, bright colors, cheerful",
            "cfg_scale": 8,
            "aspect_ratio": "9:16",
        },
        "sort_order": 2,
    },
    {
        "name": "Watercolor",
        "category": "visual",
        "description": "Soft, painterly, pastel tones with artistic texture",
        "config": {
            "model": "stability-ai/sdxl",
            "style_prompt_suffix": "watercolor painting, soft pastel tones, painterly texture, artistic",
            "negative_prompt": "photorealistic, sharp edges, digital",
            "cfg_scale": 6,
            "aspect_ratio": "9:16",
        },
        "sort_order": 3,
    },
    {
        "name": "Cinematic Dark",
        "category": "visual",
        "description": "Deep shadows, dramatic color grading, film noir aesthetic",
        "config": {
            "model": "stability-ai/sdxl",
            "style_prompt_suffix": "cinematic, deep shadows, dramatic color grading, noir aesthetic, moody",
            "negative_prompt": "bright, cheerful, cartoon, flat lighting",
            "cfg_scale": 9,
            "aspect_ratio": "9:16",
        },
        "sort_order": 4,
    },
    # Voice presets
    {
        "name": "Warm Female",
        "category": "voice",
        "description": "Warm, empathetic female narrator voice",
        "config": {
            "provider": "elevenlabs",
            "voice_id": "EXAVITQu4vr4xnSDxMaL",
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.3,
        },
        "sort_order": 1,
    },
    {
        "name": "Calm Male",
        "category": "voice",
        "description": "Steady, composed male narrator voice",
        "config": {
            "provider": "elevenlabs",
            "voice_id": "pNInz6obpgDQGcFmaJgB",
            "stability": 0.6,
            "similarity_boost": 0.7,
            "style": 0.2,
        },
        "sort_order": 2,
    },
    {
        "name": "Neutral Storyteller",
        "category": "voice",
        "description": "Gender-neutral, clear delivery",
        "config": {
            "provider": "elevenlabs",
            "voice_id": "21m00Tcm4TlvDq8ikWAM",
            "stability": 0.55,
            "similarity_boost": 0.65,
            "style": 0.25,
        },
        "sort_order": 3,
    },
    # Music moods
    {
        "name": "Tense",
        "category": "music",
        "description": "Tension-building ambient underscore",
        "config": {
            "track_url": "/music/tense-ambient-loop.mp3",
            "volume": 0.15,
            "fade_in_seconds": 2,
            "fade_out_seconds": 3,
        },
        "sort_order": 1,
    },
    {
        "name": "Hopeful",
        "category": "music",
        "description": "Light, uplifting piano/strings",
        "config": {
            "track_url": "/music/hopeful-piano-loop.mp3",
            "volume": 0.15,
            "fade_in_seconds": 2,
            "fade_out_seconds": 3,
        },
        "sort_order": 2,
    },
    {
        "name": "Melancholy",
        "category": "music",
        "description": "Slow, minor-key emotional bed",
        "config": {
            "track_url": "/music/melancholy-strings-loop.mp3",
            "volume": 0.15,
            "fade_in_seconds": 2,
            "fade_out_seconds": 3,
        },
        "sort_order": 3,
    },
    {
        "name": "None",
        "category": "music",
        "description": "No background music",
        "config": {"track_url": None, "volume": 0},
        "sort_order": 4,
    },
]


def seed():
    engine = create_engine(settings.DATABASE_URL_SYNC)
    with Session(engine) as session:
        for preset_data in PRESETS:
            existing = session.execute(
                select(StylePreset).where(StylePreset.name == preset_data["name"])
            ).scalar_one_or_none()
            if existing:
                print(f"  Skipping '{preset_data['name']}' (already exists)")
                continue
            preset = StylePreset(**preset_data)
            session.add(preset)
            print(f"  Added '{preset_data['name']}'")
        session.commit()
        print("Done! Style presets seeded.")


if __name__ == "__main__":
    seed()
