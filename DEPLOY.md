# Railway Deployment Guide

## Prerequisites
- Railway CLI installed (`railway --version`)
- Railway account logged in (`railway login`)

## Step 1: Create Railway Project

```bash
railway login
railway init    # Creates new project, name it "scooby"
```

## Step 2: Add Services

Railway dashboard → Add services:

1. **PostgreSQL** — Add Database → PostgreSQL
2. **Redis** — Add Database → Redis
3. **Backend** (web) — New Service → GitHub repo → select `ijfields/scooby` → root directory: `backend`
4. **Worker** (optional for now) — Same repo, root directory: `backend`, start command: `celery -A app.core.celery_app worker --loglevel=info --pool=solo`

## Step 3: Configure Environment Variables

In the Backend service settings, add these env vars:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}  # Railway auto-injects
REDIS_URL=${{Redis.REDIS_URL}}           # Railway auto-injects
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}
ALLOWED_ORIGINS=https://your-frontend-url.vercel.app,http://localhost:3001
CLERK_ISSUER_URL=https://your-clerk-instance.clerk.accounts.dev
ANTHROPIC_API_KEY=sk-ant-...
STABILITY_API_KEY=sk-...
ELEVENLABS_API_KEY=...
SECRET_KEY=generate-a-strong-random-string
ENV=production
```

## Step 4: Deploy via CLI

```bash
cd backend
railway link          # Link to your project
railway up            # Deploy
```

## Step 5: Run Migrations

```bash
railway run alembic upgrade head
```

## Step 6: Seed Style Presets

```bash
railway run python -m scripts.seed_style_presets
```

## Step 7: Update Frontend

Update `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app
```

Then redeploy Vercel:
```bash
cd frontend
vercel --prod
```

## Verify

- Backend: `https://your-backend.up.railway.app/health` → `{"status": "ok"}`
- Frontend: Your Vercel URL should connect to Railway backend
