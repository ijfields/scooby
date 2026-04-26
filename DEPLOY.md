# Railway Deployment Guide

> **Last updated:** 2026-03-28

## Architecture Overview

Scooby runs 4 services on Railway, all from the same GitHub repo (`ijfields/scooby`):

| Service | Purpose | Root Dir | Builder | Public URL |
|---------|---------|----------|---------|------------|
| **Backend** | FastAPI REST API | `/backend` | Dockerfile (`backend/Dockerfile`) | Yes |
| **Frontend** | Next.js 16 app | `/frontend` | Dockerfile (`frontend/Dockerfile`) | Yes |
| **Worker** | Celery task worker | *(none)* | Dockerfile (`Dockerfile.worker`) | No |
| **Postgres** | Database | — | Railway managed | No |
| **Redis** | Celery broker + cache | — | Railway managed | No |

## Prerequisites

- Railway CLI installed (`npm i -g @railway/cli`)
- Railway account logged in (`railway login`)
- GitHub repo connected to Railway project
- API keys for: Clerk, Anthropic, Stability AI, ElevenLabs

---

## Step 1: Create Railway Project

```bash
railway login
railway init    # Name it "scooby"
```

## Step 2: Add Managed Services

Railway dashboard → **New Service**:
1. **PostgreSQL** — Add Database → PostgreSQL
2. **Redis** — Add Database → Redis

## Step 3: Deploy Backend

1. **New Service** → GitHub Repo → `ijfields/scooby`
2. Name: `backend`
3. **Settings → Source:**
   - Root Directory: `/backend`
   - Branch: `master`
4. **Settings → Build:**
   - Builder: **Dockerfile** (reads from `backend/railway.toml`)
   - Dockerfile Path: `Dockerfile`
5. **Settings → Networking:**
   - Click **Generate Domain** for a public URL
6. **Variables** (see Step 6)

### Known Issues — Backend
- The `backend/railway.toml` uses `builder = "dockerfile"`. If Railway shows "Railpack", ensure root dir is `/backend`.
- The start command uses `sh -c` wrapper for `${PORT}` variable expansion:
  ```
  sh -c 'uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'
  ```
- The `backend/Dockerfile` uses paths relative to `/backend` (e.g., `COPY requirements.txt ./`, not `COPY backend/requirements.txt`).

## Step 4: Deploy Frontend

1. **New Service** → GitHub Repo → `ijfields/scooby`
2. Name: `scooby Frontend`
3. **Settings → Source:**
   - Root Directory: `/frontend`
   - Branch: `master`
4. **Settings → Build:**
   - Builder: **Dockerfile**
   - Dockerfile Path: `Dockerfile`
5. **Settings → Networking:**
   - Click **Generate Domain** for a public URL
6. **Variables:**
   - `NEXT_PUBLIC_API_URL` = `https://<backend-domain>.up.railway.app`
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` = `pk_...`
   - `CLERK_SECRET_KEY` = `sk_...`

### Known Issues — Frontend
- `NEXT_PUBLIC_*` vars are baked in at **build time**. If you change them, you must **redeploy** (not just restart).
- The `frontend/Dockerfile` uses paths relative to `/frontend` (e.g., `COPY . .`, not `COPY frontend/ .`).
- `next.config.ts` must have `output: "standalone"` for the Docker multi-stage build.

## Step 5: Deploy Worker

The worker runs Celery tasks (AI scene breakdown, image generation, TTS, video rendering).

1. **New Service** → GitHub Repo → `ijfields/scooby`
2. Name: `worker`
3. **Settings → Source:**
   - Root Directory: *(leave empty — do NOT set)*
   - Branch: `master`
4. **Settings → Build:**
   - Builder: **Dockerfile**
   - Dockerfile Path: `Dockerfile.worker`
5. **No public domain needed** — worker doesn't serve HTTP
6. **Variables** (see Step 6)

### Known Issues — Worker
- Root directory must be **empty** (not `/worker`, not `/backend`). The `Dockerfile.worker` is at repo root and copies from `backend/`.
- The worker listens on queues: `celery,ai_pipeline,image_gen,tts_gen,video_render,cleanup`. The `celery` default queue is important — some tasks may route there.
- If you see "Railpack could not determine how to build", the builder isn't set to Dockerfile. Check Settings → Build.
- If tasks are "received" but not executed, check for stale workers (`mingle: sync with N nodes` in logs).

## Step 6: Environment Variables

### Backend Variables

```
DATABASE_URL=postgresql://postgres:<password>@postgres.railway.internal:5432/railway
REDIS_URL=redis://default:<password>@<redis-host>.railway.internal:6379
CELERY_BROKER_URL=redis://default:<password>@<redis-host>.railway.internal:6379
CELERY_RESULT_BACKEND=redis://default:<password>@<redis-host>.railway.internal:6379
ALLOWED_ORIGINS=http://localhost:3001,http://localhost:3000,https://<frontend-domain>.up.railway.app
CLERK_ISSUER_URL=https://<your-clerk-instance>.clerk.accounts.dev
CLERK_SECRET_KEY=sk_test_...        # required: backend calls Clerk Backend API to fetch user email/name/avatar
ANTHROPIC_API_KEY=sk-ant-...
STABILITY_API_KEY=sk-...
ELEVENLABS_API_KEY=sk_...
SECRET_KEY=<generate-a-strong-random-string>
ENV=production
```

### Worker Variables

Same as backend except: no `ALLOWED_ORIGINS`, no `CLERK_ISSUER_URL`. Must include:
- `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `ANTHROPIC_API_KEY`, `STABILITY_API_KEY`, `ELEVENLABS_API_KEY`
- `SECRET_KEY`, `ENV=production`

### Frontend Variables

```
NEXT_PUBLIC_API_URL=https://<backend-domain>.up.railway.app
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...
```

## Step 7: Run Migrations

```bash
railway link       # Select backend service
railway run alembic upgrade head
```

## Step 8: Seed Style Presets

```bash
railway run python -m scripts.seed_style_presets
```

---

## Verify Deployment

| Check | URL | Expected |
|-------|-----|----------|
| Backend root | `https://<backend>/` | `{"service": "Scooby API", "status": "running", "docs": "/docs"}` |
| Backend health | `https://<backend>/health` | `{"status": "ok"}` |
| Backend docs | `https://<backend>/docs` | Swagger UI |
| Frontend | `https://<frontend>/` | Landing page |
| Worker | Check Railway logs | `celery@<host> ready.` |

---

## Troubleshooting

### CORS Errors
- Ensure `ALLOWED_ORIGINS` on the backend includes the full frontend URL (with `https://`).
- After changing, the backend must **redeploy** to pick up the new value.

### "Not Found" on root URL
- Backend has a root route at `/`. If missing, check that the latest code is deployed.

### 307 Redirects / Mixed Content
- FastAPI redirects `/stories` to `/stories/` by default. Collection routes use `""` not `"/"` to avoid this.
- Ensure frontend uses `https://` for the API URL, not `http://`.

### JWT / Clerk Auth Errors
- `pyjwt[crypto]` is required (not just `pyjwt`) for RSA key verification.
- Ensure `CLERK_ISSUER_URL` is set on the backend (used for JWKS lookup to verify JWT signatures).
- Ensure `CLERK_SECRET_KEY` is set on the backend — without it, new users get a synthetic `user_<id>@clerk.user` email instead of their real Clerk profile. Backend calls `GET https://api.clerk.com/v1/users/{id}` on first auth to populate email/name/avatar.

### ElevenLabs 401 Errors
- API key must have **Text to Speech** permission enabled (not just Voices).
- The deprecated `eleven_monolingual_v1` model is removed from free tier. Code uses `eleven_multilingual_v2`.
- Voice IDs from style presets may not be available. Code falls back to George (`JBFqnCBsd6RMkjVDRZzb`).

### Stability AI 429 Errors
- Check credit balance at [platform.stability.ai](https://platform.stability.ai).
- Each image generation costs ~0.5-1 credit. Free tier gives ~25 credits.
- Failed retries still consume credits for images that were generated before the failure.

### Celery Tasks Not Running
- Check worker logs for `celery@<host> ready.`
- Ensure worker listens on all queues: `celery,ai_pipeline,image_gen,tts_gen,video_render,cleanup`
- `include=["app.tasks.ai", "app.tasks.pipeline"]` must be set in `celery_app.py`
- Task routing is defined in `celery_app.py` — unrouted tasks go to the default `celery` queue.

### Video Render Fails
- Worker container ships with `ffmpeg` and `fonts-liberation` (installed via apt in `Dockerfile.worker`). If `ffmpeg: command not found`, the build is stale or the apt install failed — rebuild the worker.
- Render uses pure ffmpeg subprocess calls (Ken Burns zoompan + xfade crossfades + drawtext captions). No Node.js / Remotion dependency. The `REMOTION_SIDECAR_PATH` config setting is deprecated and unused.
- `FFMPEG_PATH` and `FFPROBE_PATH` env vars default to `ffmpeg` / `ffprobe` (matches the apt install). Override only if you've installed binaries elsewhere.

### Duplicate Row Errors
- Pipeline retries can create duplicate `VideoAsset` records. Queries use `ORDER BY created_at DESC LIMIT 1` to get the latest.

---

## CLI Quick Reference

```bash
# Link to project
railway link

# Switch between services
railway service backend
railway service "scooby Frontend"
railway service worker

# Deploy
railway up                  # Upload and deploy current service
railway redeploy --yes      # Redeploy from latest commit

# Logs
railway logs                # View runtime logs
railway logs --build        # View build logs

# Variables
railway variables           # List all variables

# Status
railway status              # Show current project/service
```

---

## Current Service URLs

- **Backend:** https://backend-production-67a9.up.railway.app
- **Frontend:** https://scooby-frontend-production.up.railway.app
