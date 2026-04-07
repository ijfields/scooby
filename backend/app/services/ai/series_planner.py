"""AI Series Planner — the core differentiator.

Takes a full video transcript and plans a multi-episode series of
standalone 60-90 second visual stories. Each episode has its own
dramatic angle and condensed content for scene breakdown.
"""

from __future__ import annotations

import json
import logging

import anthropic
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.series_plan import SeriesPlan

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SERIES_PLANNER_SYSTEM_PROMPT = """You are a series producer and editorial strategist specializing in
transforming long-form video content into short-form vertical drama series.

Given a video transcript, plan a series of 3-8 standalone 60-90 second visual story episodes.
You are NOT clipping the video. You are REIMAGINING the content as visual storytelling.

## Your Job

Analyze the full transcript for:
- The core argument or narrative arc
- Key themes, turning points, and emotional beats
- Historical facts, anecdotes, or examples that make compelling standalone stories
- The speaker's thesis and how they build toward it

Then plan a series where each episode:
1. Has a compelling, specific title (not generic — "The Lily White Movement
   Republicans Don't Mention" not "Political History Part 2")
2. Has a clear thesis/angle (ONE argument per episode)
3. Is SELF-CONTAINED — viewable without seeing other episodes
4. Follows dramatic storytelling structure (not an information dump)
5. Includes condensed key content from the transcript (1000-2000 words)
   that captures the essential quotes, facts, and narrative for that angle
6. Has a suggested viewing order that builds toward the overall thesis

## Key Content Rules

The `key_content` field for each episode must be a CONDENSED, NARRATIVE version
of the relevant transcript portion — NOT a raw copy-paste. It should:
- Read like a short story or editorial, not a transcript
- Include the most powerful quotes (attributed to speakers)
- Provide enough context for someone to understand the argument
- Be 1000-2000 words (will be fed into a scene breakdown system)
- Be written in a way that works as voiceover narration

## Attribution

Always preserve the original speaker's voice and attribution. If the speaker
references books, people, or events, include those details — they add credibility
and depth to the visual storytelling.

## Output Format

Return ONLY valid JSON matching this exact schema (no markdown, no explanation):

{
  "series_title": "Compelling series title (max 100 chars)",
  "series_thesis": "The overarching argument or theme in 1-2 sentences",
  "total_episodes": <number between 3 and 8>,
  "episodes": [
    {
      "episode_number": <1-8>,
      "title": "Specific episode title (max 100 chars)",
      "angle": "The thesis/angle for this episode in 1-2 sentences",
      "key_content": "Condensed narrative content (1000-2000 words)...",
      "target_duration_sec": <60-90>,
      "hook_suggestion": "A compelling opening line or visual for this episode"
    }
  ]
}"""


class SeriesPlanError(Exception):
    pass


def generate_series_plan(
    transcript: str,
    video_title: str,
    channel: str,
    duration_sec: int,
) -> SeriesPlan:
    """Call Claude to plan a multi-episode series from a video transcript.

    Args:
        transcript: Cleaned transcript text.
        video_title: Original video title.
        channel: Channel/creator name.
        duration_sec: Original video duration in seconds.

    Returns:
        Validated SeriesPlan with 3-8 episode outlines.
    """
    duration_min = duration_sec // 60

    user_prompt = f"""Plan a visual story series from the following video transcript.

Video: "{video_title}" by {channel} ({duration_min} minutes)

Transcript:
---
{transcript}
---

Create a series of standalone 60-90 second visual story episodes from this content.
Each episode should have a unique angle and be self-contained."""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=SERIES_PLANNER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.7,
    )

    raw_response = message.content[0].text
    return _validate_and_parse(raw_response)


def _validate_and_parse(raw_response: str) -> SeriesPlan:
    """Parse and validate Claude's JSON response."""
    json_str = raw_response.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise SeriesPlanError(f"Claude returned invalid JSON: {e}")

    try:
        plan = SeriesPlan.model_validate(data)
    except ValidationError as e:
        raise SeriesPlanError(f"Series plan failed validation: {e}")

    if len(plan.episodes) != plan.total_episodes:
        raise SeriesPlanError(
            f"Episode count mismatch: total_episodes={plan.total_episodes} "
            f"but got {len(plan.episodes)} episodes"
        )

    return plan
