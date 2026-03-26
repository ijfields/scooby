from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.auth import get_current_clerk_user_id
from app.models.user import User

router = APIRouter()


class UserSyncRequest(BaseModel):
    email: str
    display_name: str | None = None
    avatar_url: str | None = None


class UserResponse(BaseModel):
    id: str
    clerk_id: str
    email: str
    display_name: str | None
    avatar_url: str | None
    plan: str

    model_config = {"from_attributes": True}


@router.post("/sync", response_model=UserResponse)
async def sync_user(
    body: UserSyncRequest,
    clerk_id: str = Depends(get_current_clerk_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Create or update local user record from Clerk auth data."""
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            clerk_id=clerk_id,
            email=body.email,
            display_name=body.display_name,
            avatar_url=body.avatar_url,
        )
        db.add(user)
    else:
        user.email = body.email
        if body.display_name is not None:
            user.display_name = body.display_name
        if body.avatar_url is not None:
            user.avatar_url = body.avatar_url

    await db.commit()
    await db.refresh(user)
    return user


@router.get("/me", response_model=UserResponse)
async def get_me(
    clerk_id: str = Depends(get_current_clerk_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user."""
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if user is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not synced yet. Call POST /api/v1/auth/sync first.",
        )
    return user
