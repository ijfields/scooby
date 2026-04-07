"""Tests for the pluggable video animation provider system."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.video.animation_providers import (
    ANIMATION_PROVIDERS,
    KlingProProvider,
    KlingStdProvider,
    get_animation_provider,
)


class TestAnimationProviderRegistry:
    """Tests for the animation provider registry and lookup."""

    def test_registry_contains_kling_std(self):
        assert "kling_std" in ANIMATION_PROVIDERS

    def test_registry_contains_kling_pro(self):
        assert "kling_pro" in ANIMATION_PROVIDERS

    def test_get_provider_kling_std(self):
        provider = get_animation_provider("kling_std")
        assert provider is not None
        assert provider.name == "kling_std"
        assert isinstance(provider, KlingStdProvider)

    def test_get_provider_kling_pro(self):
        provider = get_animation_provider("kling_pro")
        assert provider is not None
        assert provider.name == "kling_pro"
        assert isinstance(provider, KlingProProvider)

    def test_get_provider_none_returns_none(self):
        """Storyboard mode — no animation provider."""
        provider = get_animation_provider("none")
        assert provider is None

    def test_get_provider_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown animation provider"):
            get_animation_provider("nonexistent_model")

    @patch("app.services.video.animation_providers.settings")
    def test_get_provider_uses_config_default(self, mock_settings):
        mock_settings.VIDEO_ANIMATION_PROVIDER = "kling_pro"
        provider = get_animation_provider()
        assert provider.name == "kling_pro"

    @patch("app.services.video.animation_providers.settings")
    def test_config_none_returns_none(self, mock_settings):
        mock_settings.VIDEO_ANIMATION_PROVIDER = "none"
        provider = get_animation_provider()
        assert provider is None


class TestKlingAnimation:
    """Tests for the Kling 3.0 animation service."""

    @patch("app.services.video.animation.settings")
    @patch("app.services.video.animation.httpx.Client")
    @patch("app.services.video.animation.time.sleep")
    def test_animate_image_success(self, mock_sleep, mock_client_cls, mock_settings):
        mock_settings.WAVESPEED_API_KEY = "test-key"

        # Mock submit response
        submit_resp = MagicMock()
        submit_resp.json.return_value = {"data": {"id": "task-123"}}
        submit_resp.raise_for_status = MagicMock()

        # Mock poll response — completed immediately
        poll_resp = MagicMock()
        poll_resp.json.return_value = {
            "data": {
                "status": "completed",
                "outputs": ["https://example.com/video.mp4"],
            }
        }

        # Mock video download
        download_resp = MagicMock()
        download_resp.content = b"fake-mp4-video-bytes"
        download_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        # First call = submit, second = poll, third = download
        call_count = {"n": 0}
        responses = [submit_resp, poll_resp, download_resp]

        def side_effect(*args, **kwargs):
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=MagicMock())
            ctx.__exit__ = MagicMock(return_value=False)
            return ctx

        mock_client.post.return_value = submit_resp
        mock_client.get.side_effect = [poll_resp, download_resp]
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

        from app.services.video.animation import animate_image

        result = animate_image(
            image_url="https://example.com/scene.png",
            prompt="slow zoom in",
            duration=5,
            model_key="kling_std",
            poll_interval=0,
        )
        assert result == b"fake-mp4-video-bytes"

    @patch("app.services.video.animation.settings")
    def test_animate_unknown_model_raises(self, mock_settings):
        from app.services.video.animation import animate_image

        with pytest.raises(ValueError, match="Unknown animation model"):
            animate_image(
                image_url="https://example.com/scene.png",
                model_key="nonexistent",
            )

    def test_kling_models_mapping(self):
        from app.services.video.animation import KLING_MODELS

        assert KLING_MODELS["kling_std"] == "kling-v3.0-std"
        assert KLING_MODELS["kling_pro"] == "kling-v3.0-pro"


class TestKlingProviderDelegation:
    """Tests that provider classes delegate correctly."""

    @patch("app.services.video.animation.animate_image")
    def test_std_provider_delegates(self, mock_animate):
        mock_animate.return_value = b"video-bytes"
        provider = KlingStdProvider()
        result = provider.animate(
            image_url="https://example.com/img.png",
            prompt="zoom in",
            duration=5,
        )
        assert result == b"video-bytes"
        mock_animate.assert_called_once_with(
            image_url="https://example.com/img.png",
            prompt="zoom in",
            duration=5,
            model_key="kling_std",
        )

    @patch("app.services.video.animation.animate_image")
    def test_pro_provider_delegates(self, mock_animate):
        mock_animate.return_value = b"pro-video-bytes"
        provider = KlingProProvider()
        result = provider.animate(
            image_url="https://example.com/img.png",
            prompt="dramatic push",
            duration=8,
        )
        mock_animate.assert_called_once_with(
            image_url="https://example.com/img.png",
            prompt="dramatic push",
            duration=8,
            model_key="kling_pro",
        )
