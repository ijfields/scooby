"""Kling 3.0 image-to-video animation via WaveSpeed API.

Submits an image + animation prompt to WaveSpeed's Kling endpoint,
polls for completion, and returns the generated video as MP4 bytes.

WaveSpeed API docs: https://wavespeed.ai/docs/docs-api/kwaivgi/kwaivgi-kling-v3.0-std-image-to-video
"""

from __future__ import annotations

import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

WAVESPEED_BASE = "https://api.wavespeed.ai/api/v3"

# Model IDs on WaveSpeed
KLING_MODELS = {
    "kling_std": "kling-v3.0-std",
    "kling_pro": "kling-v3.0-pro",
}


def animate_image(
    image_url: str,
    prompt: str = "",
    duration: int = 5,
    model_key: str = "kling_std",
    cfg_scale: float = 0.5,
    max_wait_seconds: int = 600,
    poll_interval: int = 10,
) -> bytes:
    """Animate a scene image into a video clip via Kling 3.0.

    Args:
        image_url: Publicly accessible URL of the source image.
                   Must be .jpg/.jpeg/.png, max 10MB, min 300px,
                   aspect ratio between 1:2.5 and 2.5:1.
        prompt: Animation direction (e.g., "slow zoom in, steam rising").
        duration: Clip duration in seconds (3-15, default 5).
        model_key: Provider key — "kling_std" or "kling_pro".
        cfg_scale: Prompt adherence 0.0-1.0 (higher = stricter).
        max_wait_seconds: Maximum polling time before timeout.
        poll_interval: Seconds between status checks.

    Returns:
        Raw MP4 video bytes.

    Raises:
        RuntimeError: If generation fails.
        TimeoutError: If generation doesn't complete in time.
        ValueError: If model_key is unknown.
    """
    model = KLING_MODELS.get(model_key)
    if not model:
        raise ValueError(
            f"Unknown animation model '{model_key}'. "
            f"Available: {', '.join(KLING_MODELS.keys())}"
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.WAVESPEED_API_KEY}",
    }

    # Step 1: Submit the animation task
    logger.info(
        "Submitting Kling animation: model=%s, duration=%ds, prompt=%s",
        model, duration, prompt[:80],
    )

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{WAVESPEED_BASE}/kwaivgi/{model}/image-to-video",
            headers=headers,
            json={
                "image": image_url,
                "prompt": prompt,
                "duration": duration,
                "cfg_scale": cfg_scale,
                "shot_type": "customize",
            },
        )
        resp.raise_for_status()
        request_id = resp.json()["data"]["id"]

    logger.info("Kling task submitted: %s", request_id)

    # Step 2: Poll for completion
    elapsed = 0
    while elapsed < max_wait_seconds:
        time.sleep(poll_interval)
        elapsed += poll_interval

        with httpx.Client(timeout=30) as client:
            result = client.get(
                f"{WAVESPEED_BASE}/predictions/{request_id}/result",
                headers=headers,
            )
            data = result.json().get("data", {})
            status = data.get("status", "unknown")

        if elapsed % 30 == 0:
            logger.info("Kling task %s: %s (%ds)", request_id, status, elapsed)

        if status == "completed":
            video_url = data["outputs"][0]
            logger.info("Kling animation complete, downloading from %s", video_url[:80])

            with httpx.Client(timeout=120) as client:
                video_resp = client.get(video_url)
                video_resp.raise_for_status()
                video_bytes = video_resp.content

            logger.info("Kling video downloaded: %d bytes", len(video_bytes))
            return video_bytes

        elif status == "failed":
            error_msg = data.get("error", str(data))
            raise RuntimeError(f"Kling animation failed for task {request_id}: {error_msg}")

    raise TimeoutError(
        f"Kling animation timed out after {max_wait_seconds}s for task {request_id}"
    )
