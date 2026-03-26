# Scooby

**"Canva for stories"** — Turn raw story text into 60–90 second vertical drama videos (9:16).

## Prerequisites

- **Node.js** 20+ (LTS)
- **Python** 3.11+
- **Docker Desktop** (for PostgreSQL & Redis)

## Quickstart

```bash
# 1. Start infrastructure
docker compose up -d

# 2. Frontend
cd frontend && npm install && npm run dev   # → http://localhost:3001

# 3. Backend
cd backend
python -m venv .venv && source .venv/Scripts/activate   # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload                           # → http://localhost:8000

# 4. Remotion sidecar
cd remotion && npm install && npx remotion studio
```

## Project Structure

```
scooby/
├── frontend/    # Next.js 14+ App Router
├── backend/     # Python / FastAPI
├── remotion/    # Remotion video sidecar
├── scripts/     # Utility scripts
└── docs/        # Architecture & design docs
```
