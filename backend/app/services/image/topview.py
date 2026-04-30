"""TopView image generation service.

TopView aggregates multiple image-gen models (Nano Banana 2/Pro, Seedream,
Imagen 4, GPT Image 2, Grok Image, Kontext-Pro) under one API. We use this
to route image-gen through TopView's billing instead of Google AI Studio
prepay (which depleted on 2026-04-30) — same Google models, different bill.

API ref: https://docs.topview.ai/reference/text-to-image-image-edit-task-api-usage

Endpoints:
- POST /v1/common_task/text2image/task/submit  → returns taskId
- GET  /v1/common_task/text2image/task/query   → poll for result + filePath

Auth: Authorization: Bearer <TOPVIEW_API_KEY>, Topview-Uid: <TOPVIEW_UID>.
"""

from __future__ import annotations

import logging
import time

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.topview.ai"
SUBMIT_PATH = "/v1/common_task/text2image/task/submit"
QUERY_PATH = "/v1/common_task/text2image/task/query"

POLL_INTERVAL_SEC = 4
POLL_TIMEOUT_SEC = 300


def _aspect_ratio(width: int, height: int) -> str:
    """Map (width, height) to a TopView aspectRatio string. Snaps to the
    nearest of the supported ratios since arbitrary dimensions aren't
    accepted. We bias toward 9:16 since Scooby is vertical drama."""
    if height <= 0 or width <= 0:
        return "9:16"
    ratio = width / height
    # Closest of the common ones (only including ratios all NB models support)
    candidates = {
        "9:16": 9 / 16,
        "3:4": 3 / 4,
        "1:1": 1.0,
        "4:3": 4 / 3,
        "16:9": 16 / 9,
    }
    best = min(candidates.items(), key=lambda kv: abs(kv[1] - ratio))
    return best[0]


def _resolution(height: int) -> str:
    """Map output height to a TopView resolution tier. 1K is roughly
    1080p, 2K is 1440p, 4K is 2160p. Higher tiers cost more."""
    if height <= 720:
        return "512p"
    if height <= 1440:
        return "1K"
    if height <= 2160:
        return "2K"
    return "4K"


def _headers() -> dict[str, str]:
    if not settings.TOPVIEW_API_KEY or not settings.TOPVIEW_UID:
        raise RuntimeError(
            "TOPVIEW_API_KEY and TOPVIEW_UID must be set to use the topview "
            "image provider"
        )
    return {
        "Authorization": f"Bearer {settings.TOPVIEW_API_KEY}",
        "Topview-Uid": settings.TOPVIEW_UID,
        "Content-Type": "application/json",
    }


def _submit(model_display_name: str, prompt: str, aspect_ratio: str,
            resolution: str | None) -> str:
    body: dict = {
        "model": model_display_name,
        "prompt": prompt,
        "aspectRatio": aspect_ratio,
        "generateCount": 1,
    }
    if resolution is not None:
        body["resolution"] = resolution

    resp = requests.post(
        f"{BASE_URL}{SUBMIT_PATH}", json=body, headers=_headers(), timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "200":
        raise RuntimeError(f"TopView submit failed: {data.get('message')} — {data}")
    return data["result"]["taskId"]


def _poll(task_id: str) -> dict:
    elapsed = 0
    headers = _headers()
    while elapsed < POLL_TIMEOUT_SEC:
        time.sleep(POLL_INTERVAL_SEC)
        elapsed += POLL_INTERVAL_SEC
        resp = requests.get(
            f"{BASE_URL}{QUERY_PATH}",
            params={"taskId": task_id},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        status = result.get("status", "unknown")
        if status == "success":
            images = result.get("images") or []
            if not images:
                raise RuntimeError(f"TopView returned no images: {result}")
            img = images[0]
            if img.get("status") != "success" or not img.get("filePath"):
                raise RuntimeError(f"TopView image failed: {img}")
            return img
        if status == "fail":
            raise RuntimeError(f"TopView task failed: {result.get('errorMsg')}")
    raise TimeoutError(f"TopView task {task_id} did not complete within {POLL_TIMEOUT_SEC}s")


def _download(file_url: str) -> bytes:
    resp = requests.get(file_url, timeout=120)
    resp.raise_for_status()
    return resp.content


def generate_image_topview(
    model_display_name: str,
    prompt: str,
    style_suffix: str = "",
    negative_prompt: str = "",
    width: int = 768,
    height: int = 1344,
    pass_resolution: bool = True,
) -> bytes:
    """Submit a text-to-image task to TopView, poll until done, return the
    bytes. `model_display_name` must match TopView's display name exactly
    (e.g. "Nano Banana 2", "Nano Banana Pro", "Imagen 4")."""
    full_prompt = f"{prompt}, {style_suffix}" if style_suffix else prompt
    if negative_prompt:
        # TopView doesn't take a negative prompt field; fold into prompt text
        # the same way the Nano Banana 2 provider does.
        full_prompt += f". Avoid: {negative_prompt}"

    aspect = _aspect_ratio(width, height)
    resolution = _resolution(height) if pass_resolution else None

    logger.info(
        "Submitting TopView text2image: model=%s aspect=%s res=%s prompt=%.80s",
        model_display_name, aspect, resolution, full_prompt,
    )
    task_id = _submit(model_display_name, full_prompt, aspect, resolution)
    logger.info("TopView taskId=%s, polling...", task_id)
    img = _poll(task_id)
    logger.info(
        "TopView image ready: %sx%s credits=%s",
        img.get("width"), img.get("height"), img.get("costCredit"),
    )
    return _download(img["filePath"])
