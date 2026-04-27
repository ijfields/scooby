# Scooby — Database Schemas

> **Version:** 0.1 (MVP)
> **Last updated:** 2026-03-25
> **Database:** PostgreSQL 15+

---

## Entity Relationship Diagram

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│  users   │──1:N──│ stories  │──1:N──│ episodes │
└──────────┘       └──────────┘       └──────────┘
                                           │
                                          1:N
                                           │
                                      ┌──────────┐
                                      │  scenes  │
                                      └──────────┘
                                           │
                                          1:N
                                           │
                                    ┌──────────────┐
                                    │ video_assets  │
                                    └──────────────┘

┌────────────────┐
│ style_presets  │ (referenced by episodes)
└────────────────┘

┌──────────────────┐
│ generation_jobs  │ (linked to episodes)
└──────────────────┘
```

---

## Tables

### 1. `users`

Stores authenticated user profiles. Auth handled externally by Clerk; this table stores the Clerk user ID and app-specific metadata.

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_id        VARCHAR(255) NOT NULL UNIQUE,
    email           VARCHAR(255) NOT NULL UNIQUE,
    display_name    VARCHAR(100),
    avatar_url      TEXT,
    plan            VARCHAR(20) NOT NULL DEFAULT 'free',  -- 'free', 'pro', 'enterprise'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_clerk_id ON users(clerk_id);
CREATE INDEX idx_users_email ON users(email);
```

**Example record:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "clerk_id": "user_2abc123def456",
  "email": "writer@example.com",
  "display_name": "Ingrid",
  "avatar_url": null,
  "plan": "free",
  "created_at": "2026-03-25T10:00:00Z",
  "updated_at": "2026-03-25T10:00:00Z"
}
```

---

### 2. `stories`

The raw story text submitted by a writer. One user can have many stories.

```sql
CREATE TABLE stories (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           VARCHAR(200) NOT NULL,
    raw_text        TEXT NOT NULL,
    word_count      INTEGER NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',  -- 'draft', 'processing', 'ready', 'archived'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_stories_user_id ON stories(user_id);
CREATE INDEX idx_stories_status ON stories(status);
```

**Example record:**
```json
{
  "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "title": "The Last Letter",
  "raw_text": "She sat at the kitchen table, staring at the envelope...",
  "word_count": 542,
  "status": "ready",
  "created_at": "2026-03-25T10:05:00Z",
  "updated_at": "2026-03-25T10:06:30Z"
}
```

---

### 3. `style_presets`

Predefined visual and audio style configurations. Seeded by the platform; users select from these during the wizard.

```sql
CREATE TABLE style_presets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,
    category        VARCHAR(50) NOT NULL,  -- 'visual', 'voice', 'music'
    description     TEXT,
    thumbnail_url   TEXT,
    preview_url     TEXT,                  -- audio preview for voice/music presets
    config          JSONB NOT NULL,        -- style-specific parameters
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_style_presets_category ON style_presets(category);
CREATE INDEX idx_style_presets_active ON style_presets(is_active);
```

**Example records:**
```json
[
  {
    "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
    "name": "Soft Realistic",
    "category": "visual",
    "description": "Warm, soft-focus photorealistic imagery with natural lighting",
    "thumbnail_url": "/presets/soft-realistic-thumb.jpg",
    "config": {
      "model": "stability-ai/sdxl",
      "style_prompt_suffix": "soft focus, warm natural lighting, photorealistic, cinematic depth of field",
      "negative_prompt": "cartoon, anime, harsh lighting, oversaturated",
      "cfg_scale": 7,
      "aspect_ratio": "9:16"
    },
    "is_active": true,
    "sort_order": 1
  },
  {
    "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
    "name": "Warm Female",
    "category": "voice",
    "description": "Warm, empathetic female narrator voice",
    "preview_url": "/presets/warm-female-preview.mp3",
    "config": {
      "provider": "elevenlabs",
      "voice_id": "EXAVITQu4vr4xnSDxMaL",
      "stability": 0.5,
      "similarity_boost": 0.75,
      "style": 0.3
    },
    "is_active": true,
    "sort_order": 1
  },
  {
    "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
    "name": "Tense",
    "category": "music",
    "description": "Tension-building ambient underscore",
    "preview_url": "/presets/tense-preview.mp3",
    "config": {
      "track_url": "/music/tense-ambient-loop.mp3",
      "volume": 0.15,
      "fade_in_seconds": 2,
      "fade_out_seconds": 3
    },
    "is_active": true,
    "sort_order": 1
  }
]
```

---

### 4. `episodes`

A single vertical drama episode derived from a story. MVP: one episode per story.

```sql
CREATE TABLE episodes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id            UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    title               VARCHAR(200),
    target_duration_sec INTEGER NOT NULL DEFAULT 90,          -- 60 or 90
    visual_style_id     UUID REFERENCES style_presets(id),
    voice_style_id      UUID REFERENCES style_presets(id),
    music_style_id      UUID REFERENCES style_presets(id),
    status              VARCHAR(20) NOT NULL DEFAULT 'draft', -- 'draft', 'scenes_generated', 'generating', 'preview_ready', 'exported'
    composition_json    JSONB,                                -- ffmpeg renderer composition spec (built by composer.build_composition_json)
    final_video_url     TEXT,                                 -- worker /tmp path; kept for log correlation only — not servable
    final_video_data    BYTEA,                                -- final rendered MP4 bytes (deferred load; survives worker restarts)
    final_video_size_bytes BIGINT,
    final_video_mime_type VARCHAR(100),
    final_video_duration_sec NUMERIC(6,2),
    script_pdf_url      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_episodes_story_id ON episodes(story_id);
CREATE INDEX idx_episodes_status ON episodes(status);
```

**Example record:**
```json
{
  "id": "f6a7b8c9-d0e1-2345-fabc-456789012345",
  "story_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "title": "The Last Letter — Episode 1",
  "target_duration_sec": 90,
  "visual_style_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "voice_style_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "music_style_id": "e5f6a7b8-c9d0-1234-efab-345678901234",
  "status": "preview_ready",
  "composition_json": { "...remotion config..." },
  "final_video_url": "https://storage.example.com/episodes/f6a7b8c9.../final.mp4",
  "final_video_duration_sec": 87.5,
  "script_pdf_url": null,
  "created_at": "2026-03-25T10:10:00Z",
  "updated_at": "2026-03-25T10:25:00Z"
}
```

---

### 5. `scenes`

Individual beats/scenes within an episode. Ordered by `scene_order`.

```sql
CREATE TABLE scenes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id          UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    scene_order         INTEGER NOT NULL,
    beat_label          VARCHAR(50) NOT NULL,    -- 'hook', 'setup', 'escalation_1', 'escalation_2', 'escalation_3', 'climax', 'button'
    visual_description  TEXT NOT NULL,
    narration_text      TEXT,
    dialogue_text       TEXT,
    duration_sec        NUMERIC(5,2),            -- target duration for this scene
    image_prompt        TEXT,                     -- generated prompt for image AI
    start_frame         INTEGER,
    end_frame           INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(episode_id, scene_order)
);

CREATE INDEX idx_scenes_episode_id ON scenes(episode_id);
CREATE INDEX idx_scenes_order ON scenes(episode_id, scene_order);
```

**Example record:**
```json
{
  "id": "a7b8c9d0-e1f2-3456-abcd-567890123456",
  "episode_id": "f6a7b8c9-d0e1-2345-fabc-456789012345",
  "scene_order": 1,
  "beat_label": "hook",
  "visual_description": "Tight close-up of a woman's trembling hands holding a sealed envelope. Kitchen table, morning light.",
  "narration_text": "She had waited three years for this letter.",
  "dialogue_text": null,
  "duration_sec": 5.0,
  "image_prompt": "cinematic close-up, woman's trembling hands holding sealed envelope, kitchen table, warm morning light, soft focus, 9:16 vertical, photorealistic",
  "start_frame": 0,
  "end_frame": 150,
  "created_at": "2026-03-25T10:12:00Z",
  "updated_at": "2026-03-25T10:15:00Z"
}
```

---

### 6. `video_assets`

Generated media assets (images, audio clips) linked to individual scenes.

```sql
CREATE TABLE video_assets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scene_id        UUID NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    asset_type      VARCHAR(20) NOT NULL,    -- 'image', 'voiceover', 'music', 'caption_srt'
    file_url        TEXT NOT NULL,            -- S3 URL
    file_size_bytes BIGINT,
    mime_type       VARCHAR(100),
    metadata        JSONB,                   -- provider response, generation params, etc.
    version         INTEGER NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,  -- only latest version is active
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_video_assets_scene_id ON video_assets(scene_id);
CREATE INDEX idx_video_assets_type ON video_assets(asset_type);
CREATE INDEX idx_video_assets_active ON video_assets(scene_id, is_active);
```

**Example record:**
```json
{
  "id": "b8c9d0e1-f2a3-4567-bcde-678901234567",
  "scene_id": "a7b8c9d0-e1f2-3456-abcd-567890123456",
  "asset_type": "image",
  "file_url": "https://storage.example.com/assets/b8c9d0e1.../scene1.png",
  "file_size_bytes": 2048576,
  "mime_type": "image/png",
  "metadata": {
    "provider": "stability-ai",
    "model": "sdxl-1.0",
    "prompt": "cinematic close-up, woman's trembling hands...",
    "seed": 42,
    "generation_time_ms": 3200
  },
  "version": 1,
  "is_active": true,
  "created_at": "2026-03-25T10:13:00Z"
}
```

---

### 7. `generation_jobs`

Tracks async generation pipeline jobs (Celery tasks).

```sql
CREATE TABLE generation_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id      UUID NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    job_type        VARCHAR(30) NOT NULL,     -- 'scene_breakdown', 'image_gen', 'voiceover_gen', 'video_compose', 'full_pipeline'
    celery_task_id  VARCHAR(255),
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed', 'cancelled'
    progress        NUMERIC(5,2) DEFAULT 0,   -- 0.00 to 100.00
    stage           VARCHAR(50),              -- current pipeline stage description
    error_message   TEXT,
    metadata        JSONB,                    -- input params, timing, cost tracking
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_gen_jobs_episode_id ON generation_jobs(episode_id);
CREATE INDEX idx_gen_jobs_status ON generation_jobs(status);
CREATE INDEX idx_gen_jobs_celery ON generation_jobs(celery_task_id);
```

**Example record:**
```json
{
  "id": "c9d0e1f2-a3b4-5678-cdef-789012345678",
  "episode_id": "f6a7b8c9-d0e1-2345-fabc-456789012345",
  "job_type": "full_pipeline",
  "celery_task_id": "celery-task-abc123",
  "status": "running",
  "progress": 45.00,
  "stage": "Generating images (3/6 scenes)",
  "error_message": null,
  "metadata": {
    "total_scenes": 6,
    "images_completed": 3,
    "estimated_cost_usd": 0.42
  },
  "started_at": "2026-03-25T10:15:00Z",
  "completed_at": null,
  "created_at": "2026-03-25T10:15:00Z"
}
```

---

## Seed Data: Style Presets

### Visual Styles

| Name | Description | Key Config |
|------|-------------|------------|
| Soft Realistic | Warm, soft-focus photorealistic | `cfg_scale: 7`, natural lighting prompt |
| Moody Graphic Novel | High contrast, ink-style shadows | `cfg_scale: 8`, graphic novel prompt |
| Watercolor | Soft, painterly, pastel tones | `cfg_scale: 6`, watercolor texture prompt |
| Cinematic Dark | Deep shadows, dramatic color grading | `cfg_scale: 9`, noir lighting prompt |

### Voice Presets

| Name | Provider | Description |
|------|----------|-------------|
| Warm Female | ElevenLabs | Empathetic, mid-range narrator |
| Calm Male | ElevenLabs | Steady, composed male narrator |
| Neutral Storyteller | ElevenLabs | Gender-neutral, clear delivery |

### Music Moods

| Name | Description |
|------|-------------|
| Tense | Tension-building ambient underscore |
| Hopeful | Light, uplifting piano/strings |
| Melancholy | Slow, minor-key emotional bed |
| None | No background music |

---

## Migration Notes

- Use UUID v4 for all primary keys (PostgreSQL `gen_random_uuid()`)
- All timestamps are `TIMESTAMPTZ` (UTC)
- `updated_at` should be maintained via application logic or a trigger
- JSONB columns (`config`, `metadata`, `composition_json`) allow flexible schema evolution
- Foreign key cascades: deleting a user cascades to stories → episodes → scenes → assets
- `video_assets.version` + `is_active` pattern supports regeneration without losing history
