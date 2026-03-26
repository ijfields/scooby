# Scooby — Task Manager / Memory Bank

> **Last updated:** 2026-03-25

---

## Project Status

| Phase | Status |
|-------|--------|
| Ideation & Research | Completed |
| Documentation | Completed |
| Environment Setup | **Next** |
| Landing Page Build | Planned |
| Core Wizard Flow | Planned |
| Video Pipeline | Planned |

---

## Previous (Completed)

### Ideation Phase
- Conversation with unpublished writer identified the core problem: writers have stories but no production skills
- Researched manual workflow: Veo 3 (via Gemini Business) + CapCut + ElevenLabs + ChatGPT prompting
- Explored vertical drama format: 60-90 second, 9:16, 5-7 beat structure (hook → setup → escalation → climax → button)
- Researched Claude Code + Remotion integration for programmatic video generation
- Developed platform concept: "Canva for stories" — phased from solo writer MVP to collaborative writers' room
- Created genesis document (`docs/genesis.md`) capturing the full evolution

### Documentation Phase
- Created complete documentation suite (9 documents):
  - `PRD.md` — Product requirements, MVP scope, user flow, tech stack
  - `Schemas.md` — Database schema (7 tables), seed data, migration notes
  - `API_Documentation.md` — Full REST API spec with examples
  - `Backend.md` — Architecture, AI pipelines, Celery orchestration, cost estimates
  - `Project_plan.md` — Phase 1 action items (10 workstreams), future phases
  - `Memory.md` — This file (task tracking)
  - `Changelog.md` — Semantic changelog
  - `Enhancements.md` — Out-of-scope items for Phase 2+
  - `Marketing_Plan.md` — Pre-launch and launch strategy

---

## Current

**Status:** Documentation complete. Ready to begin environment setup.

---

## Next Steps

1. **Environment setup** — Initialize monorepo, scaffold frontend (Next.js 14+), backend (FastAPI), and Remotion sidecar
2. **Database setup** — Docker Compose for PostgreSQL + Redis, run initial migrations
3. **Landing page build** — Hero section, How It Works, Features, CTA, Footer
4. **Auth integration** — Clerk setup, JWT verification, user sync
5. **Story intake UI** — Text input page with validation and API integration

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-25 | MVP = single writer, single episode | Simplest path to validate core value prop with target persona |
| 2026-03-25 | Next.js 14+ App Router for frontend | Server components, built-in API routes, fast iteration |
| 2026-03-25 | Python/FastAPI for backend | Async-native, excellent for AI API orchestration |
| 2026-03-25 | Celery + Redis for async jobs | Mature task queue with chaining, groups, and progress tracking |
| 2026-03-25 | Remotion for video composition | Programmatic React-based video, no manual editing needed |
| 2026-03-25 | Claude for story breakdown | Best at structured text analysis, reliable JSON output |
| 2026-03-25 | Stability AI for images | Cost-effective, good quality, 9:16 support |
| 2026-03-25 | ElevenLabs for TTS | Natural-sounding voices, easy API, voice presets |
| 2026-03-25 | Clerk for auth | Fast integration, social logins, JWT for backend verification |
| 2026-03-25 | Combined landing page + app | Phase 1 is a single entry point — hero → CTA → wizard |

---

## Open Questions

| # | Question | Status |
|---|----------|--------|
| 1 | Should MVP be sessionless (no auth) or require sign-up? | Leaning toward requiring auth via Clerk for persistence |
| 2 | Free tier limits — how many episodes per user? | TBD — depends on per-episode cost (~$0.30-0.67) |
| 3 | Hosting: Vercel + Fly.io vs. single VPS vs. cloud? | TBD — evaluate during environment setup |
| 4 | Voice dictation for story input — Phase 1 or 1.5? | Deferred to Phase 1.5 |
| 5 | Should we support story file upload (txt, docx)? | Deferred — paste/type only for MVP |
