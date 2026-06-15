"""Provider cost catalog + live balance lookups for the admin page.

Balance APIs verified 2026-06-15:
- Stability:  GET https://api.stability.ai/v1/user/balance      -> {"credits": N}
- TopView:    GET https://api.topview.ai/user/credit/detail      -> {"result":{"remainCredit": N}}  (needs Topview-Uid header)
- WaveSpeed:  GET https://api.wavespeed.ai/api/v3/balance        -> {"data":{"balance": N}}  (USD)
- Google AI Studio: no balance API — managed in Google Cloud Console.

Kept httpx-only (no DB/Celery) so it can be unit-tested in isolation. Usage
counts are aggregated by the admin endpoint from VideoAsset metadata.
"""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 15

# vendor key -> display label
VENDORS = {
    "stability": "Stability AI",
    "google": "Google AI Studio",
    "topview": "TopView",
    "wavespeed": "WaveSpeed",
}

# provider key (as used in IMAGE_PROVIDER / VIDEO_ANIMATION_PROVIDER) -> catalog
PROVIDER_CATALOG: dict[str, dict] = {
    # ── image ──
    "stability": {
        "vendor": "stability", "kind": "image",
        "cost_model": "Pay per image (no subscription)",
        "approx_price": "~$0.03–0.06 / image",
    },
    "nanobanana2": {
        "vendor": "google", "kind": "image",
        "cost_model": "Prepay per image (no subscription)",
        "approx_price": "~$0.03–0.07 / image",
    },
    "topview_nano_banana_2": {
        "vendor": "topview", "kind": "image",
        "cost_model": "Subscription (Pro) + credits per image",
        "approx_price": "~0.40 credits / image @1K",
    },
    "topview_nano_banana_pro": {
        "vendor": "topview", "kind": "image",
        "cost_model": "Subscription (Pro) + credits per image",
        "approx_price": "~0.80 credits / image @1K",
    },
    "topview_imagen_4": {
        "vendor": "topview", "kind": "image",
        "cost_model": "Subscription (Pro) + credits per image",
        "approx_price": "~0.50 credits / image",
    },
    # ── animation ──
    "kling_std": {
        "vendor": "wavespeed", "kind": "animation",
        "cost_model": "Pay per clip (no subscription)",
        "approx_price": "~$0.35–0.50 / 5s clip",
    },
    "kling_pro": {
        "vendor": "wavespeed", "kind": "animation",
        "cost_model": "Pay per clip (no subscription)",
        "approx_price": "~$1.20 / 5s clip",
    },
}


def _balance(available: bool, balance=None, unit=None, error=None) -> dict:
    return {"available": available, "balance": balance, "unit": unit, "error": error}


def _fetch_stability_balance() -> dict:
    if not settings.STABILITY_API_KEY:
        return _balance(False, error="No STABILITY_API_KEY configured")
    try:
        r = httpx.get(
            "https://api.stability.ai/v1/user/balance",
            headers={"Authorization": f"Bearer {settings.STABILITY_API_KEY}"},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        return _balance(True, balance=r.json().get("credits"), unit="credits")
    except Exception as e:  # noqa: BLE001
        return _balance(False, error=f"{type(e).__name__}: {str(e)[:120]}")


def _fetch_topview_balance() -> dict:
    if not settings.TOPVIEW_API_KEY or not settings.TOPVIEW_UID:
        return _balance(False, error="No TOPVIEW_API_KEY / TOPVIEW_UID configured")
    try:
        r = httpx.get(
            "https://api.topview.ai/user/credit/detail",
            headers={
                "Authorization": f"Bearer {settings.TOPVIEW_API_KEY}",
                "Topview-Uid": settings.TOPVIEW_UID,
            },
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        remain = (r.json().get("result") or {}).get("remainCredit")
        return _balance(True, balance=remain, unit="credits")
    except Exception as e:  # noqa: BLE001
        return _balance(False, error=f"{type(e).__name__}: {str(e)[:120]}")


def _fetch_wavespeed_balance() -> dict:
    if not settings.WAVESPEED_API_KEY:
        return _balance(False, error="No WAVESPEED_API_KEY configured")
    try:
        r = httpx.get(
            "https://api.wavespeed.ai/api/v3/balance",
            headers={"Authorization": f"Bearer {settings.WAVESPEED_API_KEY}"},
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        bal = (r.json().get("data") or {}).get("balance")
        return _balance(True, balance=bal, unit="USD")
    except Exception as e:  # noqa: BLE001
        return _balance(False, error=f"{type(e).__name__}: {str(e)[:120]}")


_VENDOR_BALANCE_FETCHERS = {
    "stability": _fetch_stability_balance,
    "topview": _fetch_topview_balance,
    "wavespeed": _fetch_wavespeed_balance,
    "google": None,  # no balance API
}


def get_vendor_balances() -> dict[str, dict]:
    """Live balance per vendor. Each entry is the _balance() shape. Vendors with
    no balance API (Google) report available=False with an explanatory error."""
    out: dict[str, dict] = {}
    for vendor, fetch in _VENDOR_BALANCE_FETCHERS.items():
        if fetch is None:
            out[vendor] = _balance(
                False, error="No balance API — manage in Google Cloud Console"
            )
        else:
            out[vendor] = fetch()
    return out
