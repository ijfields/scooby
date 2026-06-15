"""Nanobanana 2 (Gemini 3.1 Flash) image generation service."""

from __future__ import annotations

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
    reference_images: list[bytes] | None = None,
) -> bytes:
    """Generate a single image via Nanobanana 2 (Gemini 3.1 Flash).

    Returns raw PNG bytes.

    Note: Nanobanana 2 does not support explicit negative_prompt or cfg_scale
    parameters — these are accepted for interface compatibility with the
    Stability provider but are handled via prompt engineering instead.

    ``reference_images`` (anchor-frame locking) are passed to Gemini as input
    image parts so the model keeps the recurring character, art style, and
    world consistent with earlier scenes. Gemini's multimodal input natively
    supports this, so reference conditioning is functional for this provider.
    """
    full_prompt = f"{prompt}, {style_suffix}" if style_suffix else prompt

    # Append negative guidance as prompt text if provided
    if negative_prompt:
        full_prompt += f". Avoid: {negative_prompt}"

    # When reference frames are supplied, instruct the model to treat them as
    # the canonical look and prepend them as image parts in the request.
    contents: list = []
    if reference_images:
        for ref in reference_images:
            contents.append(types.Part.from_bytes(data=ref, mime_type="image/png"))
        full_prompt = (
            "Use the reference image(s) as the canonical appearance for the "
            "recurring character(s), art style, color palette, and world. "
            "Keep that character and style strictly consistent while rendering "
            f"this scene: {full_prompt}"
        )
    contents.append(full_prompt)

    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    logger.info(
        "Generating image via Nanobanana 2 (%d reference frame(s)): %s",
        len(reference_images or []), full_prompt[:100],
    )

    response = client.models.generate_content(
        model="gemini-3.1-flash-image-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        ),
    )

    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            png_bytes = image.image_bytes
            logger.info("Nanobanana 2 image generated: %d bytes", len(png_bytes))
            return png_bytes

    raise RuntimeError("Nanobanana 2 returned no image data")
