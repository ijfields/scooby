from __future__ import annotations

import json
import logging

import anthropic
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

STORY_BREAKDOWN_SYSTEM_PROMPT = """You are a professional story editor and video producer specializing in
short-form vertical drama content (60-90 second videos for social media).

Your job is to take raw story text and break it into exactly 5-7 dramatic beats
optimized for visual storytelling. Each beat maps to one scene in the final video.

## Beat Structure

Every story MUST follow this dramatic arc:

1. **hook** — The opening 3-5 seconds that grabs attention. A striking visual moment
   or provocative statement. This is the most important beat for retention.
2. **setup** — Establish the character, situation, and stakes. The audience must
   understand WHO and WHAT within 10-15 seconds.
3. **escalation_1** — First complication or twist. Raise the emotional stakes.
4. **escalation_2** — (Optional) Second complication. Deepen the conflict.
5. **escalation_3** — (Optional) Third complication or point of no return.
6. **climax** — The peak emotional moment. The confrontation, revelation, or turning point.
7. **button** — The final 3-5 seconds. A punchy ending — cliffhanger, ironic twist,
   or emotional resolution. Leave the audience wanting more.

## Rules

- Minimum 5 beats, maximum 7 beats. Choose based on story complexity.
- Total duration across all beats MUST sum to 60-90 seconds.
- Each beat duration: minimum 8 seconds, maximum 18 seconds.
- The hook beat should be 3-8 seconds.
- The button beat should be 3-8 seconds.
- visual_description must describe a SINGLE static image (not a sequence).
  Be specific about composition, lighting, colors, character appearance, and emotion.
  Write it as an image generation prompt.
- narration_text is the voiceover script for that beat. Keep it concise and dramatic.
  Match the word count to approximately (duration_sec * 2.5) words for natural pacing.
- Use present tense for narration to create immediacy.

## Output Format

Return ONLY valid JSON matching this exact schema (no markdown, no explanation):

{
  "title": "Short episode title (max 60 chars)",
  "total_duration_sec": <number between 60 and 90>,
  "beats": [
    {
      "beat_number": <1-7>,
      "beat_label": "<hook|setup|escalation_1|escalation_2|escalation_3|climax|button>",
      "visual_description": "<detailed image prompt for this scene>",
      "narration_text": "<voiceover script for this beat>",
      "duration_sec": <number between 3 and 18>
    }
  ]
}"""


class SceneBeat(BaseModel):
    beat_number: int
    beat_label: str
    visual_description: str
    narration_text: str
    duration_sec: float = Field(ge=3, le=18)


class SceneBreakdown(BaseModel):
    title: str
    total_duration_sec: float = Field(ge=60, le=90)
    beats: list[SceneBeat] = Field(min_length=5, max_length=7)


class StoryBreakdownError(Exception):
    pass


def generate_scene_breakdown(story_text: str) -> SceneBreakdown:
    """Call Claude to break a story into dramatic beats."""
    user_prompt = f"""Break the following story into dramatic beats for a short vertical video.

Story text:
---
{story_text}
---"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=STORY_BREAKDOWN_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=0.7,
    )

    raw_response = message.content[0].text
    return _validate_and_parse(raw_response)


def _validate_and_parse(raw_response: str) -> SceneBreakdown:
    """Parse and validate Claude's JSON response."""
    json_str = raw_response.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]
        json_str = json_str.rsplit("```", 1)[0]

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise StoryBreakdownError(f"Claude returned invalid JSON: {e}")

    try:
        breakdown = SceneBreakdown.model_validate(data)
    except Exception as e:
        raise StoryBreakdownError(f"Scene breakdown failed validation: {e}")

    total_duration = sum(beat.duration_sec for beat in breakdown.beats)
    if not (55 <= total_duration <= 95):
        raise StoryBreakdownError(
            f"Total duration {total_duration}s outside acceptable range (55-95s)"
        )

    return breakdown
