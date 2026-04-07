"""Tests for the YouTube-to-Series import pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestYouTubeTranscriptService:
    """Tests for YouTube transcript extraction."""

    @patch("app.services.youtube.transcript.YouTubeTranscriptApi")
    def test_fetch_transcript_returns_text(self, mock_api):
        mock_api.get_transcript.return_value = [
            {"text": "Hello world", "start": 0.0, "duration": 2.0},
            {"text": "This is a test", "start": 2.0, "duration": 3.0},
        ]

        from app.services.youtube.transcript import fetch_transcript

        result = fetch_transcript("dQw4w9WgXcQ")
        assert "Hello world" in result
        assert "This is a test" in result

    @patch("app.services.youtube.transcript.YouTubeTranscriptApi")
    def test_fetch_transcript_handles_no_transcript(self, mock_api):
        from youtube_transcript_api import NoTranscriptFound

        mock_api.get_transcript.side_effect = NoTranscriptFound(
            "dQw4w9WgXcQ", ["en"], []
        )

        from app.services.youtube.transcript import fetch_transcript

        with pytest.raises(Exception):
            fetch_transcript("dQw4w9WgXcQ")

    def test_extract_video_id_from_standard_url(self):
        from app.services.youtube.transcript import extract_video_id

        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_video_id_from_short_url(self):
        from app.services.youtube.transcript import extract_video_id

        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_video_id_from_shorts_url(self):
        from app.services.youtube.transcript import extract_video_id

        assert extract_video_id("https://www.youtube.com/shorts/EG3DtiAwoe8") == "EG3DtiAwoe8"

    def test_extract_video_id_invalid_url_raises(self):
        from app.services.youtube.transcript import extract_video_id

        with pytest.raises((ValueError, Exception)):
            extract_video_id("https://example.com/not-youtube")


class TestSeriesPlanner:
    """Tests for the AI series planner."""

    @patch("app.services.ai.series_planner.settings")
    @patch("app.services.ai.series_planner.anthropic.Anthropic")
    def test_plan_series_returns_episodes(self, mock_anthropic_cls, mock_settings):
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        # Mock Claude response with a valid series plan JSON
        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(
                text='{"series_title": "Test Series", "episodes": [{"episode_number": 1, "title": "Episode 1", "angle": "Introduction", "hook": "What if...", "scenes": []}]}'
            )
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_cls.return_value = mock_client

        from app.services.ai.series_planner import plan_series

        result = plan_series(
            transcript="This is a test transcript about an interesting topic.",
            source_title="Test Video",
            source_channel="Test Channel",
        )

        assert result is not None
        assert "episodes" in result or hasattr(result, "episodes")

    @patch("app.services.ai.series_planner.settings")
    @patch("app.services.ai.series_planner.anthropic.Anthropic")
    def test_plan_series_sends_transcript_to_claude(self, mock_anthropic_cls, mock_settings):
        mock_settings.ANTHROPIC_API_KEY = "test-key"

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text='{"series_title": "X", "episodes": []}')
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic_cls.return_value = mock_client

        from app.services.ai.series_planner import plan_series

        plan_series(
            transcript="The actual transcript content here.",
            source_title="My Video",
            source_channel="My Channel",
        )

        # Verify Claude was called with the transcript in the prompt
        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
        prompt_text = str(messages)
        assert "actual transcript content" in prompt_text


class TestSeriesPlanSchemas:
    """Tests for series plan Pydantic schemas."""

    def test_episode_plan_schema(self):
        from app.schemas.series_plan import EpisodePlan

        ep = EpisodePlan(
            episode_number=1,
            title="The Beginning",
            angle="Origin story",
            hook="It all started with...",
        )
        assert ep.episode_number == 1
        assert ep.title == "The Beginning"

    def test_series_plan_schema(self):
        from app.schemas.series_plan import EpisodePlan, SeriesPlan

        plan = SeriesPlan(
            series_title="My Series",
            episodes=[
                EpisodePlan(episode_number=1, title="Ep1", angle="A1", hook="H1"),
                EpisodePlan(episode_number=2, title="Ep2", angle="A2", hook="H2"),
            ],
        )
        assert len(plan.episodes) == 2
        assert plan.series_title == "My Series"


class TestStorySchemas:
    """Tests for YouTube-related story schema fields."""

    def test_story_create_from_youtube_schema(self):
        from app.schemas.story import StoryCreateFromYouTube

        story = StoryCreateFromYouTube(
            youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            relationship="creator",
            fair_use_acknowledged=True,
        )
        assert story.youtube_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert story.relationship == "creator"
        assert story.fair_use_acknowledged is True
