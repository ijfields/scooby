# Scooby

**"Canva for stories"** — Turn raw story text into 60–90 second vertical drama videos (9:16).

## Prerequisites

- **Node.js** 20+ (LTS) — for the frontend
- **Python** 3.11+ — for the backend and Celery worker
- **ffmpeg** + **ffprobe** — for video composition (the worker shells out to them)
- **Docker Desktop** — for local PostgreSQL & Redis

## Quickstart

```bash
# 1. Start infrastructure (Postgres on :5433, Redis on :6380)
docker compose up -d

# 2. Frontend
cd frontend && npm install && npm run dev   # → http://localhost:3001

# 3. Backend
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload                           # → http://localhost:8000

# 4. Celery worker (for AI pipeline + video render)
cd backend
celery -A app.celery_app worker --loglevel=info -Q celery,ai_pipeline,image_gen,tts_gen,video_render,cleanup
```

## Project Structure

```
scooby/
├── frontend/    # Next.js 16 App Router
├── backend/     # Python / FastAPI + Celery worker
├── scripts/     # Utility scripts (provider evals, diagnostics, backfills)
└── docs/        # Architecture, changelog, deployment guide
```

> The legacy `remotion/` directory is unused — the compositor switched to ffmpeg in v0.6.0 (see [docs/Changelog.md](docs/Changelog.md)). The dir is kept for now to avoid touching unrelated history; safe to delete in a future cleanup.

## Documentation

- [DEPLOY.md](DEPLOY.md) — Railway deployment guide
- [docs/Changelog.md](docs/Changelog.md) — Release history
- [docs/PRD.md](docs/PRD.md) — Product requirements
- [docs/Project_plan.md](docs/Project_plan.md) — Phase status & roadmap
- [docs/Backend.md](docs/Backend.md) — Backend architecture (parts marked historical, see banner)
- [docs/Testing_Checklist.md](docs/Testing_Checklist.md) — Manual + automated test procedures
