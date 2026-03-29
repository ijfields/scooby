# Session 003 — Railway Deployment & Pipeline Integration

> **Date:** 2026-03-28
> **Duration:** Extended session
> **Focus:** Deploy all services to Railway, get video generation pipeline working end-to-end

---

## What We Did

### 1. Backend Deployment Fixes
- Added root `/` endpoint (was returning 404)
- Fixed `pyjwt` → `pyjwt[crypto]` for Clerk JWT/RSA verification
- Fixed UUID serialization in `UserResponse` (str → uuid.UUID)
- Removed trailing slash routes (`"/"` → `""`) to prevent 307 redirects causing mixed content errors
- Switched `backend/railway.toml` from nixpacks to Dockerfile builder
- Fixed Dockerfile paths for `/backend` root directory context
- Wrapped start command in `sh -c` for `${PORT}` variable expansion
- Added auto-migration on startup (`alembic upgrade head`)

### 2. Frontend Deployment (New)
- Created `frontend/Dockerfile` with multi-stage build (deps → build → runner)
- Added `output: "standalone"` to `next.config.ts`
- Set up as new Railway service with root dir `/frontend`
- Configured `NEXT_PUBLIC_API_URL`, Clerk keys as build-time env vars

### 3. Celery Worker Deployment (New)
- Created `Dockerfile.worker` at repo root
- Resolved Railway config-as-code conflicts (root `railway.toml` deleted)
- Fixed task discovery: added `include=["app.tasks.ai", "app.tasks.pipeline"]`
- Fixed task routing: mapped pipeline tasks to correct queues
- Added default `celery` queue to worker's `-Q` flag for unrouted tasks

### 4. CORS Configuration
- Added `ALLOWED_ORIGINS` env var with frontend Railway URL
- Backend CORS middleware reads from env var at startup

### 5. AI Service Fixes
- **ElevenLabs:** Upgraded from deprecated `eleven_monolingual_v1` to `eleven_multilingual_v2`
- **ElevenLabs:** Added voice ID validation with free-tier fallback (George - Warm Storyteller)
- **ElevenLabs:** API key needed "Text to Speech" permission enabled
- **Stability AI:** Discovered free credits exhausted from retry attempts; user added billing

### 6. Pipeline Resilience
- Fixed duplicate `VideoAsset` rows from retries (`ORDER BY created_at DESC LIMIT 1`)

### 7. Persistent Asset Storage (New)
- Added `file_data` (LargeBinary) column to VideoAsset model with deferred loading
- Pipeline now stores image/audio bytes directly in Postgres
- New `/api/v1/assets/{id}/file` endpoint serves assets via StreamingResponse
- New `/api/v1/episodes/{id}/gallery` HTML page shows images + audio players
- Alembic migration runs automatically on backend deploy

### 8. Documentation
- Rewrote `DEPLOY.md` with complete Railway setup guide and troubleshooting
- Updated `Changelog.md` with v0.3.0 entry
- Updated `Memory.md` with current project status and decisions

---

## Pipeline Status

| Step | Status | Service |
|------|--------|---------|
| Story intake | Working | Frontend → Backend |
| Scene breakdown (Claude) | Working | Worker (Celery) |
| Style selection | Working | Frontend → Backend |
| Image generation (Stability AI) | Working | Worker |
| Voiceover generation (ElevenLabs) | Working | Worker |
| Asset storage | Working | Postgres (LargeBinary) |
| Asset serving | Working | Backend API |
| Video compositing (Remotion) | **Not started** | Needs Node.js in worker |
| Preview/download | **Blocked** | Needs compositing |

---

## Commits This Session

1. `8fd9a1e` — feat: add root endpoint for Railway health visibility
2. `cbb5f1b` — feat: add frontend Railway deployment config
3. `c9f2fd6` — fix: update Dockerfile paths for Railway root directory context
4. `9f214ea` — fix: add cryptography extra to pyjwt for RSA support
5. `f561099` — fix: UUID serialization in auth and trailing slash redirects
6. `55700ae` — feat: add Celery worker service for Railway deployment
7. `499fe78` — fix: restructure worker Dockerfile for Railway service isolation
8. `0e1b236` — fix: add task module includes to Celery app config
9. `c9aa6ce` — fix: route pipeline tasks to correct Celery queues
10. `51b1a5b` — fix: add default celery queue to worker for unrouted tasks
11. `bcd4562` — fix: update backend Dockerfile and railway.toml for /backend root dir
12. `073fcb1` — fix: wrap backend start command in sh for variable expansion
13. `9c53af7` — fix: upgrade ElevenLabs model from deprecated eleven_monolingual_v1
14. `c56c338` — fix: add voice ID validation with free-tier fallback
15. `88ec8b2` — fix: handle duplicate video assets from pipeline retries
16. `658ae5e` — docs: comprehensive deployment guide and deployment session changelog
17. `acfe7f8` — feat: store generated assets in Postgres instead of temp filesystem
18. `fff1c4c` — chore: run alembic migrations on backend startup
19. `b473a96` — feat: add episode gallery page to view generated images and audio

---

## Key Lessons Learned

1. **Railway monorepo config:** Each service needs its own root dir + railway.toml. A root-level railway.toml overrides all services.
2. **NEXT_PUBLIC_ vars are build-time:** Must redeploy (not restart) frontend when changing them.
3. **Celery task routing:** Unrouted tasks go to default `celery` queue — worker must listen on it.
4. **ElevenLabs free tier:** Old models deprecated, voice IDs from presets may not be available. Always validate.
5. **Stability AI credits:** Failed retries still consume credits for already-generated images.
6. **Temp filesystem in containers:** Files in `/tmp` are lost on redeploy. Use DB or object storage for persistence.
7. **`railway run` uses internal hostnames:** Can't connect to `*.railway.internal` from local machine; use public URLs for local scripts.

---

## Open Items

- Remotion video compositing not integrated (worker needs Node.js)
- Style preset voice IDs in DB may reference unavailable voices
- No video preview/download yet (blocked on compositing)
- Clerk development keys in use — need production keys for launch
