# Scooby — Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). Tags: `[ADDED]`, `[CHANGED]`, `[FIXED]`, `[REMOVED]`.

---

## [0.4.0] — 2026-03-29

### [ADDED]
- Interactive scene-by-scene preview page with AI images, voiceover playback, auto-advance, transport controls, and scene sidebar with thumbnails
- `GET /episodes/{id}/scenes-with-assets` — JSON endpoint returning scenes with their generated asset URLs
- `GET /episodes/by-story/{story_id}` — list all episodes for a given story
- Story detail page now shows existing episodes with links to preview, scenes, and generation progress
- Preview button in scene editor header

### [CHANGED]
- Generate page completion message updated ("Your scenes are ready" instead of "Preview Video")
- Landing page demo section replaced with preview experience mockup
- Story detail CTA section redesigned with breakdown explanation
- Stories list empty state improved with icon and descriptive text
- Project plan updated to v0.4 with current sprint (lexicon, branding, shareable previews)

### [FIXED]
- Unused `stageProgress` variable in generate page

---

## [0.3.0] — 2026-03-28

### [ADDED]
- Frontend Railway deployment with Dockerfile multi-stage build and standalone output
- Celery worker Railway service (`Dockerfile.worker`) for async AI pipeline tasks
- Root endpoint (`/`) on backend returning service status JSON
- Voice ID validation with free-tier fallback in TTS generator
- Comprehensive deployment guide (`DEPLOY.md`) with troubleshooting

### [FIXED]
- CORS: Added production frontend URL to `ALLOWED_ORIGINS`
- JWT auth: Changed `pyjwt` to `pyjwt[crypto]` for RSA algorithm support
- UUID serialization: Changed `UserResponse.id` from `str` to `uuid.UUID`
- Trailing slash redirects: Collection routes use `""` instead of `"/"` to prevent 307 → mixed content
- Celery task discovery: Added `include=["app.tasks.ai", "app.tasks.pipeline"]` to celery config
- Celery task routing: Mapped pipeline tasks to correct queues, added default `celery` queue to worker
- ElevenLabs TTS model: Upgraded from deprecated `eleven_monolingual_v1` to `eleven_multilingual_v2`
- ElevenLabs voice fallback: Invalid voice IDs now fall back to George (Warm Storyteller)
- Duplicate video assets: Queries use `ORDER BY created_at DESC LIMIT 1` for retry resilience
- Backend Dockerfile: Fixed relative paths for `/backend` root directory context
- Backend start command: Wrapped in `sh -c` for `${PORT}` variable expansion
- Frontend Dockerfile: Fixed paths for `/frontend` root directory context

### [CHANGED]
- Backend builder switched from nixpacks to Dockerfile in `railway.toml`
- Removed root-level `railway.toml` to prevent service config conflicts in monorepo

---

## [0.2.0] — 2026-03-26

### [ADDED]
- Landing page with hero, how-it-works strip, feature cards, demo placeholder, footer
- SEO meta tags (Open Graph, Twitter cards)
- Responsive mobile-first layout
- Sticky navigation with backdrop blur
- Session summary: `docs/sessions/session-002-landing-page.md`

---

## [0.1.1] — 2026-03-26

### [ADDED]
- Phase 1.5 "Veo Movie Mode" section in `Enhancements.md` — generation mode toggle, character bible, cinematic script generation, Veo clip pipeline, clip composition, cost tier
- Section 2.5 in `Backend.md` — full technical spec for Movie Mode pipeline (Claude cinematic script prompt, Veo API integration, character bible schema, clip composition via Remotion)
- Phase 1.5 preview note in `PRD.md` Future Vision section
- Moved "Character consistency" from Beyond Phase 3 to Phase 1.5 in `Enhancements.md` (now addressed by character bible)

---

## [0.1.0] — 2026-03-25

### [ADDED]
- Genesis document (`genesis.md`) capturing platform concept evolution from manual Veo+CapCut workflow to automated platform
- Product Requirements Document (`PRD.md`) defining MVP scope, user flow, feature specs, and tech stack
- Database Schemas (`Schemas.md`) with 7 tables: users, stories, style_presets, episodes, scenes, video_assets, generation_jobs
- API Documentation (`API_Documentation.md`) with full endpoint specs, request/response examples
- Backend Architecture (`Backend.md`) covering AI pipelines, Celery orchestration, Remotion composition, cost estimates
- Project Plan (`Project_plan.md`) with Phase 1 action items across 10 workstreams
- Task Manager / Memory Bank (`Memory.md`) tracking project state and decisions
- Enhancements document (`Enhancements.md`) cataloging Phase 2+ features and ideas
- Marketing Plan (`Marketing_Plan.md`) with pre-launch, launch, and growth strategies
