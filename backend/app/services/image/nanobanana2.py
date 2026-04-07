"""Nanobanana 2 (Gemini 3.1 Flash) image generation service."""

from __future__ import annotations

import io
import logging

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_image_nb2(
    prompt: str,
    style_suffix: str = "",
    negative_prompt: str = "",
    cfg_scale: int = 7,
    width: int = 768,
    height: int = 1344,
) -> bytes:
    """Generate a single image via Nanobanana 2 (Gemini 3.1 Flash).

    Returns raw PNG bytes.

    Note: Nanobanana 2 does not support explicit negative_prompt or cfg_scale
    parameters — these are accepted for interface compatibility with the
    Stability provider but are handled via prompt engineering instead.
    """
    full_prompt = f"{prompt}, {style_suffix}" if style_suffix else prompt

    # Append negative guidance as prompt text if provided
    if negative_prompt:
        full_prompt += f". Avoid: {negative_prompt}"

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    logger.info("Generating image via Nanobanana 2: %s", full_prompt[:100])

    response = client.models.generate_content(
        model="gemini-3.1-flash-image-preview",
        contents=[full_prompt],
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        ),
    )

    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            png_bytes = buf.getvalue()
            logger.info("Nanobanana 2 image generated: %d bytes", len(png_bytes))
            return png_bytes

    raise RuntimeError("Nanobanana 2 returned no image data")
