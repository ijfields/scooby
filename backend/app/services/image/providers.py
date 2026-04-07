"""Pluggable image generation provider registry.

Add new providers by:
1. Creating a new module (e.g., new_model.py) with a generate function
2. Adding a Provider class below
3. Registering it in IMAGE_PROVIDERS

Switch the active provider via IMAGE_PROVIDER env var — no code changes needed.
"""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class ImageProvider(Protocol):
    """Interface that all image generation providers must implement."""

    name: str

    def generate(
        self,
        prompt: str,
        style_suffix: str = "",
        negative_prompt: str = "",
        cfg_scale: int = 7,
        width: int = 768,
        height: int = 1344,
    ) -> bytes:
        """Generate an image from a text prompt. Returns raw PNG bytes."""
        ...


class StabilityProvider:
    """Stability AI SDXL image generation."""

    name = "stability"

    def generate(
        self,
        prompt: str,
        style_suffix: str = "",
        negative_prompt: str = "",
        cfg_scale: int = 7,
        width: int = 768,
        height: int = 1344,
    ) -> bytes:
        from app.services.image.generator import generate_image

        return generate_image(
            prompt=prompt,
            style_suffix=style_suffix,
            negative_prompt=negative_prompt,
            cfg_scale=cfg_scale,
            width=width,
            height=height,
        )


class NanoBanana2Provider:
    """Nanobanana 2 (Gemini 3.1 Flash) image generation via Google API."""

    name = "nanobanana2"

    def generate(
        self,
        prompt: str,
        style_suffix: str = "",
        negative_prompt: str = "",
        cfg_scale: int = 7,
        width: int = 768,
        height: int = 1344,
    ) -> bytes:
        from app.services.image.nanobanana2 import generate_image_nb2

        return generate_image_nb2(
            prompt=prompt,
            style_suffix=style_suffix,
            negative_prompt=negative_prompt,
            cfg_scale=cfg_scale,
            width=width,
            height=height,
        )


# ── Registry ─────────────────────────────────────────────────────────
# To add a new provider: create the class above, add it here.
IMAGE_PROVIDERS: dict[str, ImageProvider] = {
    "stability": StabilityProvider(),
    "nanobanana2": NanoBanana2Provider(),
}


def get_image_provider(name: str | None = None) -> ImageProvider:
    """Get image provider by name, or fall back to configured default."""
    from app.core.config import settings

    provider_name = name or settings.IMAGE_PROVIDER

    if provider_name not in IMAGE_PROVIDERS:
        raise ValueError(
            f"Unknown image provider '{provider_name}'. "
            f"Available: {', '.join(IMAGE_PROVIDERS.keys())}"
        )

    provider = IMAGE_PROVIDERS[provider_name]
    logger.debug("Using image provider: %s", provider.name)
    return provider
