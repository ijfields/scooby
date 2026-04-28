# Scooby — Testing Checklist

> **Last updated:** 2026-04-27

---

## Running Automated Tests

```bash
cd backend
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

### Test Files

| File | Covers | Requires DB |
|------|--------|-------------|
| `test_health.py` | Health endpoint | No |
| `test_stories.py` | Story CRUD | Yes |
| `test_episodes.py` | Episode CRUD | Yes |
| `test_styles.py` | Style presets | Yes |
| `test_image_providers.py` | Provider registry, NB2 service, Stability wrapper | No (mocked) |
| `test_animation_providers.py` | Animation registry, Kling service, WaveSpeed API | No (mocked) |
| `test_pipeline_providers.py` | Pipeline integration, config, Episode model | No (mocked) |
| `test_youtube_import.py` | Transcript extraction, series planner, schemas | No (mocked) |

---

## Manual Testing Checklist

### Core Pipeline (Existing MVP)

- [ ] **Story creation** — Create a new story with 300-800 words of text
- [ ] **Scene breakdown** — Verify Claude generates 5-7 scenes with beat types
- [ ] **Style selection** — Select visual + voice style presets
- [ ] **Image generation** — All scenes get images (check `/api/v1/assets/{id}/file`)
- [ ] **Voiceover generation** — All scenes get audio (non-fatal if ElevenLabs fails)
- [ ] **Scene preview** — Interactive slideshow plays images + audio with auto-advance
- [ ] **Shareable link** — Generate share token, verify preview works without login

### YouTube-to-Series (New)

- [ ] **Import form** — Tab switcher shows "Write" and "Import from YouTube" tabs
- [ ] **URL validation** — Accepts youtube.com/watch, youtu.be, youtube.com/shorts URLs
- [ ] **Relationship selector** — Creator/Permission/Fair Use options render
- [ ] **Fair use checkbox** — Required before submit when Fair Use selected
- [ ] **Transcript fetch** — Backend extracts transcript (check Celery logs)
- [ ] **Series planning** — Claude generates multi-episode plan with angles/hooks
- [ ] **Plan review UI** — Episodes shown with toggle to include/exclude
- [ ] **Plan approval** — Approved episodes create Episode records with scene breakdowns
- [ ] **Attribution display** — YouTube source shown in episode preview + shared links
- [ ] **YouTube Series badge** — Story cards show badge for YouTube-sourced content
- [ ] **Error handling** — Private/unavailable video shows clear error message
- [ ] **Status polling** — UI polls during importing/planning states, stops on completion

### Pluggable Generation Providers (New)

#### Phase 0: Test Scripts (run before backend integration)

```bash
# 1. Test Nanobanana 2 image generation
GOOGLE_API_KEY=your-key python scripts/test_nanobanana2.py
# → Check: test_generations/nanobanana2/ has 3 PNG images
# → Check: Images are portrait (9:16), cinematic quality

# 2. Test Kling 3.0 animation
WAVESPEED_API_KEY=your-key python scripts/test_kling_animation.py
# → Input: public URL of a test image
# → Check: test_generations/kling/ has MP4 video clips
# → Check: Videos show smooth camera motion, 5-8 seconds

# 3. Side-by-side comparison
STABILITY_API_KEY=xxx GOOGLE_API_KEY=xxx python scripts/compare_generations.py
# → Check: test_generations/comparison/ has pairs of images
# → Check: Compare quality, style consistency, prompt adherence
```

- [ ] NB2 generates images successfully
- [ ] NB2 images are comparable or better quality than Stability AI
- [ ] NB2 handles vertical 9:16 composition well
- [ ] Kling generates video clips from images
- [ ] Kling videos have smooth, natural camera motion
- [ ] Kling respects animation prompt (zoom, pan, etc.)
- [ ] Comparison script runs both providers on same prompts

#### Provider System Integration

- [ ] **Default provider** — `IMAGE_PROVIDER=stability` uses Stability AI (unchanged behavior)
- [ ] **Swap to NB2** — Set `IMAGE_PROVIDER=nanobanana2`, run pipeline, verify NB2 images
- [ ] **Provider metadata** — Generated asset `metadata_` shows correct provider name
- [ ] **Animation off** — `VIDEO_ANIMATION_PROVIDER=none` skips animation step
- [ ] **Animation on** — `VIDEO_ANIMATION_PROVIDER=kling_std` generates video clips
- [ ] **Animation assets** — Video clips stored as `asset_type="animation"` with `video/mp4` mime
- [ ] **Pipeline timing** — Animation adds 2-6 min per scene (logged in Celery)
- [ ] **Missing API key** — Clear error message when GOOGLE_API_KEY or WAVESPEED_API_KEY missing
- [ ] **Generation tier** — Episode `generation_tier` column accepts standard/enhanced/movie_lite

### Railway Deployment Checks

- [ ] **Backend deploys** — Push to master triggers Railway rebuild
- [ ] **Migration runs** — `alembic upgrade head` adds new columns without errors
- [ ] **Env vars set** — GOOGLE_API_KEY, WAVESPEED_API_KEY configured (if using new providers)
- [ ] **Worker picks up tasks** — Celery worker processes YouTube import + pipeline tasks
- [ ] **Frontend deploys** — Next.js builds without errors, new pages accessible

### Netlify (if applicable)

- [ ] **Site deploys** — Verify Netlify build succeeds
- [ ] **Routing** — All pages load correctly (stories, episodes, share links)

### Local Dev Smoke Test

```bash
# Start local stack
docker-compose up -d   # Postgres + Redis
cd backend && uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev -- -p 3001

# Quick smoke test
curl http://localhost:8000/api/v1/health
# → {"status": "ok"}
```

- [ ] Backend starts without import errors
- [ ] Frontend compiles without errors
- [ ] Health endpoint responds
- [ ] Can create a story end-to-end

---

## Environment Variables Reference

### Required (existing)

| Var | Service |
|-----|---------|
| `ANTHROPIC_API_KEY` | Claude scene breakdown + series planning |
| `STABILITY_API_KEY` | Image generation (default provider) |
| `ELEVENLABS_API_KEY` | Voiceover generation |
| `DATABASE_URL` | PostgreSQL |
| `REDIS_URL` | Celery broker |
| `CLERK_ISSUER_URL` | Auth |

### New (optional — for new providers)

| Var | Default | Purpose |
|-----|---------|---------|
| `GOOGLE_API_KEY` | `""` | Nanobanana 2 image generation |
| `WAVESPEED_API_KEY` | `""` | Kling 3.0 animation via WaveSpeed |
| `IMAGE_PROVIDER` | `"stability"` | `stability` or `nanobanana2` |
| `VIDEO_ANIMATION_PROVIDER` | `"none"` | `none`, `kling_std`, or `kling_pro` |

---

## Cost Monitoring

After enabling new providers, monitor actual costs:

| Provider | Expected Cost | How to Check |
|----------|--------------|--------------|
| Stability AI | ~$0.03-0.06/image | Stability AI dashboard |
| Nanobanana 2 | ~$0.034-0.067/image | Google Cloud Console → Billing |
| Kling 3.0 Std | ~$0.35-0.50/5s clip | WaveSpeed dashboard |
| Kling 3.0 Pro | ~$1.20/5s clip | WaveSpeed dashboard |
| TopView Seedance 1.5 Pro | ~$0.30-0.50/5-8s clip | TopView dashboard (credits) |
| Claude | ~$0.01-0.03/breakdown | Anthropic dashboard |
| ElevenLabs | ~$0.01-0.03/scene | ElevenLabs usage page |

---

## Polishing Matrix (added 2026-04-27)

> **Goal:** systematically test combinations of pipeline components to identify which produce the best output for the writer cofounder. Run one matrix cell per real story and capture quick subjective notes. The output of every cell is a viewable episode in production — link to the preview URL in the notes column.

### Visual style × image provider

Most important matrix to run first. Same story, same scene breakdown, vary just these two axes. Score on character consistency + visual coherence + "does this feel like the writer's tone?"

| Visual style preset | Stability AI | Nanobanana 2 | Notes |
|---------------------|--------------|--------------|-------|
| Cinematic (default) | | | |
| Watercolor | ❌ poor (Joyce 2026-04-26) | | Watercolor preset on Stability produced inconsistent character renders + duplicate object hallucinations (e.g. two red balls in foreground). Try NB2 with same preset before retiring it. |
| Comic / graphic novel | ✓ good (Ingrid Betrayal Recording) | | Strong B&W ink-style renders for stylized drama. |
| Photorealistic | ✓ good (Joyce $1 Standoff) | | Most cinematic-looking output of the three. |
| Anime / illustrative | | | Not yet tested. |

### Animation provider

Run the same episode through each animation backend, compare the resulting clips' continuity + character coherence.

| Animation provider | Cost / 5-8s clip | Status | Best for |
|--------------------|------------------|--------|----------|
| `none` (Storyboard / Ken Burns) | $0 | Default, working | Free tier, fastest, lowest cost |
| Kling 3.0 std (WaveSpeed) | ~$0.35-0.50 | Built, untested | Mid-tier — needs validation run |
| Kling 3.0 pro (WaveSpeed) | ~$1.20 | Built, untested | Premium tier |
| TopView Seedance 1.5 Pro (t2v) | ~$0.30-0.50 | Eval in flight (Joyce Heart for Fun) | **Candidate winner per Phase 0** |
| TopView Veo 3.1 Fast | TBD | Phase 0 only | Higher quality, native audio |

### Voice preset (ElevenLabs)

Subjective listen-test only — pick 2-3 narration styles per story and have the writer pick.

| Voice | Voice ID | Tone | Use cases |
|-------|----------|------|-----------|
| George (default fallback) | `JBFqnCBsd6RMkjVDRZzb` | Warm storyteller | All-purpose |
| Sarah | `EXAVITQu4vr4xnSDxMaL` | Bright, conversational | Lighter material |
| Charlie | `IKne3meq5aSn9XLyUdCD` | Older, gravitas | Drama, retrospection |
| Laura | `FGY2WhTYpPnrIDTdsKH5` | Younger female | Coming-of-age |
| Roger | `CwhRBWXzGAHq8TQ4Fs17` | Grounded male | Documentary feel |

Free-tier-safe voice list lives in [tts/generator.py:17](backend/app/services/tts/generator.py#L17). Anything outside that set falls back to George.

### Story type × source

| Source | Status | Notes |
|--------|--------|-------|
| User-typed text | ✓ Working | Both production users (Ingrid + Joyce) have used this path |
| YouTube URL → series planner | Built, lightly tested | Run an end-to-end with a real YouTube video before exposing more broadly |

### Caption rendering

| Caption length | Result | Notes |
|----------------|--------|-------|
| Single short sentence (≤32 chars) | ✓ Single line, centered, readable | Joyce hook scene "Today I chose to just be." |
| Wrapped multi-line (≥33 chars) | ✓ Multi-line stack, centered | Fixed in v0.6.3 (per-line drawtext) |
| Special characters (`'`, `:`, `%`, `\`) | ✓ Escaped | Verified via the synthetic test in `scripts/test_ffmpeg_renderer.py` |

---

## Character Consistency (added 2026-04-27)

t2v and t2i models don't have cross-call state — characters drift across independent scene generations. The mitigation is a **character bible** prepended to every scene prompt. Reference implementation lives in [scripts/eval_topview_joyce_heart.py](scripts/eval_topview_joyce_heart.py).

Bible should be tight (≤500 chars) and cover: name, demographics, distinguishing features, typical clothing, demeanor. Avoid prompt bloat — verbose bibles dilute the scene-specific direction.

**Open product question:** how should writers author the bible? Options being considered:
- Auto-extract from `Story.raw_text` via Claude on first scene generation (no UI work needed)
- Explicit "Character Bible" step in the wizard between scene breakdown and image gen (more friction, more control)
- Hybrid: auto-extract a draft, let the writer edit before locking it in
