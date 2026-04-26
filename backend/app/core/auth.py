import jwt
import httpx
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.models.user import User

_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    """Fetch Clerk's JWKS (cached in memory)."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache

    clerk_domain = settings.CLERK_ISSUER_URL
    if not clerk_domain:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_ISSUER_URL not configured",
        )

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{clerk_domain}/.well-known/jwks.json")
        resp.raise_for_status()
        _jwks_cache = resp.json()
        return _jwks_cache


def _extract_token(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    return auth[7:]


async def get_current_clerk_user_id(request: Request) -> str:
    """Verify Clerk JWT and return the Clerk user ID (sub claim)."""
    token = _extract_token(request)

    try:
        jwks = await _get_jwks()
        public_keys = {}
        for key_data in jwks.get("keys", []):
            kid = key_data["kid"]
            public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)

        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if kid not in public_keys:
            # Invalidate cache and retry once
            global _jwks_cache
            _jwks_cache = None
            jwks = await _get_jwks()
            for key_data in jwks.get("keys", []):
                k = key_data["kid"]
                public_keys[k] = jwt.algorithms.RSAAlgorithm.from_jwk(key_data)
            if kid not in public_keys:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unable to find appropriate key",
                )

        payload = jwt.decode(
            token,
            key=public_keys[kid],
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload["sub"]

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


async def fetch_clerk_user(clerk_id: str) -> dict | None:
    """Fetch a user's profile (email, name, avatar) from Clerk's Backend API.

    Returns a dict with keys 'email', 'display_name', 'avatar_url' on success,
    or None if CLERK_SECRET_KEY isn't configured or the request fails.
    """
    if not settings.CLERK_SECRET_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"https://api.clerk.com/v1/users/{clerk_id}",
                headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError:
        return None

    # Pick the primary email if marked, else the first one
    primary_id = data.get("primary_email_address_id")
    emails = data.get("email_addresses") or []
    email = next(
        (e.get("email_address") for e in emails if e.get("id") == primary_id),
        None,
    ) or (emails[0].get("email_address") if emails else None)

    first = data.get("first_name") or ""
    last = data.get("last_name") or ""
    display_name = f"{first} {last}".strip() or None

    return {
        "email": email,
        "display_name": display_name,
        "avatar_url": data.get("image_url"),
    }


async def get_current_user(
    request: Request,
    clerk_id: str = Depends(get_current_clerk_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the local User record for the authenticated Clerk user.

    Auto-creates the user on first request so the frontend doesn't
    need to call /auth/sync manually. New records get email + display_name
    + avatar from Clerk's Backend API; falls back to JWT claims, then
    to a synthetic email if all else fails.
    """
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    # New user — try Clerk's Backend API first for the real email
    profile = await fetch_clerk_user(clerk_id)

    if profile and profile["email"]:
        email = profile["email"]
        display_name = profile["display_name"]
        avatar_url = profile["avatar_url"]
    else:
        # Fallback: JWT claims (only works if Clerk JWT template includes email)
        try:
            claims = jwt.decode(_extract_token(request), options={"verify_signature": False})
            email = claims.get("email") or claims.get("primary_email") or f"{clerk_id}@clerk.user"
        except Exception:
            email = f"{clerk_id}@clerk.user"
        display_name = None
        avatar_url = None

    user = User(
        clerk_id=clerk_id,
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
