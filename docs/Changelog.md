# Scooby — Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/). Tags: `[ADDED]`, `[CHANGED]`, `[FIXED]`, `[REMOVED]`.

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
