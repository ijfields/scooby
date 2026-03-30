"""Import all models so Alembic autogenerate can detect them."""

from app.models.user import User
from app.models.story import Story
from app.models.style_preset import StylePreset
from app.models.episode import Episode
from app.models.scene import Scene
from app.models.video_asset import VideoAsset
from app.models.generation_job import GenerationJob
from app.models.share_token import ShareToken

__all__ = [
    "User",
    "Story",
    "StylePreset",
    "Episode",
    "Scene",
    "VideoAsset",
    "GenerationJob",
    "ShareToken",
]
