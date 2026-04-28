# Scooby — Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). Tags: `[ADDED]`, `[CHANGED]`, `[FIXED]`, `[REMOVED]`.

---

## [0.6.3] — 2026-04-27

### [FIXED]

**Captions truncated to a single overflowing line.** `_burn_captions` in the ffmpeg renderer joined wrapped lines with `'\n'` and fed the result into a single `drawtext text=` argument. ffmpeg's drawtext interpretation of `\n` as a real line break depends on expansion mode + font shaping; in production on the Linux worker it consumed the backslash and rendered the literal `n` inline, producing single-line captions that overflowed the 1080-wide frame. Now emits one `drawtext` filter per wrapped line with manual y-offsets so the block is vertically centered around y=75% — guaranteed multi-line behavior independent of font/expansion quirks. Tightened MAX_CHARS_PER_LINE from 35 → 32 (better fit at fontsize=42) and bumped LINE_SPACING from 8 → 12. Verified visually on Joyce's hook scene (`ab8bf1d4`): "Today I chose to just be." renders cleanly as a single centered line; longer narrations wrap properly.

### [ADDED]

**TopView Seedance text-to-video eval with character bible.** `scripts/eval_topview_joyce_heart.py` runs Joyce's "Heart for Fun" episode (6 scenes) through TopView's Seedance 1.5 Pro t2v API with a hand-curated character bible prepended to every scene's `visual_description`. Output is a side-by-side comparison set the writer can review for character consistency before we commit to wiring TopView as a production animation provider. Reference implementation for the broader character-bible pattern noted in `docs/Testing_Checklist.md`.

**Polishing matrix in [docs/Testing_Checklist.md](Testing_Checklist.md)** — visual style × image provider grid, animation provider comparison, voice-preset listing, caption render cases, character-consistency strategy. First documented finding: the Watercolor visual preset on Stability AI produces inconsistent character renders + duplicate-object hallucinations (verified on Joyce's "Heart for Fun" — two red balls in the same frame). Test the same preset on Nanobanana 2 before retiring it.

---

## [0.6.2] — 2026-04-27

### [ADDED]

**Final-video persistence in Postgres + in-app player.** Rendered MP4s now live in `episodes.final_video_data` (LargeBinary, deferred), with `final_video_size_bytes` and `final_video_mime_type` exposed on `EpisodeResponse`. The compositor task reads the rendered file after writing and stores its bytes alongside; the file path stays on `final_video_url` for log correlation only. Migration `f7g2h8i9k0l1`.

`GET /api/v1/episodes/{id}/download/video` rewritten — used to return JSON with the worker's `/tmp` path (which the browser couldn't load), now streams the bytes from Postgres with proper `Content-Type` / `Content-Length` / `Accept-Ranges` headers. New `?inline=1` query param for in-browser playback (Content-Disposition: inline) vs the default attachment download.

The episode preview page now renders a `<video>` player above the slideshow when a final video is available — fetched via the auth-aware blob-URL pattern (same as the existing script download). New "Download MP4" button next to "Download Script". Slideshow remains as the secondary preview.

`scripts/backfill_episode_videos.py` — one-shot recovery for the 2 production episodes (`00adb67f`, `3d7dae6b`) whose MP4s were rendered before the blob columns existed and would have vanished on the next worker `/tmp` wipe.

### [FIXED]

**Worker `/tmp` data loss on redeploy.** Before this release, `final_video_url` pointed to `/tmp/scooby/{id}/final.mp4` on the worker container. That path is wiped on every worker redeploy (env-var changes, code pushes, scaling, etc.), so any rendered episode would silently lose its video and the download endpoint would 404 on next request. Fixed by storing the bytes in Postgres directly.

---

## [0.6.1] — 2026-04-26

### [FIXED]

**Stalled episodes stuck at `status='generating'`.** When `compose_and_render_task` raised, the orchestrator caught the exception (intentional — render failure is non-fatal, slideshow preview still works) but never updated `episode.status` away from `'generating'`. The episode was effectively done (job marked completed, images all there) but the UI polled forever waiting for the status to change. Now if render fails, the orchestrator refreshes the episode and explicitly sets `status='preview_ready'` so the UI advances. Diagnosed via the 2 production episodes (`00adb67f`, `3d7dae6b`) that ran in early April before the Remotion → ffmpeg switch — Remotion render failed every time, episode stayed stuck.

---

## [0.6.0] — 2026-04-26

### [CHANGED]

**Video compositor: Remotion → ffmpeg.** The never-shipped Remotion Node.js sidecar is gone. `backend/app/services/video/renderer.py` now composes the final 9:16 MP4 directly via `ffmpeg` subprocess calls — Ken Burns zoompan on static images, scale+pad+tpad on animation clips, xfade crossfades (≤4 scenes) or concat demuxer (5+), `adelay`-mixed voiceovers, `drawtext` caption burn. `Dockerfile.worker` and `worker/Dockerfile` install `ffmpeg` + `fonts-liberation`. `FFMPEG_PATH` and `FFPROBE_PATH` config settings added (default to system PATH). `REMOTION_SIDECAR_PATH` retained as deprecated, unused. `compose_and_render_task` no longer skips on render failure — failures now surface in logs as errors. Verified end-to-end on production data 2026-04-25 (silent video; full render with VO not yet exercised).

### [ADDED]

**Clerk Backend API integration for user profiles.** Standard Clerk JWTs don't include email/name/avatar by default, so every new user fell through to a synthetic `user_<clerk_id>@clerk.user` email. Backend now calls `GET https://api.clerk.com/v1/users/{user_id}` on first auth (in `get_current_user`) and populates `email`, `display_name`, `avatar_url` from the real profile. JWT-claim and synthetic-email fallbacks remain as defense-in-depth. Requires new `CLERK_SECRET_KEY` env var on the backend service.

`scripts/backfill_user_emails.py` — idempotent one-shot migration tool, dry-run by default, skips users whose email already looks real. Used to update the 2 existing production users (Ingrid Fields, Joyce Harris) with their real Google emails on 2026-04-26.

`scripts/test_ffmpeg_renderer.py` — synthetic-asset smoke test for the compositor. Exercises Ken Burns, animation-clip path, xfade crossfade, concat demuxer, audio mixing, and caption burn — no DB or API keys needed.

### [FIXED]

**Caption render on Windows.** `_get_font_path()` over-escaped the `:` in Windows paths (`C\\:/Windows/...`) which broke ffmpeg's filter parser. Now uses single-backslash escape (`\:`). Linux paths unaffected (no colon to escape) so production was never broken; only local dev rendering with captions failed.

**`nanobanana2.py` BytesIO roundtrip removed** in favor of the SDK's direct `image.image_bytes` accessor.

### Infrastructure

- 4 stale empty Postgres services and 2 stale Redis services deleted from Railway, plus 4 orphaned `postgres-volume-*` volumes. Active services: backend, worker, scooby Frontend, Postgres, Redis-7bIt.
- Backend service env: `CLERK_SECRET_KEY` set.
- 2 production episodes (`00adb67f`, `3d7dae6b`) identified as stalled mid-pipeline at the voiceover step (6 images, 0 voiceovers, status `generating`). Pre-existed this release; cause not yet diagnosed.

---

## [0.5.1] — 2026-04-18

### [ADDED]

**TopView AI — Phase 0 evaluation:**
- Evaluation scripts: `scripts/test_topview_image2video.py` and `scripts/test_topview_text2video.py` for running TopView's Image-to-Video V2 and Text-to-Video endpoints against Scooby's 9:16 vertical drama use case
- Shared CSV logging helper `scripts/_topview_results.py` — auto-appends every run (ok / failed / error) to `test_generations/topview_results.csv` with model, credits, gen time, dims, output path
- `TOPVIEW_API_KEY` + `TOPVIEW_UID` added to `.env.example` (Pro plan required)
- Partner review page generator: `scripts/build_topview_review_page.py` renders a single-file `test_generations/index.html` in Scooby's brand styling, grouping clips by i2v/t2v with plain-language labels and per-clip feedback textareas
- Living evaluation report at `docs/research/TopView_Eval.md` — methodology, credit math, per-model qualitative checklists, decision matrix, tier recommendations
- Review deployed to https://scooby-video-review.netlify.app for non-technical partner feedback

**Runs completed (7 total, 6 successful):**
- Image-to-Video: Kling 2.6 (3.25 cr), Vidu Q3 Pro (7.2 cr), Seedance 1.0 Pro Fast (0.7 cr), Sora 2 Pro (blocked by moderation on human faces)
- Text-to-Video: Kling V3 (4.0 cr), Sora 2 Pro (13.44 cr), Seedance 1.5 pro (2.0 cr)

**Key findings:**
- Seedance 1.0 Pro Fast is ~10× cheaper per second than Kling 2.6 (0.07 vs 0.65 credits/sec) — if quality holds up in partner review, it becomes the budget-tier default
- Sora 2 Pro i2v rejects any source image containing a realistic human, ruling it out for Scooby's default character-driven pipeline (still viable for Freestyle t2v mode and environment-only shots)
- All working models produce genuine 9:16 vertical output

### [CHANGED]
- `.gitignore` adds `.firecrawl/` (local scrape cache) and `test_generations/` (eval output and generated videos)

---

## [0.5.0] — 2026-04-07

### [ADDED]

**YouTube-to-Series Import:**
- YouTube-to-Series input path: paste a YouTube URL to create a multi-episode visual series
- AI Series Planner: Claude analyzes full video transcript and plans 3-8 standalone episodes with dramatic structure
- YouTube transcript extraction service with auto-caption cleanup
- Series plan review UI: edit titles, remove episodes, reorder before generating
- `source_type`, `source_url`, `source_meta` columns on Story model for multi-source support
- `episode_number`, `series_angle` columns on Episode model for series ordering
- `POST /api/v1/youtube/import` — import YouTube video and plan series
- `GET /api/v1/youtube/{story_id}/plan` — retrieve series plan for review
- `POST /api/v1/youtube/{story_id}/approve` — approve plan and start episode generation
- Tab switcher on story creation page: "Write a Story" / "Import from YouTube"
- Fair use acknowledgment + relationship selector on YouTube import form
- Automatic non-removable attribution on all YouTube-sourced episodes (preview, share, MP4 end card)
- Source badge on stories list (YouTube vs original)

**Pluggable Generation Providers:**
- Provider registry pattern for image generation — swap AI models via `IMAGE_PROVIDER` env var
- Nanobanana 2 (Gemini 3.1 Flash) image provider via Google API ($0.034-0.067/image)
- Kling 3.0 image-to-video animation provider via WaveSpeed API ($0.35-1.20/clip)
- Animation provider registry — swap via `VIDEO_ANIMATION_PROVIDER` env var
- `generate_animations_task` in pipeline (between images and voiceover)
- `generation_tier` column on Episode model (standard/enhanced/movie_lite/movie/movie_pro)
- Phase 0 test scripts: `scripts/test_nanobanana2.py`, `scripts/test_kling_animation.py`, `scripts/compare_generations.py`

**Testing:**
- 34 automated unit tests (all mocked, no API keys needed)
- Testing checklist document (`docs/Testing_Checklist.md`)
- Tests cover: image providers, animation providers, pipeline integration, YouTube import

### [CHANGED]
- PRD updated to v0.2 with two input paths, content repurposer persona, and competitive differentiation
- Project plan updated to v0.6 with consolidated feature work
- Marketing plan updated with content repurposing positioning
- Overview deck updated with "Canva with multi-use" pitch
- Pipeline task uses pluggable provider registry instead of hardcoded Stability AI
- Enhancements doc expanded with Movie Lite tier, Script Mode, Freestyle Mode concepts
- Feature branches consolidated onto master (feat/youtube-to-series + feat/pluggable-generation-providers deleted)

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
