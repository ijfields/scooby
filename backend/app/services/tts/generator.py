"""ElevenLabs TTS voiceover generation service."""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# Free-tier voice IDs that are always available
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # George - Warm, Captivating Storyteller
FREE_VOICE_IDS = {
    "CwhRBWXzGAHq8TQ4Fs17",  # Roger
    "EXAVITQu4vr4xnSDxMaL",  # Sarah
    "FGY2WhTYpPnrIDTdsKH5",  # Laura
    "IKne3meq5aSn9XLyUdCD",  # Charlie
    "JBFqnCBsd6RMkjVDRZzb",  # George
    "N2lVS1w4EtoT3dr4eOWO",  # Callum
    "SAz9YHcvj6GT2YYXdXww",  # River
    "SOYHLrjzK2X1ezoPC6cr",  # Harry
    "TX3LPaxmHKxFdv7VOQHJ",  # Liam
    "Xb7hH8MSUJpSbSDYk0k2",  # Alice
}


def generate_voiceover(
    text: str,
    voice_id: str = DEFAULT_VOICE_ID,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.3,
) -> bytes:
    """Generate voiceover audio via ElevenLabs API.

    Returns raw MP3 bytes.
    """
    # Fall back to default if voice_id isn't in the free tier
    if voice_id not in FREE_VOICE_IDS:
        logger.warning("Voice %s not available, falling back to %s", voice_id, DEFAULT_VOICE_ID)
        voice_id = DEFAULT_VOICE_ID

    url = f"{ELEVENLABS_API_URL}/{voice_id}"

    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
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
