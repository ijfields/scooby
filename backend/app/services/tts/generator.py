"""ElevenLabs TTS voiceover generation service."""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"


def generate_voiceover(
    text: str,
    voice_id: str = "EXAVITQu4vr4xnSDxMaL",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.3,
) -> bytes:
    """Generate voiceover audio via ElevenLabs API.

    Returns raw MP3 bytes.
    """
    url = f"{ELEVENLABS_API_URL}/{voice_id}"

    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
        },
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            url,
            headers={
                "xi-api-key": settings.ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json=payload,
        )
        resp.raise_for_status()
        return resp.content
