"""Tests for the pluggable image generation provider system."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.image.providers import (
    IMAGE_PROVIDERS,
    NanoBanana2Provider,
    StabilityProvider,
    get_image_provider,
)


class TestProviderRegistry:
    """Tests for the provider registry and lookup."""

    def test_registry_contains_stability(self):
        assert "stability" in IMAGE_PROVIDERS

    def test_registry_contains_nanobanana2(self):
        assert "nanobanana2" in IMAGE_PROVIDERS

    def test_get_provider_by_name_stability(self):
        provider = get_image_provider("stability")
        assert provider.name == "stability"
        assert isinstance(provider, StabilityProvider)

    def test_get_provider_by_name_nanobanana2(self):
        provider = get_image_provider("nanobanana2")
        assert provider.name == "nanobanana2"
        assert isinstance(provider, NanoBanana2Provider)

    def test_get_provider_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown image provider"):
            get_image_provider("nonexistent_model")

    @patch("app.services.image.providers.settings")
    def test_get_provider_uses_config_default(self, mock_settings):
        mock_settings.IMAGE_PROVIDER = "nanobanana2"
        provider = get_image_provider()
        assert provider.name == "nanobanana2"

    @patch("app.services.image.providers.settings")
    def test_explicit_name_overrides_config(self, mock_settings):
        mock_settings.IMAGE_PROVIDER = "nanobanana2"
        provider = get_image_provider("stability")
        assert provider.name == "stability"


class TestStabilityProvider:
    """Tests for the Stability AI provider wrapper."""

    @patch("app.services.image.generator.generate_image")
    def test_generate_delegates_to_generator(self, mock_gen):
        mock_gen.return_value = b"fake-png-bytes"
        provider = StabilityProvider()
        result = provider.generate(
            prompt="a sunset",
            style_suffix="cinematic",
            negative_prompt="blurry",
            cfg_scale=8,
        )
        assert result == b"fake-png-bytes"
        mock_gen.assert_called_once_with(
            prompt="a sunset",
            style_suffix="cinematic",
            negative_prompt="blurry",
            cfg_scale=8,
            width=768,
            height=1344,
        )


class TestNanoBanana2Provider:
    """Tests for the Nanobanana 2 provider wrapper."""

    @patch("app.services.image.nanobanana2.generate_image_nb2")
    def test_generate_delegates_to_nb2(self, mock_gen):
        mock_gen.return_value = b"fake-nb2-png"
        provider = NanoBanana2Provider()
        result = provider.generate(
            prompt="a sunset",
            style_suffix="cinematic",
        )
        assert result == b"fake-nb2-png"
        mock_gen.assert_called_once()


class TestNanoBanana2Service:
    """Tests for the Nanobanana 2 image generation service."""

    @patch("app.services.image.nanobanana2.settings")
    @patch("app.services.image.nanobanana2.genai.Client")
    def test_generate_image_returns_png_bytes(self, mock_client_cls, mock_settings):
        mock_settings.GOOGLE_API_KEY = "test-key"

        # Mock the Gemini response with an image part
        mock_image = MagicMock()
        mock_buf = MagicMock()

        mock_part = MagicMock()
        mock_part.inline_data = True
        mock_part.as_image.return_value = mock_image

        mock_response = MagicMock()
        mock_response.parts = [mock_part]

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        # Mock image.save to write known bytes
        def fake_save(buf, format=None):
            buf.write(b"PNG-DATA")

        mock_image.save.side_effect = fake_save

        from app.services.image.nanobanana2 import generate_image_nb2

        result = generate_image_nb2(prompt="a sunset", style_suffix="cinematic")
        assert b"PNG-DATA" in result

        # Verify the model was called correctly
        mock_client.models.generate_content.assert_called_once()
        call_kwargs = mock_client.models.generate_content.call_args
        assert call_kwargs.kwargs["model"] == "gemini-3.1-flash-image-preview"

    @patch("app.services.image.nanobanana2.settings")
    @patch("app.services.image.nanobanana2.genai.Client")
    def test_generate_raises_on_no_image(self, mock_client_cls, mock_settings):
        mock_settings.GOOGLE_API_KEY = "test-key"

        # Response with text only, no image
        mock_part = MagicMock()
        mock_part.inline_data = None
        mock_part.text = "I cannot generate that image"

        mock_response = MagicMock()
        mock_response.parts = [mock_part]

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from app.services.image.nanobanana2 import generate_image_nb2

        with pytest.raises(RuntimeError, match="no image data"):
            generate_image_nb2(prompt="something blocked")

    @patch("app.services.image.nanobanana2.settings")
    @patch("app.services.image.nanobanana2.genai.Client")
    def test_negative_prompt_appended(self, mock_client_cls, mock_settings):
        mock_settings.GOOGLE_API_KEY = "test-key"

        mock_part = MagicMock()
        mock_part.inline_data = True
        mock_part.as_image.return_value = MagicMock()
        mock_part.as_image.return_value.save = lambda buf, format=None: buf.write(b"x")

        mock_response = MagicMock()
        mock_response.parts = [mock_part]

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        from app.services.image.nanobanana2 import generate_image_nb2

        generate_image_nb2(prompt="sunset", negative_prompt="blurry, low quality")

        call_args = mock_client.models.generate_content.call_args
        prompt_sent = call_args.kwargs["contents"][0]
        assert "Avoid: blurry, low quality" in prompt_sent
