# Scooby — Backend Architecture & Operations

**Version:** 0.1 (MVP)
**Date:** 2026-03-25
**Status:** Draft

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Story-to-Scene AI Pipeline](#2-story-to-scene-ai-pipeline)
2.5. [Movie Mode — Veo Video Pipeline (Phase 1.5)](#25-movie-mode--veo-video-pipeline-phase-15)
3. [Image Generation Pipeline](#3-image-generation-pipeline)
4. [TTS / Voiceover Generation](#4-tts--voiceover-generation)
5. [Remotion Video Composition](#5-remotion-video-composition)
6. [Full Pipeline Orchestration](#6-full-pipeline-orchestration)
7. [Asset Management & Cleanup](#7-asset-management--cleanup)
8. [Cost Estimation Per Episode](#8-cost-estimation-per-episode)
9. [Environment Variables & Configuration](#9-environment-variables--configuration)
10. [Local Development Setup](#10-local-development-setup)

---

## 1. Architecture Overview

Scooby is a "Canva for stories" platform that transforms raw story text into finished 60-90 second vertical drama videos (9:16 aspect ratio). The backend is built on Python/FastAPI with a Celery-based asynchronous job system, a Remotion Node.js sidecar for video composition, and three external AI services for content generation.

### High-Level Architecture Diagram

```
                          +---------------------+
                          |   Browser / Client   |
                          |  (React SPA)         |
                          +----------+----------+
                                     |
                          HTTP / WebSocket
                                     |
                          +----------v----------+
                          |    FastAPI App       |
                          |    (Python 3.11+)    |
                          |                      |
                          |  - REST endpoints    |
                          |  - WebSocket server  |
                          |  - Auth middleware    |
                          |  - Request validation|
                          +----+-----+-----+----+
                               |     |     |
              +----------------+     |     +----------------+
              |                      |                      |
     +--------v--------+   +--------v--------+   +---------v--------+
     |   PostgreSQL     |   |     Redis        |   |  S3-Compatible   |
     |                  |   |                  |   |  Storage (R2/S3) |
     |  - Users         |   |  - Celery broker |   |                  |
     |  - Episodes      |   |  - Result backend|   |  - Scene images  |
     |  - Scenes        |   |  - Pub/Sub for   |   |  - VO audio      |
     |  - Jobs          |   |    progress      |   |  - Final videos  |
     |  - Audit logs    |   |  - Cache layer   |   |  - Temp assets   |
     +------------------+   +--------+---------+   +------------------+
                                     |
                            +--------v--------+
                            |  Celery Workers  |
                            |  (Python)        |
                            |                  |
                            |  Task queues:    |
                            |  - ai_pipeline   |
                            |  - image_gen     |
                            |  - tts_gen       |
                            |  - video_render  |
                            |  - cleanup       |
                            +---+---------+----+
                                |         |
               +----------------+         +----------------+
               |                                           |
  +------------v-----------+               +---------------v-----------+
  |   External AI APIs     |               |   Remotion Sidecar        |
  |                        |               |   (Node.js 20+)           |
  |  - Claude (Anthropic)  |               |                           |
  |    Scene breakdown     |               |  - Composition rendering  |
  |                        |               |  - 1080x1920 @ 30fps     |
  |  - Stability AI (SDXL) |               |  - H.264 MP4 output      |
  |    Image generation    |               |  - Ken Burns, crossfades  |
  |                        |               |  - Caption overlays       |
  |  - ElevenLabs          |               |                           |
  |    TTS voiceover       |               +---------------------------+
  +------------------------+
```

### Component Summary

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Server | Python 3.11+ / FastAPI | REST API, WebSocket, request routing |
| Task Queue | Celery 5.x + Redis | Async job orchestration and execution |
| Message Broker | Redis 7.x | Celery broker, pub/sub for progress, caching |
| Database | PostgreSQL 15+ | Persistent data storage |
| Object Storage | S3-compatible (Cloudflare R2 or AWS S3) | Images, audio, video assets |
| Video Renderer | Remotion (Node.js 20+) | Scene composition and final video render |
| AI - Story | Claude API (Anthropic) | Story breakdown into scenes/beats |
| AI - Images | Stability AI (SDXL) | Scene image generation |
| AI - Voice | ElevenLabs | Text-to-speech narration |

### Request Flow (Simplified)

```
1. User submits story text via POST /api/v1/episodes
2. FastAPI validates input, creates Episode record (status: "queued")
3. FastAPI dispatches Celery task chain
4. Celery workers execute pipeline stages sequentially
5. Progress updates pushed to Redis pub/sub
6. FastAPI WebSocket relays progress to client in real time
7. Final video URL stored in Episode record (status: "completed")
8. Client receives completion event and can play/download video
```

---

## 2. Story-to-Scene AI Pipeline

The first stage of the pipeline uses Anthropic's Claude API to break raw story text into a structured sequence of 5-7 dramatic beats suitable for short-form vertical video.

### Claude API Integration

```python
# app/services/ai/story_breakdown.py

import anthropic
from app.core.config import settings
from app.models.scene import SceneBreakdown, SceneBeat

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


async def generate_scene_breakdown(story_text: str, style_hint: str = "") -> SceneBreakdown:
    """
    Send raw story text to Claude and receive a structured scene breakdown.

    Args:
        story_text: The raw story/script submitted by the user.
        style_hint: Optional style guidance (e.g., "noir thriller", "romantic drama").

    Returns:
        SceneBreakdown: Validated Pydantic model of the scene breakdown.

    Raises:
        StoryBreakdownError: If Claude returns invalid JSON or fails validation.
    """
    user_prompt = f"""Break the following story into dramatic beats for a short vertical video.

Story text:
---
{story_text}
---"""

    if style_hint:
        user_prompt += f"\n\nStyle guidance: {style_hint}"

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=STORY_BREAKDOWN_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
    )

    raw_response = message.content[0].text
    return _validate_and_parse(raw_response)
```

### Example Prompt and Response

**User story input:**

> She found the letter tucked inside her late grandmother's recipe book. It was addressed to someone named "My Darling" and described a secret love affair from 1962. The handwriting wasn't her grandmother's. It was her grandfather's — written to someone else entirely.

**Claude structured response:**

```json
{
  "title": "The Letter in the Recipe Book",
  "total_duration_sec": 75,
  "beats": [
    {
      "beat_number": 1,
      "beat_label": "hook",
      "visual_description": "Close-up of weathered, yellowed envelope tucked between pages of a vintage cookbook, warm kitchen light casting golden shadows, a woman's trembling fingers just touching the edge of the paper, shallow depth of field, intimate and mysterious mood",
      "narration_text": "She almost missed it. A letter, hidden for sixty years.",
      "duration_sec": 6
    },
    {
      "beat_number": 2,
      "beat_label": "setup",
      "visual_description": "A woman in her 30s sitting at an old farmhouse kitchen table, grandmother's worn recipe book open before her, afternoon sunlight streaming through lace curtains, nostalgic warm tones, boxes of inherited belongings stacked in background",
      "narration_text": "Claire is sorting through her late grandmother's things when she finds the recipe book. Gram's famous dishes, handwritten with love. But between the pages for apple pie and pot roast, there's an envelope she's never seen before.",
      "duration_sec": 15
    },
    {
      "beat_number": 3,
      "beat_label": "escalation_1",
      "visual_description": "Extreme close-up of elegant cursive handwriting on aged paper, words 'My Darling' visible at top, soft focus on passionate love words below, candlelight warmth, romantic and secretive atmosphere",
      "narration_text": "The letter is addressed to 'My Darling.' The words inside are passionate, desperate, aching. A secret love affair. Summer of 1962. Claire's heart races — her grandmother had a secret life.",
      "duration_sec": 14
    },
    {
      "beat_number": 4,
      "beat_label": "escalation_2",
      "visual_description": "Woman's face in profile, half-lit by window light, expression shifting from curiosity to shock, the letter held up near her face, tears forming in her eyes, dramatic chiaroscuro lighting",
      "narration_text": "But then she looks more carefully at the handwriting. She knows this handwriting. She's seen it on birthday cards her entire childhood. This isn't her grandmother's hand.",
      "duration_sec": 13
    },
    {
      "beat_number": 5,
      "beat_label": "climax",
      "visual_description": "Overhead shot of the letter laid flat on the kitchen table, beside a framed black-and-white photo of grandparents on their wedding day, the woman's hands flat on the table on either side, dramatic shadows, revelation moment",
      "narration_text": "It's her grandfather's. The letter was written by her grandfather — to someone who is not her grandmother. Every Sunday dinner, every anniversary, every 'your grandparents had the perfect marriage' — it was all a lie.",
      "duration_sec": 16
    },
    {
      "beat_number": 6,
      "beat_label": "button",
      "visual_description": "The woman clutching the letter to her chest, standing alone in the kitchen doorway, silhouetted against fading golden light, the recipe book still open on the table behind her, bittersweet and contemplative mood",
      "narration_text": "Claire folds the letter carefully and slides it back between the recipes. Some secrets, she decides, are best left where they were hidden.",
      "duration_sec": 11
    }
  ]
}
```

### Validation and Fallback Handling

```python
# app/services/ai/story_breakdown.py (continued)

import json
from app.core.exceptions import StoryBreakdownError

def _validate_and_parse(raw_response: str) -> SceneBreakdown:
    """
    Parse and validate Claude's JSON response against business rules.
    """
    # Step 1: Extract JSON from response (handle markdown code fences if present)
    json_str = raw_response.strip()
    if json_str.startswith("```"):
        json_str = json_str.split("\n", 1)[1]  # Remove opening fence
        json_str = json_str.rsplit("```", 1)[0]  # Remove closing fence

    # Step 2: Parse JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise StoryBreakdownError(f"Claude returned invalid JSON: {e}")

    # Step 3: Validate structure with Pydantic
    try:
        breakdown = SceneBreakdown.model_validate(data)
    except ValidationError as e:
        raise StoryBreakdownError(f"Scene breakdown failed validation: {e}")

    # Step 4: Business rule validation
    total_duration = sum(beat.duration_sec for beat in breakdown.beats)
    if not (60 <= total_duration <= 90):
        raise StoryBreakdownError(
            f"Total duration {total_duration}s is outside 60-90s range"
        )

    beat_count = len(breakdown.beats)
    if not (5 <= beat_count <= 7):
        raise StoryBreakdownError(
            f"Beat count {beat_count} is outside 5-7 range"
        )

    # Verify beat labels follow the required arc
    required_labels = {"hook", "setup", "climax", "button"}
    present_labels = {beat.beat_label for beat in breakdown.beats}
    missing = required_labels - present_labels
    if missing:
        raise StoryBreakdownError(f"Missing required beat labels: {missing}")

    return breakdown


async def generate_scene_breakdown_with_retry(
    story_text: str,
    style_hint: str = "",
    max_retries: int = 2,
) -> SceneBreakdown:
    """
    Attempt scene breakdown with automatic retries on validation failure.
    On the retry attempt, include the validation error in the prompt so
    Claude can self-correct.
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            if attempt == 0:
                return await generate_scene_breakdown(story_text, style_hint)
            else:
                # Include error feedback for self-correction
                correction_hint = (
                    f"\n\nPREVIOUS ATTEMPT FAILED VALIDATION: {last_error}\n"
                    f"Please fix the issue and return valid JSON."
                )
                return await generate_scene_breakdown(
                    story_text, style_hint + correction_hint
                )
        except StoryBreakdownError as e:
            last_error = str(e)
            if attempt == max_retries:
                raise

    raise StoryBreakdownError("Exhausted all retries for scene breakdown")
```

---

## 2.5 Movie Mode — Veo Video Pipeline (Phase 1.5)

> **Status:** Not yet implemented. This section documents the planned Veo-powered "Movie Mode" pipeline that will ship as a Phase 1.5 enhancement after the MVP launches with Storyboard Mode (static images).

Movie Mode is an alternative generation pipeline that produces AI-generated video clips instead of static images. When a user selects Movie Mode in the wizard, the pipeline diverges after story intake — Claude generates a cinematic script (not just narration + visual description), and Veo generates ~8-second video clips per scene instead of Stability AI images.

### 2.5.1 Pipeline Overview

```
Story Text
    │
    ▼
[Claude] Cinematic Script Breakdown
    │   (camera directions, dialogue, character refs)
    │
    ├──► Character Bible Expansion
    │     (expand character refs → full descriptions)
    │
    ▼
[Veo] Per-Scene Video Clip Generation
    │   (~8 seconds per clip, 1080×1920, 9:16)
    │
    ├──► [ElevenLabs] TTS Voiceover (same as Storyboard Mode)
    │
    ▼
[Remotion] Clip Stitching & Composition
    │   (clips + transitions + VO overlay + captions)
    │
    ▼
Final MP4 (60–90 seconds)
```

### 2.5.2 Character Bible

Before scene generation begins, the user provides character descriptions that are stored per-story and injected into every Veo prompt:

```python
class CharacterBibleEntry(BaseModel):
    name: str                    # e.g., "Maria"
    appearance: str              # Physical description, clothing, distinguishing features
    personality_notes: str       # Emotional defaults, mannerisms (used for Claude script directions)

class CharacterBible(BaseModel):
    characters: list[CharacterBibleEntry]  # Max 4 for MVP
```

The character bible serves two purposes:
1. **Claude prompt enrichment:** Character names in the story are expanded with personality notes to guide dialogue and emotional direction
2. **Veo prompt consistency:** Every Veo prompt includes the full appearance description of characters present in that scene

### 2.5.3 Cinematic Script Generation (Claude)

In Movie Mode, the Claude system prompt changes to request a cinematic script rather than a storyboard:

```python
MOVIE_MODE_SYSTEM_PROMPT = """
You are a cinematic script writer for short-form vertical drama (9:16, 60-90 seconds).

Given a story and character bible, break it into 5-7 scenes. For each scene, provide:

1. **camera_direction**: A concise shot description for an AI video generator.
   Include shot type (close-up, wide, medium), camera movement (dolly, pan, static),
   and key visual action. Example: "Medium shot, slow push-in. Maria sits at a desk,
   opens an envelope, her expression shifts from curiosity to shock."

2. **dialogue**: Any spoken lines by characters, with speaker labels and emotional
   direction in parentheses. Example:
   MARIA (whispering, trembling): "I never thought he'd actually leave."

3. **narration**: Voiceover narration text (same role as Storyboard Mode).

4. **character_refs**: List of character names from the bible who appear in this scene.

5. **beat_label**: One of: Hook, Setup, Escalation, Climax, Button.

Return valid JSON matching the MovieModeScene schema.
"""
```

**Response schema (per scene):**

```python
class MovieModeScene(BaseModel):
    scene_number: int
    beat_label: str              # Hook | Setup | Escalation | Climax | Button
    camera_direction: str        # Shot type, movement, action description
    dialogue: str | None         # Character lines with speaker labels, or null
    narration: str               # Voiceover text
    character_refs: list[str]    # Character names from bible present in scene
    duration_hint: float         # Suggested duration in seconds (6-10)
```

### 2.5.4 Veo API Integration

Each scene's cinematic script is sent to the **Gemini / Veo API** for video clip generation:

```python
async def generate_veo_clip(
    scene: MovieModeScene,
    character_bible: CharacterBible,
    style_preset: str,
    max_retries: int = 2
) -> VeoClipResult:
    """
    Generate an ~8-second video clip for a single scene via Veo.

    Prompt construction:
    1. Style prefix (from preset): e.g., "Cinematic, moody lighting, shallow DOF"
    2. Character descriptions (from bible, filtered to character_refs)
    3. Camera direction (from Claude breakdown)
    4. Scene context (dialogue action, if any)
    """
    # Build character block from bible
    char_descriptions = []
    for ref in scene.character_refs:
        char = character_bible.get(ref)
        if char:
            char_descriptions.append(
                f"{char.name}: {char.appearance}"
            )

    prompt = (
        f"Style: {style_preset}. "
        f"Characters: {'; '.join(char_descriptions)}. "
        f"Scene: {scene.camera_direction}"
    )

    for attempt in range(max_retries + 1):
        try:
            # Call Veo API (via Google Generative AI SDK)
            response = await veo_client.generate_video(
                prompt=prompt,
                aspect_ratio="9:16",
                duration_seconds=8,
                resolution="1080x1920"
            )

            # Download and store clip
            clip_url = await storage.upload(
                response.video_bytes,
                path=f"clips/{scene.scene_number}.mp4"
            )

            return VeoClipResult(
                scene_number=scene.scene_number,
                clip_url=clip_url,
                duration=response.duration
            )

        except ContentFilterError:
            if attempt < max_retries:
                # Soften prompt and retry
                prompt = soften_prompt(prompt)
            else:
                raise VeoGenerationError(
                    f"Scene {scene.scene_number} failed content safety "
                    f"after {max_retries + 1} attempts"
                )
```

**Key integration details:**

| Parameter | Value | Notes |
|-----------|-------|-------|
| API | Google Generative AI (Gemini/Veo 2) | Uses `google-genai` Python SDK |
| Aspect ratio | 9:16 | Vertical format, matches Storyboard Mode |
| Clip duration | ~8 seconds | Per scene; total episode composed from 5-7 clips |
| Resolution | 1080×1920 | Matches final export spec |
| Parallelism | Up to 3 concurrent clips | Rate-limited by API quota |
| Timeout | 120 seconds per clip | Veo generation can be slow |

### 2.5.5 Clip Composition (Remotion)

Movie Mode uses a different Remotion composition that stitches video clips instead of animating static images:

```
Remotion Composition: MovieModeEpisode
├── Sequence: Scene 1
│   ├── <Video src="clip_1.mp4" />
│   ├── <Audio src="vo_1.mp3" /> (mixed over clip, clip audio ducked)
│   └── <Captions text="..." />
├── Transition: Crossfade (15 frames)
├── Sequence: Scene 2
│   ├── <Video src="clip_2.mp4" />
│   ├── <Audio src="vo_2.mp3" />
│   └── <Captions text="..." />
├── ...
└── Sequence: Scene N
    ├── <Video src="clip_N.mp4" />
    ├── <Audio src="vo_N.mp3" />
    └── <Captions text="..." />
```

**Differences from Storyboard Mode composition:**

| Aspect | Storyboard Mode | Movie Mode |
|--------|----------------|------------|
| Visual source | Static images with Ken Burns (pan/zoom) | Video clips (played natively) |
| Transitions | Crossfade between images | Crossfade, cut, or dip-to-black between clips |
| Audio | VO only (no source audio) | VO mixed over clip audio (ducking) |
| Duration per scene | Calculated from VO length | Clip duration (~8s), VO trimmed/padded to match |
| Captions | Same | Same |

### 2.5.6 Cost Comparison

| Pipeline | Image/Clip Cost | 6-Scene Episode | Notes |
|----------|----------------|-----------------|-------|
| Storyboard Mode | ~$0.01–0.02 per image | ~$0.06–0.12 | Stability AI SDXL |
| Movie Mode | ~$0.10–0.50 per clip | ~$0.60–3.00 | Veo pricing TBD |

Movie Mode is **10–25× more expensive** per episode than Storyboard Mode. This is reflected in the product as a premium/paid feature tier.

---

## 3. Image Generation Pipeline

Each scene's `visual_description` from the Claude breakdown is used to generate a vertical image via Stability AI's SDXL model.

### Stability AI Integration

```python
# app/services/ai/image_generation.py

import httpx
import base64
from pathlib import Path
from app.core.config import settings

STABILITY_API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

# Style presets that can be applied on top of the scene visual_description.
# The user picks a preset in the UI; it gets appended to the prompt.
STYLE_PRESETS = {
    "cinematic": "cinematic lighting, dramatic shadows, film grain, anamorphic lens, movie still",
    "noir": "black and white, high contrast, film noir, dramatic shadows, moody, 1940s aesthetic",
    "warm_drama": "warm golden tones, soft lighting, emotional, intimate, shallow depth of field",
    "anime": "anime style, vibrant colors, detailed illustration, studio ghibli inspired",
    "documentary": "photorealistic, natural lighting, raw, unfiltered, documentary photography",
    "default": "photorealistic, cinematic lighting, high detail, dramatic, 8k quality",
}


async def generate_scene_image(
    visual_description: str,
    style_preset: str = "default",
    negative_prompt: str = "",
) -> bytes:
    """
    Generate a single 1080x1920 image from a scene's visual description.

    Args:
        visual_description: The scene's visual_description from Claude breakdown.
        style_preset: Key from STYLE_PRESETS dict.
        negative_prompt: Things to avoid in the image.

    Returns:
        Raw PNG bytes of the generated image.
    """
    style_suffix = STYLE_PRESETS.get(style_preset, STYLE_PRESETS["default"])
    full_prompt = f"{visual_description}, {style_suffix}"

    default_negative = (
        "blurry, low quality, distorted, deformed, text, watermark, logo, "
        "oversaturated, cartoon (unless style is anime), extra limbs, bad anatomy"
    )
    full_negative = f"{default_negative}, {negative_prompt}".strip(", ")

    headers = {
        "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "text_prompts": [
            {"text": full_prompt, "weight": 1.0},
            {"text": full_negative, "weight": -1.0},
        ],
        "cfg_scale": 7,
        "height": 1920,
        "width": 1080,
        "samples": 1,
        "steps": 40,
        "style_preset": "photographic" if style_preset != "anime" else "anime",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            STABILITY_API_URL,
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    image_b64 = data["artifacts"][0]["base64"]
    return base64.b64decode(image_b64)
```

### Parallel Generation via Celery Group

All scene images are generated simultaneously using a Celery group to minimize total pipeline latency.

```python
# app/tasks/image_tasks.py

from celery import shared_task, group
from app.services.ai.image_generation import generate_scene_image
from app.services.storage import upload_asset
from app.models.episode import Episode

@shared_task(
    bind=True,
    queue="image_gen",
    max_retries=2,
    default_retry_delay=10,
    rate_limit="10/m",  # Stability AI rate limit protection
)
def generate_single_image(self, episode_id: str, scene_id: str,
                          visual_description: str, style_preset: str):
    """Generate and upload a single scene image."""
    try:
        image_bytes = generate_scene_image(  # sync wrapper for Celery
            visual_description=visual_description,
            style_preset=style_preset,
        )

        # Upload to S3-compatible storage
        s3_key = f"{episode_id}/scenes/{scene_id}/image.png"
        url = upload_asset(
            key=s3_key,
            data=image_bytes,
            content_type="image/png",
        )

        return {"scene_id": scene_id, "image_url": url, "status": "success"}

    except Exception as exc:
        self.retry(exc=exc)


def generate_all_images(episode_id: str, scenes: list, style_preset: str):
    """
    Dispatch parallel image generation for all scenes in an episode.
    Returns a Celery GroupResult that resolves when all images are done.
    """
    tasks = [
        generate_single_image.s(
            episode_id=episode_id,
            scene_id=scene["scene_id"],
            visual_description=scene["visual_description"],
            style_preset=style_preset,
        )
        for scene in scenes
    ]
    return group(tasks).apply_async()
```

### Image Specifications

| Property | Value |
|----------|-------|
| Resolution | 1080 x 1920 (9:16 vertical) |
| Format | PNG |
| Color space | sRGB |
| Model | Stable Diffusion XL 1.0 |
| Steps | 40 |
| CFG Scale | 7 |
| Typical file size | 2-4 MB per image |

### Error Handling and Retry Logic

- **HTTP 429 (Rate Limit):** Retry after exponential backoff (10s, 30s, 90s). Celery `rate_limit="10/m"` prevents burst overload.
- **HTTP 400 (Content Filter):** Log the rejected prompt, attempt a sanitized version with explicit terms removed. If it fails again, use a generic fallback image.
- **HTTP 500/502/503 (Server Error):** Retry up to 2 times with 10-second delay.
- **Timeout:** 120-second per-request timeout. Retry once on timeout.

### Cost

Stability AI SDXL pricing is approximately $0.03-0.06 per image at 40 steps. For a 6-scene episode, total image generation cost is roughly $0.18-0.36.

---

## 4. TTS / Voiceover Generation

Each scene's `narration_text` is converted to spoken audio using ElevenLabs' text-to-speech API. The audio for each scene is generated independently and later synchronized with scene durations during video composition.

### ElevenLabs API Integration

```python
# app/services/ai/tts_generation.py

import httpx
from app.core.config import settings

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# Curated voice presets for story narration
VOICE_PRESETS = {
    "narrator_male_deep": {
        "voice_id": "pNInz6obpgDQGcFmaJgB",      # "Adam"
        "description": "Deep male narrator, dramatic",
    },
    "narrator_female_warm": {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",      # "Bella"
        "description": "Warm female narrator, emotional",
    },
    "narrator_male_neutral": {
        "voice_id": "ErXwobaYiN019PkySvjV",      # "Antoni"
        "description": "Neutral male narrator, storytelling",
    },
    "narrator_female_dramatic": {
        "voice_id": "MF3mGyEYCl7XYWbV9V6O",      # "Elli"
        "description": "Dramatic female narrator, intense",
    },
}


async def generate_scene_voiceover(
    narration_text: str,
    voice_preset: str = "narrator_female_warm",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.4,
) -> bytes:
    """
    Generate TTS audio for a single scene's narration text.

    Args:
        narration_text: The voiceover script text.
        voice_preset: Key from VOICE_PRESETS.
        stability: Voice consistency (0.0 = more variable, 1.0 = more stable).
        similarity_boost: How closely to match the original voice.
        style: Expressiveness level (0.0 = neutral, 1.0 = very expressive).

    Returns:
        Raw MP3 bytes of the generated audio.
    """
    voice_config = VOICE_PRESETS.get(voice_preset, VOICE_PRESETS["narrator_female_warm"])
    voice_id = voice_config["voice_id"]

    url = f"{ELEVENLABS_API_URL}/{voice_id}"

    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    payload = {
        "text": narration_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": True,
        },
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()

    return response.content  # Raw MP3 bytes
```

### Per-Scene Audio Generation (Celery Task)

```python
# app/tasks/tts_tasks.py

from celery import shared_task, group
from app.services.ai.tts_generation import generate_scene_voiceover
from app.services.storage import upload_asset
from app.services.audio import get_audio_duration, normalize_audio

@shared_task(
    bind=True,
    queue="tts_gen",
    max_retries=2,
    default_retry_delay=5,
)
def generate_single_voiceover(self, episode_id: str, scene_id: str,
                               narration_text: str, voice_preset: str):
    """Generate, normalize, and upload a single scene voiceover."""
    try:
        audio_bytes = generate_scene_voiceover(  # sync wrapper
            narration_text=narration_text,
            voice_preset=voice_preset,
        )

        # Normalize audio levels to -16 LUFS for consistent volume
        normalized_bytes = normalize_audio(audio_bytes, target_lufs=-16.0)

        # Get actual audio duration for synchronization
        duration_sec = get_audio_duration(normalized_bytes)

        # Upload to S3
        s3_key = f"{episode_id}/scenes/{scene_id}/voiceover.mp3"
        url = upload_asset(
            key=s3_key,
            data=normalized_bytes,
            content_type="audio/mpeg",
        )

        return {
            "scene_id": scene_id,
            "audio_url": url,
            "actual_duration_sec": duration_sec,
            "status": "success",
        }

    except Exception as exc:
        self.retry(exc=exc)


def generate_all_voiceovers(episode_id: str, scenes: list, voice_preset: str):
    """Dispatch parallel VO generation for all scenes."""
    tasks = [
        generate_single_voiceover.s(
            episode_id=episode_id,
            scene_id=scene["scene_id"],
            narration_text=scene["narration_text"],
            voice_preset=voice_preset,
        )
        for scene in scenes
    ]
    return group(tasks).apply_async()
```

### Timestamp Synchronization

When Claude specifies `duration_sec` for a beat and ElevenLabs produces audio of a different length, the system must reconcile the two. The reconciliation strategy is:

```python
# app/services/audio.py

def reconcile_scene_timing(target_duration_sec: float,
                           actual_audio_duration_sec: float) -> dict:
    """
    Reconcile the target scene duration with the actual VO audio duration.

    Strategy:
    - If audio is shorter than target: pad with silence at the end.
      The visual holds on the image for the extra time.
    - If audio is longer than target (up to 120%): extend the scene duration
      to match the audio. The visual simply plays longer.
    - If audio is much longer than target (>120%): flag for review. The narration
      text may need shortening.

    Returns:
        Dict with final_duration_sec and any adjustments made.
    """
    tolerance = target_duration_sec * 1.2  # 20% tolerance

    if actual_audio_duration_sec <= target_duration_sec:
        return {
            "final_duration_sec": target_duration_sec,
            "padding_sec": target_duration_sec - actual_audio_duration_sec,
            "adjustment": "padded_silence",
        }
    elif actual_audio_duration_sec <= tolerance:
        return {
            "final_duration_sec": actual_audio_duration_sec,
            "padding_sec": 0,
            "adjustment": "extended_scene",
        }
    else:
        return {
            "final_duration_sec": actual_audio_duration_sec,
            "padding_sec": 0,
            "adjustment": "needs_review",
            "warning": (
                f"Audio ({actual_audio_duration_sec:.1f}s) exceeds target "
                f"({target_duration_sec:.1f}s) by more than 20%"
            ),
        }
```

### Audio Normalization

All voiceover audio is normalized to -16 LUFS (Loudness Units Full Scale) to ensure consistent volume across scenes and against the background music bed. Normalization is performed using `pydub` with `ffmpeg`:

```python
from pydub import AudioSegment
import io

def normalize_audio(audio_bytes: bytes, target_lufs: float = -16.0) -> bytes:
    """Normalize audio to target LUFS for consistent volume."""
    audio = AudioSegment.from_mp3(io.BytesIO(audio_bytes))

    # Simple loudness normalization (approximate LUFS via dBFS)
    current_dbfs = audio.dBFS
    target_dbfs = target_lufs  # Approximate: LUFS ~ dBFS for speech
    change_db = target_dbfs - current_dbfs

    normalized = audio.apply_gain(change_db)

    buffer = io.BytesIO()
    normalized.export(buffer, format="mp3", bitrate="192k")
    return buffer.getvalue()
```

### Cost

ElevenLabs pricing for the multilingual v2 model is approximately $0.01-0.03 per scene depending on text length. For a 6-scene episode, total TTS cost is roughly $0.06-0.18.

---

## 5. Remotion Video Composition

The final video is composed using Remotion, a React-based video creation framework that runs as a Node.js sidecar process. The Python backend generates a composition JSON spec, passes it to Remotion, and Remotion renders the final MP4.

### Composition JSON Structure

The Python backend produces a JSON file that the Remotion composition reads as its input props:

```json
{
  "episodeId": "ep_abc123",
  "title": "The Letter in the Recipe Book",
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "totalDurationFrames": 2250,
  "musicBed": {
    "url": "https://storage.example.com/music/dramatic_piano_01.mp3",
    "volume": 0.12,
    "fadeInFrames": 30,
    "fadeOutFrames": 60
  },
  "scenes": [
    {
      "sceneId": "scene_001",
      "beatLabel": "hook",
      "startFrame": 0,
      "durationFrames": 180,
      "image": {
        "url": "https://storage.example.com/ep_abc123/scenes/scene_001/image.png",
        "animation": {
          "type": "ken_burns",
          "startScale": 1.0,
          "endScale": 1.15,
          "startX": 0,
          "startY": 0,
          "endX": -20,
          "endY": -10
        }
      },
      "voiceover": {
        "url": "https://storage.example.com/ep_abc123/scenes/scene_001/voiceover.mp3",
        "startOffsetFrames": 15,
        "volume": 1.0
      },
      "captions": [
        {
          "text": "She almost missed it.",
          "startFrame": 15,
          "endFrame": 75,
          "style": "dramatic_center"
        },
        {
          "text": "A letter, hidden for sixty years.",
          "startFrame": 80,
          "endFrame": 165,
          "style": "dramatic_center"
        }
      ],
      "transition": {
        "type": "crossfade",
        "durationFrames": 15
      }
    }
  ]
}
```

### Remotion Component Architecture

```
remotion-sidecar/
  src/
    Root.tsx                    # Entry point, registers compositions
    compositions/
      EpisodeVideo.tsx          # Main composition — maps over scenes
    components/
      Scene.tsx                 # Single scene: image + VO + captions
      KenBurnsImage.tsx         # Animated image with pan/zoom
      CaptionOverlay.tsx        # Styled text overlay with animation
      MusicBed.tsx              # Background music with fade in/out
      CrossfadeTransition.tsx   # Transition between scenes
    lib/
      types.ts                  # TypeScript types for composition JSON
      interpolations.ts         # Custom easing functions
```

### Scene-by-Scene Composition

Each scene in the final video combines the following layers (bottom to top):

```
Layer 4 (top):  Caption text overlay with entrance/exit animation
Layer 3:        Voiceover audio
Layer 2:        Background music bed (low volume, continuous)
Layer 1 (base): Scene image with Ken Burns pan/zoom animation
```

### Effects

**Crossfade Transitions:**
- Each scene transition uses a 15-frame (0.5 second) crossfade.
- The outgoing scene fades to 0 opacity while the incoming scene fades from 0 to full opacity.

**Ken Burns Effect on Images:**
- Each static image is slowly panned and zoomed over the scene's duration.
- Scale typically moves from 1.0x to 1.1-1.2x (subtle zoom in).
- Pan direction is randomized per scene to create visual variety.
- Uses `spring()` interpolation for natural, organic movement.

**Caption Text Animations:**
- Captions appear word-by-word or as full phrases with a fade-up animation.
- Positioned at bottom-center of the frame with a semi-transparent dark gradient backdrop.
- Font: bold sans-serif, white text with subtle drop shadow.
- Each caption phrase is timed to match the voiceover using word-level timestamps.

### Render Configuration

| Property | Value |
|----------|-------|
| Resolution | 1080 x 1920 |
| Frame Rate | 30 fps |
| Codec | H.264 |
| Container | MP4 |
| CRF | 18 (high quality) |
| Pixel Format | yuv420p |
| Audio Codec | AAC |
| Audio Bitrate | 192 kbps |
| Typical Output Size | 15-30 MB for 60-90s |

### Remotion CLI Render Command

The Python backend invokes Remotion rendering via a subprocess call to the Remotion CLI:

```python
# app/services/video/renderer.py

import subprocess
import json
import tempfile
from pathlib import Path
from app.core.config import settings

REMOTION_PROJECT_DIR = Path(settings.REMOTION_SIDECAR_PATH)


def render_video(composition_data: dict, output_path: str) -> str:
    """
    Invoke Remotion CLI to render the final video.

    Args:
        composition_data: The full composition JSON spec.
        output_path: Local path for the output MP4 file.

    Returns:
        Path to the rendered MP4 file.
    """
    # Write composition data to a temp JSON file that Remotion will read
    props_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, dir="/tmp"
    )
    json.dump(composition_data, props_file)
    props_file.close()

    total_frames = composition_data["totalDurationFrames"]

    cmd = [
        "npx", "remotion", "render",
        str(REMOTION_PROJECT_DIR / "src" / "index.ts"),
        "EpisodeVideo",
        output_path,
        f"--props={props_file.name}",
        f"--width=1080",
        f"--height=1920",
        f"--fps=30",
        f"--frames=0-{total_frames - 1}",
        "--codec=h264",
        "--crf=18",
        "--pixel-format=yuv420p",
        "--audio-codec=aac",
        "--audio-bitrate=192K",
        "--log=verbose",
        "--timeout=600000",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,  # 10 minute timeout
        cwd=str(REMOTION_PROJECT_DIR),
    )

    if result.returncode != 0:
        raise VideoRenderError(
            f"Remotion render failed (exit code {result.returncode}):\n"
            f"STDOUT: {result.stdout[-2000:]}\n"
            f"STDERR: {result.stderr[-2000:]}"
        )

    return output_path
```

---

## 6. Full Pipeline Orchestration

The complete story-to-video pipeline is orchestrated as a Celery task chain, where each stage's output feeds into the next. Parallel stages (image generation and voiceover generation) are executed simultaneously using Celery groups within a chord.

### Pipeline Architecture

```
                    +---------------------------+
                    | generate_scene_breakdown   |
                    | (Claude API)               |
                    +-------------+-------------+
                                  |
                    +-------------v-------------+
                    |       Celery Chord         |
                    |  (parallel execution)      |
                    |                            |
                    |  +---------------------+   |
                    |  | generate_images     |   |
                    |  | (Stability AI)      |   |
                    |  | [group of N tasks]  |   |
                    |  +---------------------+   |
                    |                            |
                    |  +---------------------+   |
                    |  | generate_voiceovers |   |
                    |  | (ElevenLabs)        |   |
                    |  | [group of N tasks]  |   |
                    |  +---------------------+   |
                    |                            |
                    +-------------+-------------+
                                  |
                    +-------------v-------------+
                    |      compose_video         |
                    |      (Remotion render)      |
                    +-------------+-------------+
                                  |
                    +-------------v-------------+
                    |     finalize_episode        |
                    |  (DB update, cleanup, notify)|
                    +---------------------------+
```

### Celery Task Chain Implementation

```python
# app/tasks/pipeline.py

from celery import chain, chord, group, shared_task
from app.tasks.ai_tasks import generate_scene_breakdown_task
from app.tasks.image_tasks import generate_single_image
from app.tasks.tts_tasks import generate_single_voiceover
from app.tasks.video_tasks import compose_video_task
from app.tasks.cleanup_tasks import finalize_episode_task
from app.services.progress import publish_progress
from app.models.episode import EpisodeStatus
from app.db import get_db_session


@shared_task(bind=True, queue="ai_pipeline")
def run_episode_pipeline(self, episode_id: str, story_text: str,
                          style_preset: str, voice_preset: str):
    """
    Top-level orchestrator that kicks off the full pipeline.
    This task dispatches the chain and returns immediately.
    """
    pipeline = chain(
        # Stage 1: Scene breakdown
        generate_scene_breakdown_task.s(
            episode_id=episode_id,
            story_text=story_text,
            style_preset=style_preset,
        ),

        # Stage 2 & 3: Images + Voiceovers in parallel (chord)
        # The callback fires after both groups complete
        dispatch_parallel_generation.s(
            episode_id=episode_id,
            style_preset=style_preset,
            voice_preset=voice_preset,
        ),

        # Stage 4: Video composition
        compose_video_task.s(episode_id=episode_id),

        # Stage 5: Finalize
        finalize_episode_task.s(episode_id=episode_id),
    )

    pipeline.apply_async()
    publish_progress(episode_id, stage="queued", progress=0)


@shared_task(bind=True, queue="ai_pipeline")
def dispatch_parallel_generation(self, breakdown_result: dict,
                                  episode_id: str, style_preset: str,
                                  voice_preset: str):
    """
    After scene breakdown, dispatch image and voiceover generation
    in parallel using a Celery chord.
    """
    scenes = breakdown_result["beats"]

    # Build parallel task groups
    image_tasks = group([
        generate_single_image.s(
            episode_id=episode_id,
            scene_id=f"scene_{i:03d}",
            visual_description=scene["visual_description"],
            style_preset=style_preset,
        )
        for i, scene in enumerate(scenes)
    ])

    tts_tasks = group([
        generate_single_voiceover.s(
            episode_id=episode_id,
            scene_id=f"scene_{i:03d}",
            narration_text=scene["narration_text"],
            voice_preset=voice_preset,
        )
        for i, scene in enumerate(scenes)
    ])

    # Combine both groups into one chord
    all_parallel = group(image_tasks, tts_tasks)

    # Use a chord: run all parallel tasks, then call merge_results when done
    result = chord(all_parallel)(
        merge_generation_results.s(
            episode_id=episode_id,
            breakdown=breakdown_result,
        )
    )

    publish_progress(episode_id, stage="generating_assets", progress=25)
    return result


@shared_task(bind=True, queue="ai_pipeline")
def merge_generation_results(self, parallel_results: list,
                              episode_id: str, breakdown: dict):
    """
    Merge image and voiceover results back into the scene breakdown
    to build the Remotion composition JSON.
    """
    # parallel_results is a flat list of all image + VO results
    image_results = {}
    audio_results = {}

    for result in parallel_results:
        if "image_url" in result:
            image_results[result["scene_id"]] = result
        elif "audio_url" in result:
            audio_results[result["scene_id"]] = result

    # Build composition data
    composition = build_composition_json(
        breakdown=breakdown,
        image_results=image_results,
        audio_results=audio_results,
        episode_id=episode_id,
    )

    publish_progress(episode_id, stage="composing_video", progress=70)
    return composition
```

### Progress Tracking via Redis Pub/Sub and WebSocket

Real-time progress is communicated to the client through Redis pub/sub channels, relayed by the FastAPI WebSocket endpoint.

```python
# app/services/progress.py

import json
import redis
from app.core.config import settings

redis_client = redis.Redis.from_url(settings.REDIS_URL)

PROGRESS_STAGES = {
    "queued":              {"step": 0, "label": "Queued"},
    "analyzing_story":     {"step": 1, "label": "Analyzing your story..."},
    "generating_assets":   {"step": 2, "label": "Creating images & voiceover..."},
    "composing_video":     {"step": 3, "label": "Composing your video..."},
    "rendering":           {"step": 4, "label": "Rendering final video..."},
    "finalizing":          {"step": 5, "label": "Finalizing..."},
    "completed":           {"step": 6, "label": "Done!"},
    "failed":              {"step": -1, "label": "Something went wrong"},
}


def publish_progress(episode_id: str, stage: str, progress: int,
                     detail: str = ""):
    """Publish a progress update to the Redis channel for this episode."""
    stage_info = PROGRESS_STAGES.get(stage, {"step": 0, "label": stage})

    message = {
        "episode_id": episode_id,
        "stage": stage,
        "step": stage_info["step"],
        "label": stage_info["label"],
        "progress_pct": progress,
        "detail": detail,
    }

    channel = f"progress:{episode_id}"
    redis_client.publish(channel, json.dumps(message))
```

```python
# app/api/ws/progress.py

from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import redis.asyncio as aioredis
from app.core.config import settings


async def progress_websocket(websocket: WebSocket, episode_id: str):
    """
    WebSocket endpoint that subscribes to Redis pub/sub and relays
    progress updates to the connected client.
    """
    await websocket.accept()

    r = aioredis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"progress:{episode_id}")

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"].decode())
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"progress:{episode_id}")
        await r.close()
```

### Error Handling at Each Stage

| Stage | Error Type | Handling |
|-------|-----------|----------|
| Scene Breakdown | Invalid JSON from Claude | Retry with error feedback (up to 2 retries) |
| Scene Breakdown | Claude API timeout/500 | Retry with exponential backoff (10s, 30s) |
| Image Generation | Content filter rejection | Sanitize prompt and retry; fall back to generic image |
| Image Generation | Rate limit (429) | Celery rate limiting + exponential backoff |
| Image Generation | API error (500/502/503) | Retry up to 2 times |
| Voiceover Generation | API error | Retry up to 2 times with 5s delay |
| Voiceover Generation | Audio too long/short | Reconcile timing (see Section 4) |
| Video Composition | Remotion render failure | Log full stderr, mark episode as failed, notify user |
| Video Composition | Render timeout (>10min) | Kill process, mark as failed |
| Any Stage | Unhandled exception | Catch at chain level, set episode status to "failed", publish error progress |

### Retry Policies

```python
# app/core/celery_config.py (relevant excerpt)

CELERY_TASK_ANNOTATIONS = {
    "app.tasks.ai_tasks.generate_scene_breakdown_task": {
        "max_retries": 2,
        "default_retry_delay": 15,
        "rate_limit": "5/m",
    },
    "app.tasks.image_tasks.generate_single_image": {
        "max_retries": 2,
        "default_retry_delay": 10,
        "rate_limit": "10/m",
    },
    "app.tasks.tts_tasks.generate_single_voiceover": {
        "max_retries": 2,
        "default_retry_delay": 5,
        "rate_limit": "20/m",
    },
    "app.tasks.video_tasks.compose_video_task": {
        "max_retries": 1,
        "default_retry_delay": 30,
        "time_limit": 660,      # Hard kill after 11 minutes
        "soft_time_limit": 600,  # Graceful shutdown after 10 minutes
    },
}
```

---

## 7. Asset Management & Cleanup

### S3 Bucket Structure

All assets are stored in an S3-compatible bucket (Cloudflare R2 or AWS S3) with the following directory structure:

```
scooby-assets/
  {user_id}/
    {episode_id}/
      metadata.json                          # Episode metadata + composition JSON
      scenes/
        scene_000/
          image.png                          # Generated scene image (1080x1920)
          voiceover.mp3                      # Generated voiceover audio
        scene_001/
          image.png
          voiceover.mp3
        ...
      output/
        final.mp4                            # Final rendered video
        thumbnail.jpg                        # Auto-generated thumbnail (720x1280)
      temp/
        composition.json                     # Remotion input (temporary)
        render_log.txt                       # Render log (temporary)
  shared/
    music/
      dramatic_piano_01.mp3                  # Music bed library
      tension_strings_01.mp3
      emotional_ambient_01.mp3
      ...
    fonts/
      inter-bold.woff2                       # Caption fonts
      ...
```

### Temporary vs Permanent Assets

| Asset Type | Location | Lifecycle | Retention |
|-----------|----------|-----------|-----------|
| Scene images | `scenes/{id}/image.png` | Permanent | Retained while episode exists |
| Voiceover audio | `scenes/{id}/voiceover.mp3` | Permanent | Retained while episode exists |
| Final video | `output/final.mp4` | Permanent | Retained while episode exists |
| Thumbnail | `output/thumbnail.jpg` | Permanent | Retained while episode exists |
| Composition JSON | `temp/composition.json` | Temporary | Deleted after 24h |
| Render logs | `temp/render_log.txt` | Temporary | Deleted after 24h |
| Metadata | `metadata.json` | Permanent | Retained while episode exists |

### Cleanup Policy

```python
# app/tasks/cleanup_tasks.py

from celery import shared_task
from celery.schedules import crontab
from datetime import datetime, timedelta
from app.services.storage import list_objects, delete_objects
from app.core.config import settings

# Scheduled via Celery Beat
# Runs daily at 3:00 AM UTC
CELERYBEAT_SCHEDULE = {
    "cleanup-temp-assets": {
        "task": "app.tasks.cleanup_tasks.cleanup_temp_assets",
        "schedule": crontab(hour=3, minute=0),
    },
}


@shared_task(queue="cleanup")
def cleanup_temp_assets():
    """
    Delete temporary assets older than 24 hours.
    Scans all episode temp/ directories and removes stale files.
    """
    cutoff = datetime.utcnow() - timedelta(hours=24)

    # List all objects under temp/ prefixes
    temp_objects = list_objects(prefix="", suffix="/temp/")

    to_delete = [
        obj["key"]
        for obj in temp_objects
        if obj["last_modified"] < cutoff
    ]

    if to_delete:
        delete_objects(to_delete)

    return {"deleted_count": len(to_delete)}


@shared_task(queue="cleanup")
def cleanup_deleted_episode_assets(user_id: str, episode_id: str):
    """
    Delete all assets for a deleted episode.
    Called when a user deletes an episode via the API.
    """
    prefix = f"{user_id}/{episode_id}/"
    objects = list_objects(prefix=prefix)
    keys = [obj["key"] for obj in objects]

    if keys:
        delete_objects(keys)

    return {"deleted_count": len(keys)}
```

### Storage Cost Estimation

| Asset Type | Size Per Episode | Monthly Cost (R2, per 1000 episodes) |
|-----------|-----------------|--------------------------------------|
| Scene images (6x) | ~18 MB | ~$0.27 |
| Voiceover audio (6x) | ~3 MB | ~$0.045 |
| Final video | ~20 MB | ~$0.30 |
| Thumbnail | ~0.1 MB | ~$0.0015 |
| Temp files | ~0.5 MB (deleted) | ~$0 |
| **Total per episode** | **~41.6 MB** | |
| **Total per 1000 episodes** | **~40.6 GB** | **~$0.61** |

*Based on Cloudflare R2 pricing: $0.015/GB/month for storage, free egress.*

---

## 8. Cost Estimation Per Episode

The following table breaks down the estimated cost for a typical episode with 6 scenes and approximately 90 seconds of total duration.

### Per-Episode Cost Breakdown

| Service | Operation | Unit Cost | Quantity | Low Estimate | High Estimate |
|---------|-----------|-----------|----------|-------------|---------------|
| **Claude (Anthropic)** | Scene breakdown | ~$0.003/1K input + $0.015/1K output tokens | 1 call (~800 input, ~600 output tokens) | $0.01 | $0.03 |
| **Stability AI** | Image generation (SDXL) | $0.03-0.06/image | 6 images | $0.18 | $0.36 |
| **ElevenLabs** | Text-to-speech | ~$0.01-0.03/scene (~30-50 words each) | 6 scenes | $0.06 | $0.18 |
| **Compute** | Remotion render (CPU time) | ~$0.05-0.10 per render | 1 render | $0.05 | $0.10 |
| **Storage** | S3/R2 (monthly, amortized) | ~$0.015/GB/month | ~42 MB | $0.001 | $0.001 |
| | | | | | |
| **TOTAL** | | | | **$0.30** | **$0.67** |

### Cost Scaling Notes

- **At 100 episodes/day:** ~$30-67/day, ~$900-2,010/month
- **At 1,000 episodes/day:** ~$300-670/day, ~$9,000-20,100/month
- **Primary cost driver:** Image generation (Stability AI) accounts for ~55-60% of total cost
- **Optimization opportunities:**
  - Cache common style preset images for reuse
  - Use lower step count (30 instead of 40) for ~20% image cost reduction with minimal quality loss
  - Batch ElevenLabs requests where API supports it
  - Use spot/preemptible instances for Remotion rendering

---

## 9. Environment Variables & Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@localhost:5432/scooby` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | `sk-ant-api03-...` |
| `STABILITY_API_KEY` | Stability AI API key | `sk-...` |
| `ELEVENLABS_API_KEY` | ElevenLabs API key | `xi-...` |
| `S3_ENDPOINT_URL` | S3-compatible endpoint | `https://your-account.r2.cloudflarestorage.com` |
| `S3_ACCESS_KEY_ID` | S3 access key | `AKIA...` |
| `S3_SECRET_ACCESS_KEY` | S3 secret key | `wJal...` |
| `S3_BUCKET_NAME` | Asset storage bucket | `scooby-assets` |
| `S3_PUBLIC_URL` | Public CDN URL for assets | `https://assets.scooby.app` |
| `REMOTION_SIDECAR_PATH` | Path to Remotion project directory | `/app/remotion-sidecar` |
| `SECRET_KEY` | Application secret for JWT signing | `your-secret-key-change-in-production` |
| `ALLOWED_ORIGINS` | CORS allowed origins (comma-separated) | `http://localhost:3000,https://scooby.app` |
| `ENV` | Environment name | `development` / `staging` / `production` |
| `LOG_LEVEL` | Logging level | `DEBUG` / `INFO` / `WARNING` |
| `CELERY_BROKER_URL` | Celery broker (usually same as REDIS_URL) | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://localhost:6379/1` |
| `MAX_EPISODES_PER_USER_DAY` | Rate limit: episodes per user per day | `10` |
| `MAX_STORY_LENGTH_CHARS` | Maximum story input length | `5000` |

### Example `.env.example` File

```bash
# ============================================================
# Scooby Backend — Environment Variables
# ============================================================
# Copy this file to .env and fill in your values.
# NEVER commit the .env file to version control.
# ============================================================

# ---------- Core ----------
ENV=development
SECRET_KEY=change-me-to-a-real-secret-in-production
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
LOG_LEVEL=DEBUG

# ---------- Database ----------
DATABASE_URL=postgresql+asyncpg://scooby:scooby_dev@localhost:5432/scooby

# ---------- Redis / Celery ----------
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# ---------- AI Services ----------
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
STABILITY_API_KEY=sk-your-stability-key-here
ELEVENLABS_API_KEY=xi-your-elevenlabs-key-here

# ---------- S3-Compatible Storage ----------
S3_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=scooby-assets-dev
S3_PUBLIC_URL=https://pub-xxxx.r2.dev

# ---------- Remotion ----------
REMOTION_SIDECAR_PATH=./remotion-sidecar

# ---------- Rate Limits ----------
MAX_EPISODES_PER_USER_DAY=10
MAX_STORY_LENGTH_CHARS=5000
```

---

## 10. Local Development Setup

### Prerequisites

| Requirement | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Backend API and Celery workers |
| Node.js | 20+ (LTS) | Remotion video rendering sidecar |
| PostgreSQL | 15+ | Primary database |
| Redis | 7+ | Celery broker, caching, pub/sub |
| FFmpeg | 6+ | Audio processing (pydub) and Remotion rendering |
| pnpm or npm | Latest | Node.js package management for Remotion |

### Initial Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/scooby.git
cd scooby

# 2. Create and activate Python virtual environment
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# 3. Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt   # Testing, linting, etc.

# 4. Copy environment file and configure
cp .env.example .env
# Edit .env with your API keys and local service URLs

# 5. Set up the database
# Ensure PostgreSQL is running, then:
createdb scooby                      # Create the database
alembic upgrade head                 # Run migrations

# 6. Set up the Remotion sidecar
cd remotion-sidecar
npm install                          # or: pnpm install
cd ..

# 7. Verify Redis is running
redis-cli ping                       # Should return: PONG
```

### Running the Development Server

You need four processes running simultaneously. Use separate terminal windows/tabs or a process manager like `honcho` or `overmind`.

**Terminal 1 — FastAPI Dev Server:**

```bash
cd scooby
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Celery Worker:**

```bash
cd scooby
source .venv/bin/activate
celery -A app.core.celery_app worker \
  --loglevel=info \
  --queues=ai_pipeline,image_gen,tts_gen,video_render,cleanup \
  --concurrency=4
```

**Terminal 3 — Celery Beat (Scheduler):**

```bash
cd scooby
source .venv/bin/activate
celery -A app.core.celery_app beat --loglevel=info
```

**Terminal 4 — Remotion Studio (optional, for visual debugging):**

```bash
cd scooby/remotion-sidecar
npx remotion studio
# Opens browser at http://localhost:3000 with Remotion preview
```

### Using a Procfile (Alternative)

Create a `Procfile` for running all services with a single command via `honcho` or `foreman`:

```procfile
web:     uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
worker:  celery -A app.core.celery_app worker --loglevel=info --queues=ai_pipeline,image_gen,tts_gen,video_render,cleanup --concurrency=4
beat:    celery -A app.core.celery_app beat --loglevel=info
```

Then run:

```bash
pip install honcho
honcho start
```

### Running Tests

```bash
# Run the full test suite
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run a specific test file
pytest tests/test_story_breakdown.py -v

# Run only unit tests (skip integration tests that need real API keys)
pytest -m "not integration"
```

### Common Development Tasks

```bash
# Create a new database migration
alembic revision --autogenerate -m "add episodes table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Open a Python shell with app context
python -c "from app.main import app; import IPython; IPython.start_ipython()"

# Monitor Celery tasks in real-time
celery -A app.core.celery_app events

# Purge all queued tasks (use with caution)
celery -A app.core.celery_app purge

# Check Remotion render locally with test data
cd remotion-sidecar
npx remotion render src/index.ts EpisodeVideo out/test.mp4 \
  --props=test-fixtures/sample-composition.json
```

---

*This document describes the MVP (v0.1) backend architecture for Scooby. As the platform evolves, this document should be updated to reflect changes in the pipeline, new service integrations, and scaling decisions.*
