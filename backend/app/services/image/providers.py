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
        reference_images: list[bytes] | None = None,
    ) -> bytes:
        """Generate an image from a text prompt. Returns raw PNG bytes.

        ``reference_images`` are optional canonical frames used to keep a
        character / art style consistent across scenes (anchor-frame
        locking). Providers that cannot condition on an input image accept
        the argument and ignore it.
        """
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
        reference_images: list[bytes] | None = None,
    ) -> bytes:
        from app.services.image.generator import generate_image

        # Stability's text-to-image endpoint cannot condition on a reference
        # image — reference_images is accepted for interface parity and ignored.
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
        reference_images: list[bytes] | None = None,
    ) -> bytes:
        from app.services.image.nanobanana2 import generate_image_nb2

        return generate_image_nb2(
            prompt=prompt,
            style_suffix=style_suffix,
            negative_prompt=negative_prompt,
            cfg_scale=cfg_scale,
            width=width,
            height=height,
            reference_images=reference_images,
        )


class _TopViewProviderBase:
    """Common base for the TopView-routed image providers. Each subclass
    fixes a specific TopView model display name and (optionally) whether
    that model takes a `resolution` parameter."""

    name = "topview"
    model_display_name = ""
    pass_resolution = True

    def generate(
        self,
        prompt: str,
        style_suffix: str = "",
        negative_prompt: str = "",
        cfg_scale: int = 7,
        width: int = 768,
        height: int = 1344,
        reference_images: list[bytes] | None = None,
    ) -> bytes:
        from app.services.image.topview import generate_image_topview

        # TopView's text2image submit path doesn't accept a reference image —
        # reference_images is ignored until the image-edit endpoint is wired.
        return generate_image_topview(
            model_display_name=self.model_display_name,
            prompt=prompt,
            style_suffix=style_suffix,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            pass_resolution=self.pass_resolution,
        )


class TopViewNanoBanana2Provider(_TopViewProviderBase):
    """Nano Banana 2 via TopView. Same Google model as `nanobanana2` but
    routed through TopView's billing — sidesteps Google AI Studio
    prepayment exhaustion. Cheapest at 1K (0.40 credits/image)."""
    name = "topview_nano_banana_2"
    model_display_name = "Nano Banana 2"
    pass_resolution = True


class TopViewNanoBananaProProvider(_TopViewProviderBase):
    """Nano Banana Pro (Gemini 3.0 Pro) via TopView. Higher quality than
    Nano Banana 2, ~2× the cost (0.80 credits/image at 1K). Use for
    premium tiers or when image quality is the bottleneck."""
    name = "topview_nano_banana_pro"
    model_display_name = "Nano Banana Pro"
    pass_resolution = True


class TopViewImagen4Provider(_TopViewProviderBase):
    """Google Imagen 4 via TopView. Flat 0.50 credits/image, no
    resolution parameter (the model picks). Decent fallback if both
    Nano Banana variants are unavailable."""
    name = "topview_imagen_4"
    model_display_name = "Imagen 4"
    pass_resolution = False


# ── Registry ─────────────────────────────────────────────────────────
# To add a new provider: create the class above, add it here.
IMAGE_PROVIDERS: dict[str, ImageProvider] = {
    "stability": StabilityProvider(),
    "nanobanana2": NanoBanana2Provider(),
    "topview_nano_banana_2": TopViewNanoBanana2Provider(),
    "topview_nano_banana_pro": TopViewNanoBananaProProvider(),
    "topview_imagen_4": TopViewImagen4Provider(),
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
