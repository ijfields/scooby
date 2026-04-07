"""Pluggable video animation provider registry.

Add new providers by:
1. Implementing the AnimationProvider protocol
2. Registering in ANIMATION_PROVIDERS

Switch via VIDEO_ANIMATION_PROVIDER env var. Set to "none" to skip animation
(Storyboard mode — static images with Ken Burns).
"""

from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)


class AnimationProvider(Protocol):
    """Interface that all video animation providers must implement."""

    name: str

    def animate(
        self,
        image_url: str,
        prompt: str = "",
        duration: int = 5,
    ) -> bytes:
        """Animate an image into a video clip. Returns raw MP4 bytes."""
        ...


class KlingStdProvider:
    """Kling 3.0 Standard via WaveSpeed — good balance of cost and quality."""

    name = "kling_std"

    def animate(
        self,
        image_url: str,
        prompt: str = "",
        duration: int = 5,
    ) -> bytes:
        from app.services.video.animation import animate_image

        return animate_image(
            image_url=image_url,
            prompt=prompt,
            duration=duration,
            model_key="kling_std",
        )


class KlingProProvider:
    """Kling 3.0 Pro via WaveSpeed — premium quality, higher cost."""

    name = "kling_pro"

    def animate(
        self,
        image_url: str,
        prompt: str = "",
        duration: int = 5,
    ) -> bytes:
        from app.services.video.animation import animate_image

        return animate_image(
            image_url=image_url,
            prompt=prompt,
            duration=duration,
            model_key="kling_pro",
        )


# ── Registry ─────────────────────────────────────────────────────────
ANIMATION_PROVIDERS: dict[str, AnimationProvider] = {
    "kling_std": KlingStdProvider(),
    "kling_pro": KlingProProvider(),
}


def get_animation_provider(name: str | None = None) -> AnimationProvider | None:
    """Get animation provider by name, or fall back to configured default.

    Returns None if provider is "none" (Storyboard mode — no animation).
    """
    from app.core.config import settings

    provider_name = name or settings.VIDEO_ANIMATION_PROVIDER

    if provider_name == "none":
        return None

    if provider_name not in ANIMATION_PROVIDERS:
        raise ValueError(
            f"Unknown animation provider '{provider_name}'. "
            f"Available: none, {', '.join(ANIMATION_PROVIDERS.keys())}"
        )

    provider = ANIMATION_PROVIDERS[provider_name]
    logger.debug("Using animation provider: %s", provider.name)
    return provider
