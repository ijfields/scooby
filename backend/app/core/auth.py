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


async def get_current_user(
    request: Request,
    clerk_id: str = Depends(get_current_clerk_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the local User record for the authenticated Clerk user.

    Auto-creates the user on first request so the frontend doesn't
    need to call /auth/sync manually.
    """
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if user is None:
        # Extract email from Clerk JWT claims
        token = _extract_token(request)
        try:
            claims = jwt.decode(token, options={"verify_signature": False})
            email = claims.get("email") or claims.get("primary_email") or f"{clerk_id}@clerk.user"
        except Exception:
            email = f"{clerk_id}@clerk.user"

        user = User(clerk_id=clerk_id, email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user
