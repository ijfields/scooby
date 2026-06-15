"""User-facing translation of generation-pipeline errors.

Kept free of Celery/DB imports so it can be unit-tested in isolation and reused
by any layer that needs to present a failure to a non-technical writer.
"""

from __future__ import annotations


def friendly_error(e: Exception) -> str:
    """Translate a pipeline exception into a message a non-technical writer can
    act on. Falls back to the raw message so we never hide detail entirely."""
    from app.services.image.providers import AllImageProvidersFailedError

    raw = str(e)
    low = raw.lower()

    if isinstance(e, AllImageProvidersFailedError):
        names = ", ".join(name for name, _ in e.attempts) or "all providers"
        if any(k in low for k in ("resource_exhausted", "429", "depleted", "quota", "credit")):
            return (
                "Image generation is out of credits on every configured provider "
                f"({names}). Top up the provider's billing or switch IMAGE_PROVIDER, "
                "then try again."
            )
        return (
            f"Image generation failed on every configured provider ({names}). "
            "See logs for the per-provider error."
        )

    if any(k in low for k in ("resource_exhausted", "depleted", "quota")) or "429" in raw:
        return (
            "An AI provider is out of credits or rate-limited. Check the provider's "
            "billing/quota and try again."
        )

    return f"Generation failed: {raw[:300]}"
