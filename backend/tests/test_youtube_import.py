"""Tests for the YouTube-to-Series import pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestYouTubeTranscriptService:
    """Tests for YouTube transcript extraction."""

    @patch("app.services.youtube.transcript.YouTubeTranscriptApi")
    def test_fetch_transcript_returns_text(self, mock_api):
        # New API: YouTubeTranscriptApi() instance, .fetch() returns snippet
        # objects exposing .text (not the old classmethod-returns-dicts shape).
        mock_api.return_value.fetch.return_value = [
            MagicMock(text="Hello world"),
            MagicMock(text="This is a test"),
        ]

        from app.services.youtube.transcript import fetch_transcript

        result = fetch_transcript("dQw4w9WgXcQ")
        assert "Hello world" in result
        assert "This is a test" in result

    @patch("app.services.youtube.transcript.YouTubeTranscriptApi")
    def test_fetch_transcript_handles_no_transcript(self, mock_api):
        from youtube_transcript_api import NoTranscriptFound

        mock_api.return_value.fetch.side_effect = NoTranscriptFound(
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


def _valid_plan_json(n_episodes: int = 3) -> str:
    """Build a JSON series plan that satisfies the SeriesPlan schema —
    total_episodes in [3, 8] and matching the episode count (see
    series_planner._validate_and_parse)."""
    import json

    episodes = [
        {
            "episode_number": i + 1,
            "title": f"Episode {i + 1}",
            "angle": "An angle",
            "key_content": "Condensed narrative content for the episode.",
            "target_duration_sec": 75,
            "hook_suggestion": "A compelling hook.",
        }
        for i in range(n_episodes)
    ]
    return json.dumps(
        {
            "series_title": "Test Series",
            "series_thesis": "The overarching theme.",
            "total_episodes": n_episodes,
            "episodes": episodes,
        }
    )


class TestSeriesPlanner:
    """Tests for the AI series planner."""

    @patch("app.services.ai.series_planner.client")
    def test_generate_series_plan_returns_episodes(self, mock_client):
        # The Anthropic client is constructed at module import, so patch the
        # already-built `client`, not the anthropic.Anthropic class.
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=_valid_plan_json(3))]
        mock_client.messages.create.return_value = mock_message

        from app.services.ai.series_planner import generate_series_plan

        result = generate_series_plan(
            transcript="This is a test transcript about an interesting topic.",
            video_title="Test Video",
            channel="Test Channel",
            duration_sec=600,
        )

        assert result is not None
        assert hasattr(result, "episodes")
        assert len(result.episodes) == 3

    @patch("app.services.ai.series_planner.client")
    def test_generate_series_plan_sends_transcript_to_claude(self, mock_client):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=_valid_plan_json(3))]
        mock_client.messages.create.return_value = mock_message

        from app.services.ai.series_planner import generate_series_plan

        generate_series_plan(
            transcript="The actual transcript content here.",
            video_title="My Video",
            channel="My Channel",
            duration_sec=600,
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
            key_content="Condensed narrative content for the episode.",
            hook_suggestion="It all started with...",
        )
        assert ep.episode_number == 1
        assert ep.title == "The Beginning"

    def test_series_plan_schema(self):
        from app.schemas.series_plan import EpisodePlan, SeriesPlan

        plan = SeriesPlan(
            series_title="My Series",
            series_thesis="The overarching theme of the series.",
            total_episodes=3,  # schema enforces 3-8 episodes
            episodes=[
                EpisodePlan(
                    episode_number=1, title="Ep1", angle="A1",
                    key_content="C1", hook_suggestion="H1",
                ),
                EpisodePlan(
                    episode_number=2, title="Ep2", angle="A2",
                    key_content="C2", hook_suggestion="H2",
                ),
                EpisodePlan(
                    episode_number=3, title="Ep3", angle="A3",
                    key_content="C3", hook_suggestion="H3",
                ),
            ],
        )
        assert len(plan.episodes) == 3
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
