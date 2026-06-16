"""Admin-only endpoints — providers & costs overview."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.auth import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.video_asset import VideoAsset
from app.services.billing import (
    PROVIDER_CATALOG,
    VENDORS,
    get_vendor_balances,
)
from app.services.image.providers import IMAGE_PROVIDERS
from app.services.video.animation_providers import TIER_ANIMATION_MAP

router = APIRouter()


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Allow only emails listed in ADMIN_EMAILS. Empty list = locked down."""
    allow = settings.admin_emails_list
    if user.email.lower() not in allow:
        if not allow:
            detail = (
                f"Admin access required. ADMIN_EMAILS is not set on the backend. "
                f"Add ADMIN_EMAILS={user.email} to the backend service and redeploy."
            )
        else:
            detail = (
                f"Admin access required. Your account email is '{user.email}', which "
                f"is not in the allow-list. Add it to ADMIN_EMAILS on the backend."
            )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    return user


@router.get("/admin/providers")
async def providers_overview(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Active providers, fallback chain, live vendor balances, cost models, and
    real per-provider usage counts (from generated-asset metadata)."""
    balances = get_vendor_balances()

    # Real usage: count generated assets grouped by the provider that made them.
    rows = (
        await db.execute(
            select(
                VideoAsset.metadata_["provider"].astext,
                func.count(),
            )
            .where(VideoAsset.asset_type.in_(["image", "animation"]))
            .group_by(VideoAsset.metadata_["provider"].astext)
        )
    ).all()
    usage = {(name or "unknown"): count for name, count in rows}

    def _provider_row(key: str) -> dict:
        cat = PROVIDER_CATALOG.get(key, {})
        vendor = cat.get("vendor")
        return {
            "name": key,
            "vendor": vendor,
            "vendor_label": VENDORS.get(vendor, vendor),
            "kind": cat.get("kind"),
            "cost_model": cat.get("cost_model", "Unknown"),
            "approx_price": cat.get("approx_price", "—"),
            "balance": balances.get(vendor) if vendor else None,
            "assets_generated": usage.get(key, 0),
        }

    image_providers = [_provider_row(k) for k in IMAGE_PROVIDERS]
    animation_providers = [
        _provider_row(k)
        for k, v in PROVIDER_CATALOG.items()
        if v.get("kind") == "animation"
    ]

    return {
        "active": {
            "image_provider": settings.IMAGE_PROVIDER,
            "image_fallbacks": settings.image_provider_fallbacks_list,
            "animation_mode": settings.VIDEO_ANIMATION_PROVIDER,
            "tier_animation_map": TIER_ANIMATION_MAP,
        },
        "image_providers": image_providers,
        "animation_providers": animation_providers,
        "usage": usage,
    }
