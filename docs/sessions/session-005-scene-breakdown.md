# Session 005 — Workstream 1.5: AI Scene Breakdown Integration

**Date:** 2026-03-26
**Status:** Complete

## What was done

### Backend — AI Service
- Created `app/services/ai/story_breakdown.py`:
  - Full Claude system prompt for 5-7 beat dramatic arc (hook, setup, escalation 1-3, climax, button)
  - `generate_scene_breakdown()` — calls Claude API, parses structured JSON response
  - `SceneBeat` and `SceneBreakdown` Pydantic models for validation
  - JSON extraction handles markdown code fences from Claude
  - Duration validation (55-95s range with tolerance)

### Backend — Celery Task
- Created `app/tasks/ai.py`:
  - `generate_scene_breakdown_task` — Celery task with retry (max 2)
  - Updates GenerationJob status (pending → running → completed/failed)
  - Creates Scene records from breakdown beats
  - Updates Episode title and status to "scenes_generated"
  - Uses sync SQLAlchemy session (Celery doesn't support async)

### Backend — Episodes API
- Created `app/api/v1/endpoints/episodes.py`:
  - `POST /episodes/from-story/{story_id}` — creates episode + dispatches Celery breakdown
  - `GET /episodes/{id}` — episode detail
  - `PATCH /episodes/{id}` — update episode (styles, duration)
  - `GET /episodes/{id}/scenes` — list scenes ordered
  - `PATCH /episodes/{id}/scenes/{scene_id}` — update scene
  - `DELETE /episodes/{id}/scenes/{scene_id}` — delete scene
  - `GET /episodes/{id}/jobs` — list generation jobs
- Created `app/schemas/episode.py` — all Pydantic schemas

## Notes
- Claude model: `claude-sonnet-4-20250514`
- Celery tasks use sync SQLAlchemy since Celery workers are synchronous
- Real scene breakdown requires ANTHROPIC_API_KEY to be set in .env
