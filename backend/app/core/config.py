from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    ENV: str = "development"
    SECRET_KEY: str = "change-me-to-a-real-secret-in-production"
    ALLOWED_ORIGINS: str = "http://localhost:3001,http://localhost:3000"
    LOG_LEVEL: str = "DEBUG"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://scooby:scooby_dev@localhost:5433/scooby"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6380/0"
    CELERY_BROKER_URL: str = "redis://localhost:6380/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6380/1"

    # AI Services
    ANTHROPIC_API_KEY: str = ""
    STABILITY_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""       # Nanobanana 2 / Gemini image generation
    WAVESPEED_API_KEY: str = ""    # Kling 3.0 image-to-video via WaveSpeed

    # Generation providers (pluggable — swap models via config)
    IMAGE_PROVIDER: str = "stability"       # stability | nanobanana2
    VIDEO_ANIMATION_PROVIDER: str = "none"  # none | kling_std | kling_pro

    # S3
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "scooby-assets-dev"
    S3_PUBLIC_URL: str = ""

    # Clerk
    CLERK_ISSUER_URL: str = ""
    CLERK_SECRET_KEY: str = ""  # used to fetch user details (email/name/avatar) from Clerk Backend API

    # Video rendering
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"
    REMOTION_SIDECAR_PATH: str = "./remotion"  # deprecated — ffmpeg is now used

    # Rate limits
    MAX_EPISODES_PER_USER_DAY: int = 10
    MAX_STORY_LENGTH_CHARS: int = 5000

    @property
    def DATABASE_URL_ASYNC(self) -> str:
        """Async driver URL for SQLAlchemy async engine."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync driver URL for Alembic migrations."""
        url = self.DATABASE_URL
        return url.replace("+asyncpg", "").replace("postgresql://", "postgresql://", 1)

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
