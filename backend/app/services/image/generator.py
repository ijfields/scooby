"""Stability AI image generation service."""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

STABILITY_API_URL = (
    "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
)


def generate_image(
    prompt: str,
    style_suffix: str = "",
    negative_prompt: str = "",
    cfg_scale: int = 7,
    width: int = 768,
    height: int = 1344,
) -> bytes:
    """Generate a single image via Stability AI SDXL API.

    Returns raw PNG bytes.
    """
    full_prompt = f"{prompt}, {style_suffix}" if style_suffix else prompt

    payload = {
        "text_prompts": [
            {"text": full_prompt, "weight": 1.0},
        ],
        "cfg_scale": cfg_scale,
        "width": width,
        "height": height,
        "samples": 1,
        "steps": 30,
    }

    if negative_prompt:
        payload["text_prompts"].append({"text": negative_prompt, "weight": -1.0})

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            STABILITY_API_URL,
            headers={
                "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "image/png",
            },
            json=payload,
        )
        resp.raise_for_status()
        return resp.content
