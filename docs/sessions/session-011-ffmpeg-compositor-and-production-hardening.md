# Session 011 — ffmpeg Compositor + Production Hardening

**Date range:** 2026-04-23 → 2026-04-30 (~7 days)
**Releases shipped:** v0.6.0, v0.6.1, v0.6.2, v0.6.3, v0.6.4, v0.6.5
**Commits:** 17 ([249a7a6](https://github.com/ijfields/scooby/commit/249a7a6) → [8e7cfa5](https://github.com/ijfields/scooby/commit/8e7cfa5))

## TL;DR

Replaced the never-shipped Remotion sidecar with a pure-ffmpeg compositor in the worker container, fixed two long-standing Clerk auth + UI bugs, persisted rendered MP4s in Postgres so they survive worker redeploys, shipped an in-app `<video>` player + a public share link Joyce can send to non-Scooby reviewers, evaluated TopView's Seedance 1.5 Pro for video animation, built a TopView-routed image provider after Stability AI and Google AI Studio both rate-limited / depleted, recovered a 26-day-old stuck episode, and produced a pre-launch scoping doc for the path to public users.

End state: **5 Movie-Lite-grade Joyce / Ingrid renders live in production**, all with persistent storage; **production image generation routed through TopView credits** instead of Google direct; **public share infrastructure ready** for non-user reviewers.

## Major workstreams

### 1. Compositor: Remotion → ffmpeg (v0.6.0, 2026-04-23)

**Why:** Remotion sidecar was never integrated; worker had no Node.js. Per project memory the renderer was marked "NOT STARTED" — ffmpeg in the worker container is the cheaper, faster path.

**What shipped** ([249a7a6](https://github.com/ijfields/scooby/commit/249a7a6)):
- `backend/app/services/video/renderer.py` rewritten — Ken Burns zoompan for static images, scale+pad+tpad for animation clips, xfade crossfades (≤4 scenes) or concat demuxer (5+), `adelay`-mixed voiceovers, `drawtext` caption burn.
- `Dockerfile.worker` + `worker/Dockerfile` install `ffmpeg` + `fonts-liberation`.
- `FFMPEG_PATH` / `FFPROBE_PATH` config settings; `REMOTION_SIDECAR_PATH` retained as deprecated, unused.
- `scripts/test_ffmpeg_renderer.py` — synthetic-asset smoke test.
- Verified end-to-end on production data (silent video).

**Bug fixes that followed:**
- **Windows font-path escape** — `_get_font_path()` over-escaped `:` as `\\:` instead of `\:`, breaking the drawtext filter on local dev. Linux production was fine.
- **Episode status sync** ([4d03cf8](https://github.com/ijfields/scooby/commit/4d03cf8), v0.6.1) — when render failed in the orchestrator's try/except, `job.status` flipped to `completed` but `episode.status` stayed `generating` forever. Fixed: orchestrator now refreshes the episode and forces `preview_ready` if still `generating`. Two production episodes had been stuck for ~4 weeks because of this.
- **Caption truncation** ([4cfb927](https://github.com/ijfields/scooby/commit/4cfb927), v0.6.3) — `drawtext` rendered `\n` as a literal "n" instead of a line break, producing single-line captions overflowing the frame. Fix: emit one `drawtext` per wrapped line with manual y-offsets. All 3 production episodes re-rendered with the fix.

### 2. Persistent video storage + in-app player (v0.6.2, 2026-04-27)

**Why:** Rendered MP4s lived at `/tmp/scooby/{episode_id}/final.mp4` on the worker — wiped on every redeploy. `final_video_url` was a worker-local path the browser couldn't load. So every render was effectively temporary.

**What shipped** ([d7cab92](https://github.com/ijfields/scooby/commit/d7cab92), [296075a](https://github.com/ijfields/scooby/commit/296075a)):
- 3 new columns on `episodes`: `final_video_data` (LargeBinary, deferred), `final_video_size_bytes`, `final_video_mime_type`. Migration `f7g2h8i9k0l1`.
- `compose_and_render_task` reads the rendered file and stores bytes alongside.
- `GET /api/v1/episodes/{id}/download/video` rewritten to stream bytes from Postgres (was returning a JSON pointer to the worker's `/tmp` path).
- `?inline=1` query param for in-browser playback (`Content-Disposition: inline`) vs the default attachment download.
- Frontend preview page renders `<video>` above the slideshow when the episode has bytes; uses the auth-aware blob-URL pattern so the bearer token is on the fetch.
- "Download MP4" button next to "Download Script".
- `scripts/backfill_episode_videos.py` — recovered the 2 production MP4s rendered before this column existed.

### 3. Clerk auth: real profile fetch (v0.6.0, 2026-04-26)

**Why:** Standard Clerk JWTs don't include email/name/avatar. The previous auto-create logic fell through to a synthetic `user_<clerk_id>@clerk.user` for every new user. Joyce had that placeholder; Ingrid had a hand-inserted dev placeholder (`user@scooby.app`). Both were correctly clerk-linked the whole time — only the email field was wrong.

**What shipped** ([04373c7](https://github.com/ijfields/scooby/commit/04373c7)):
- `app.core.auth.fetch_clerk_user()` — calls `GET https://api.clerk.com/v1/users/{id}` on first auth, populates email + display_name + avatar_url from the real profile.
- New `CLERK_SECRET_KEY` config setting required on backend.
- Falls back gracefully to JWT claims, then synthetic email, when the secret isn't set or the API call fails.
- `scripts/backfill_user_emails.py` — idempotent one-shot, fetched real Google emails for both production users (Ingrid Fields, Joyce Harris) on 2026-04-26.

**Saved memory:** `clerk_id` is the join key, never `email`. Documented in `project_auth_clerk.md`.

### 4. Public share link with video player (v0.6.4, 2026-04-29)

**Why:** Joyce wanted to send a preview link to non-Scooby reviewers (friends, social testers, agents). Existing share/{token} page only rendered the slideshow; the new `<video>` player from v0.6.2 was authed-only.

**What shipped** ([f899151](https://github.com/ijfields/scooby/commit/f899151)):
- New `GET /api/v1/shared/{token}/video?inline=1` — streams bytes using the share token as the credential, no Clerk JWT needed.
- Share page renders `<video>` above the slideshow when present.
- `SharedPreviewResponse` exposes `final_video_size_bytes` + `final_video_mime_type` so frontend knows when to show the player.
- Joyce's "Heart for Fun" episode now has a public share token: `CaxC4Hp0S8Mto4erOYIaaG3O3y6PD_a-Vo_E3r6-CIA`.

### 5. Scenes-page polling bug (v0.6.4, 2026-04-29)

**Why:** Episode `7eda8b61` ("I'm gonna tell it") had been showing an infinite spinner since 2026-04-02. Page logic was `if (status === 'draft' && scenes.length === 0) { setPolling(true); }` — never checked the underlying `GenerationJob.status`. The breakdown had failed weeks earlier with "Your credit balance is too low to access the Anthropic API" but the UI had no way to know.

**What shipped** (same commit as #4):
- Page also fetches `/api/v1/episodes/{id}/jobs` on each poll.
- If the latest `scene_breakdown` job is `failed`, polling stops and the error is shown with a way back.

### 6. TopView Seedance 1.5 Pro eval + Movie Lite render (2026-04-26 / 2026-04-27)

**Why:** Phase 0 had identified Seedance 1.5 Pro as the lead t2v candidate (~10× cheaper than Kling 2.6, comparable quality). Wanted to evaluate it on real Scooby content before integrating.

**What happened:**
- `scripts/eval_topview_joyce_heart.py` — hand-curated character bible prepended to each of Joyce's 6 scene prompts; runs Seedance 1.5 Pro t2v.
- 6/6 successful, 3.6 credits ($0.36), 7.5 min wall time, 720x1280 photorealistic.
- Character consistency strong on 4-of-5 Joyce shots; close-up "button" scene drifted (older-looking woman, brown vs gray cardigan) because the scene prompt was just "hands clapping" — bibles can't anchor identity when there's no character context to anchor to.
- `scripts/upload_joyce_movie_lite.py` — uploaded the 6 clips as `animation` VideoAssets on Joyce's existing scenes.
- Triggered `compose_and_render_task` — produced a Movie Lite version (animation clips + ElevenLabs VO + captions) at 1080x1920 H.264 + AAC, 66.8s, 32.6 MB.
- 5 production renders now persist in DB (Ingrid's "Betrayal Recording", Joyce's "$1 Standoff", Joyce's "Heart for Fun" — all three Storyboard renders, plus the Movie Lite version of "Heart for Fun"; all re-rendered after the caption fix).

### 7. Image provider chaos → TopView image-gen provider (v0.6.5, 2026-04-30)

**Why:** Stability AI returned a 429 mid-generation. Switched to NB2 (matches local). NB2 returned 429 RESOURCE_EXHAUSTED ("prepayment credits depleted") from Google AI Studio. Switched back to Stability. Then the user found that **TopView also offers Nano Banana 2 / Pro / Imagen 4** via API ([docs](https://docs.topview.ai/reference/text-to-image-image-edit-task-api-usage)) — same Google models, but billed through TopView's funded credits instead of Google direct.

**What shipped** ([2277b58](https://github.com/ijfields/scooby/commit/2277b58), [08b9d34](https://github.com/ijfields/scooby/commit/08b9d34)):
- `backend/app/services/image/topview.py` — submit / poll / download client.
- 3 new providers registered: `topview_nano_banana_2`, `topview_nano_banana_pro`, `topview_imagen_4`.
- `TOPVIEW_API_KEY` + `TOPVIEW_UID` first-class config (eval scripts had been reading them via `os.environ` directly).
- Production hot-switched to `topview_nano_banana_2` on deploy.
- End-to-end smoke test: ~114 seconds wall time, 3.2 MB photorealistic 9:16 image.
- One bug fix: TopView's per-image-task status comes back uppercase (`SUCCESS`) while parent task uses lowercase (`success`); polling helper now case-insensitive.

**Honest moment:** I initially told the user "TopView doesn't offer image generation." User pointed me at https://www.topview.ai/make/nano-banana-pro and proved me wrong. Updated changelog to reflect the corrected understanding.

### 8. Stuck episode recovery (2026-04-30)

`7eda8b61` ("I'm gonna tell it") had been stuck since 2026-04-02 because Anthropic credits had depleted at the time and the breakdown failed. Re-enqueued `generate_scene_breakdown_task` directly via `railway ssh`. Succeeded — episode now has 6 scenes, status flipped to `scenes_generated`, Ingrid can pick a style and continue.

### 9. Pre-launch reliability scoping ([8e7cfa5](https://github.com/ijfields/scooby/commit/8e7cfa5), 2026-04-30)

User asked about the path to a public platform: should we self-host or negotiate direct rates? Wrote `docs/Pre_Launch_Checklist.md` (208 lines) covering:

1. **Production Clerk keys** (~2h, blocks public launch). Hidden risk: prod clerk_ids ≠ dev clerk_ids; need a migration script or existing users get orphaned.
2. **Provider failover** (~1.5d). Today's two 429 incidents would have been fully recoverable with automatic chain.
3. **Cost-tracking per episode** (~1d). `cost_credits` column on `video_assets`, instrument providers, admin endpoint for breakdown by stage and provider.
4. **Sentry observability** (~1d). Recommended over Axiom for our use case; alerts on Celery failures, generate-endpoint error rates, stuck-job class of bug.

Recommendation: Clerk → failover → Sentry → cost-tracking. ~5 working days total.

## Infrastructure cleanup (2026-04-26)

User deleted 4 stale empty Postgres services and 2 stale Redis services from Railway. Active services now: **scooby Frontend, backend, worker, Postgres, Redis-7bIt**. Updated `deployment_details.md` accordingly.

## Files added (selection)

- `backend/app/services/video/renderer.py` — ffmpeg pipeline (replaced Remotion shim)
- `backend/app/services/image/topview.py` — TopView text2image client
- `backend/alembic/versions/f7g2h8i9k0l1_add_final_video_blob_to_episodes.py`
- `scripts/test_ffmpeg_renderer.py` — synthetic-asset compositor smoke test
- `scripts/backfill_user_emails.py` — Clerk Backend API one-shot
- `scripts/backfill_episode_videos.py` — recovered MP4s into the new blob columns
- `scripts/eval_topview_joyce_heart.py` — character-bible Seedance 1.5 Pro eval
- `scripts/upload_joyce_movie_lite.py` — animation-asset uploader
- `docs/Pre_Launch_Checklist.md` — scoping doc for public-launch reliability work

## Memory updates

- `MEMORY.md` — pipeline status (compositor: working, not "not started"); tech stack reflects ffmpeg
- `project_auth_clerk.md` (new) — clerk_id is the join key, why CLERK_SECRET_KEY is required, Backend API call pattern
- `feedback_doc_sync_discipline.md` (new) — sweep Changelog/PRD/READMEs as part of every change, not after the user asks
- `user_cofounder_context.md` — Joyce Harris by name, both clerk_ids documented
- `deployment_details.md` — cleaned-up service inventory after the 2026-04-26 Railway cleanup

## Known issues left for the next session

- **Episode `7eda8b61`** has scenes now but no styles/assets. Ingrid should pick a style and trigger generation to see whether the full pipeline survives end-to-end on the (currently active) TopView NB2 provider.
- **Image-regen on retry creates duplicates.** `run_full_pipeline_task` doesn't check for existing image assets; composer takes the latest. Cost waste, not breakage. Listed as Project_plan #9.
- **Watercolor visual preset** flagged as poor on Stability (Joyce 2026-04-26 — duplicate balls in the same frame). Not retested with NB2 / Imagen 4 yet.
- **`remotion/` directory** still in repo with full Node project + node_modules. Unused since v0.6.0. Safe to delete.
- **Provider failover** not yet implemented (scoping doc has the design).
- **Production Clerk keys** still pending (you're on `harmless-reindeer-82.clerk.accounts.dev` dev instance).
- **Seedance 2.0 Omni Reference eval** still pending — character lookbook approach was queued behind today's image-gen incident.

## Status

- **MVP pipeline:** working end-to-end for both Storyboard and Movie Lite tiers, with three production episodes verified.
- **Public-share infrastructure:** ready (Joyce can already send the share link to anyone).
- **Pre-launch reliability work:** scoped, not started.
