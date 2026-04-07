"""Tests for the pipeline integration with pluggable providers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestPipelineImageProviderIntegration:
    """Tests that the pipeline correctly uses the provider registry."""

    @patch("app.services.image.providers.settings")
    def test_pipeline_uses_configured_provider(self, mock_settings):
        """Verify the pipeline reads IMAGE_PROVIDER from settings."""
        mock_settings.IMAGE_PROVIDER = "stability"
        from app.services.image.providers import get_image_provider

        provider = get_image_provider()
        assert provider.name == "stability"

        mock_settings.IMAGE_PROVIDER = "nanobanana2"
        provider = get_image_provider()
        assert provider.name == "nanobanana2"

    @patch("app.services.video.animation_providers.settings")
    def test_pipeline_skips_animation_when_none(self, mock_settings):
        """Storyboard mode should return None for animation provider."""
        mock_settings.VIDEO_ANIMATION_PROVIDER = "none"
        from app.services.video.animation_providers import get_animation_provider

        provider = get_animation_provider()
        assert provider is None


class TestConfigSettings:
    """Tests for the new config settings."""

    def test_config_has_generation_provider_fields(self):
        from app.core.config import Settings

        # Verify the fields exist with defaults
        s = Settings(
            DATABASE_URL="postgresql+asyncpg://x:x@localhost/x",
            REDIS_URL="redis://localhost",
        )
        assert s.IMAGE_PROVIDER == "stability"
        assert s.VIDEO_ANIMATION_PROVIDER == "none"
        assert s.GOOGLE_API_KEY == ""
        assert s.WAVESPEED_API_KEY == ""

    def test_config_accepts_nanobanana2_provider(self):
        from app.core.config import Settings

        s = Settings(
            DATABASE_URL="postgresql+asyncpg://x:x@localhost/x",
            REDIS_URL="redis://localhost",
            IMAGE_PROVIDER="nanobanana2",
            GOOGLE_API_KEY="test-key",
        )
        assert s.IMAGE_PROVIDER == "nanobanana2"
        assert s.GOOGLE_API_KEY == "test-key"

    def test_config_accepts_kling_provider(self):
        from app.core.config import Settings

        s = Settings(
            DATABASE_URL="postgresql+asyncpg://x:x@localhost/x",
            REDIS_URL="redis://localhost",
            VIDEO_ANIMATION_PROVIDER="kling_std",
            WAVESPEED_API_KEY="test-key",
        )
        assert s.VIDEO_ANIMATION_PROVIDER == "kling_std"
        assert s.WAVESPEED_API_KEY == "test-key"


class TestEpisodeModelGenerationTier:
    """Tests for the generation_tier field on Episode model."""

    def test_episode_model_has_generation_tier(self):
        from app.models.episode import Episode

        # Verify the column exists in the model
        assert hasattr(Episode, "generation_tier")

    def test_generation_tier_column_properties(self):
        from app.models.episode import Episode

        col = Episode.__table__.columns["generation_tier"]
        assert not col.nullable
        assert str(col.server_default.arg) == "standard"
