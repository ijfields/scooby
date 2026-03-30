# Scooby — Phased Project Plan

> **Version:** 0.4
> **Last updated:** 2026-03-29
> **Focus:** Phase 1 completion — Lexicon, Branding, Shareable Previews

---

## Phase 1 Progress Tracker

| Workstream | Status | Notes |
|-----------|--------|-------|
| 1.1 Environment & Repo Setup | **Done** | Monorepo, Docker Compose, Railway deployment |
| 1.2 Landing Page | **Done** | Hero, how-it-works, features, CTA, updated demo section |
| 1.3 Authentication (Clerk) | **Done** | Dev keys — need production keys for launch |
| 1.4 Story Intake UI + API | **Done** | Create, list, view stories |
| 1.5 AI Scene Breakdown | **Done** | Claude integration, Celery task, polling UI |
| 1.6 Scene Editor UI | **Done** | Beat labels, inline edit, reorder, delete, preview link |
| 1.7 Style & Voice Selection | **Done** | Visual/voice/music presets, duration toggle |
| 1.8 Video Generation Pipeline | **Done** | Images (Stability AI) + voiceovers (ElevenLabs), Celery orchestration |
| 1.9 Preview & Export | **Partial** | Scene-by-scene slideshow preview working; Remotion video render not started |
| 1.10 Testing & Polish | **Not started** | E2E tests, error states, accessibility, mobile |

### Recent Additions (Session 004)

- Interactive scene-by-scene preview (slideshow with AI images, voiceover playback, auto-advance)
- `GET /episodes/{id}/scenes-with-assets` and `GET /episodes/by-story/{story_id}` endpoints
- Story detail page shows existing episodes (no more dead-end workflow)
- UI polish across all pages

---

## Current Sprint: Lexicon + Branding + Shareable Previews

### Priority 1: Lock the Content Lexicon

**Problem:** The codebase and UI use "episode" for everything — a single standalone generation and a member of a series. This is confusing for non-technical writers and will compound as we add series support.

**Proposed hierarchy:**

| Term | Definition | Contains | In Code (current) |
|------|-----------|----------|--------------------|
| **Story** | Raw text input from the writer | — | `stories` table (keep) |
| **Video** | One generated output — the thing you preview/export | Scenes | `episodes` table (rename) |
| **Scene** | A single beat within a video (image + narration) | Assets | `scenes` table (keep) |
| **Series** | A collection of related videos (optional, Phase 2) | Videos | Does not exist yet |

**Decision needed:** Confirm naming with cofounder before renaming. The rename touches:
- Database table + model (`episodes` -> `videos`)
- All API routes (`/episodes/` -> `/videos/`)
- All frontend pages and routes
- UI copy throughout

**Recommendation:** Do a single coordinated rename with an Alembic migration. Don't half-rename — that's worse than the current state.

### Priority 2: Branding & Visual Theme

**Goal:** Make the demo feel like a product, not a prototype, before gathering wider feedback.

| Item | Scope | Status |
|------|-------|--------|
| Competitive intelligence | FireCrawl analysis of 5 competitors — [see report](research/Competitive_Intelligence.md) | **Done** |
| Color palette | Deep Violet primary (#6D28D9) + Warm Amber accent (#F59E0B), full OKLCH system | **Done** |
| Typography | Playfair Display (headings), Inter (body), Geist Mono (code) | **Done** |
| Logo | "scooby" wordmark in Playfair Display italic | **Done** |
| Hero animation | Scroll-triggered before/after: raw story text → finished video scene (inspired by Nano Banana 2 technique) | Not started |
| Dark mode | Currently has CSS variables but not tested/polished | Not started |
| Empty states | Add illustrations or branded graphics | Partially done |
| Loading states | Consistent spinner/skeleton pattern | Partially done |
| UI/UX audit | Run accessibility, SEO, and design audit on landing page (post-branding) | Not started |

### Priority 3: Shareable Preview Links

**Goal:** Let the cofounder (and future test users) view a preview without logging in.

| Task | Details |
|------|---------|
| Share token generation | `POST /videos/{id}/share` → returns a short-lived or permanent token |
| Public preview route | `/share/{token}` — renders the slideshow preview, no auth required |
| Copy link button | On the preview page, one-click copy shareable URL |
| Optional: expiry | Tokens expire after N days or are revokable |

This is simpler and more useful than team/multi-user features right now.

---

## Phase 1 Remaining Work (after current sprint)

### 1.9 Preview & Export (remaining)

| # | Task | Details | Priority |
|---|------|---------|----------|
| 1 | Per-scene regeneration | "Regenerate image" and "Regenerate voiceover" buttons per scene | High |
| 2 | Remotion integration | Node.js sidecar, video composition, MP4 render | Medium — slideshow covers 80% |
| 3 | MP4 download | Direct download of rendered video | Blocked on Remotion |
| 4 | Script PDF export | Generate and download beat-by-beat script | Low |

### 1.10 Testing & Polish

| # | Task | Details | Priority |
|---|------|---------|----------|
| 1 | Error states | Graceful handling of API failures, timeouts, empty states | High |
| 2 | Mobile testing | Test full wizard flow on phone screens | High |
| 3 | Accessibility | Keyboard nav, ARIA labels, color contrast | Medium |
| 4 | E2E tests | Playwright: story → breakdown → style → generate → preview | Medium |
| 5 | API tests | pytest for all backend endpoints | Medium |
| 6 | Performance | Image lazy loading, skeleton states | Low |

---

## Phase 1.5: Veo Movie Mode (unchanged)

See [Enhancements.md](./Enhancements.md) for full spec. Prerequisite: Phase 1 complete with Remotion integration.

---

## Phase 2: Collaborative Writers' Room

> **Updated 2026-03-29** — Team features deferred to Phase 2. Shareable preview links (Phase 1) cover the immediate need.

| Feature | Description | Priority |
|---------|-------------|----------|
| Series support | Group videos into series with ordering | High — once lexicon is locked |
| Shared workspace | Invite collaborators by email, role-based access | Medium |
| Comments & annotations | Per-scene comment threads | Medium |
| Version history | Scene edit history with diff view and rollback | Low |
| Custom style presets | Users create and save their own styles | Low |

See [Enhancements.md](./Enhancements.md) for full Phase 2 spec.

---

## Phase 3: Distribution & Analytics (unchanged)

See [Enhancements.md](./Enhancements.md).

---

## Timeline & Milestones

| Milestone | Target | Status |
|-----------|--------|--------|
| Story → AI scenes → edit → style → generate pipeline | 2026-03-28 | **Done** |
| Scene-by-scene preview with images + audio | 2026-03-29 | **Done** |
| Episode navigation (revisit generated content) | 2026-03-29 | **Done** |
| Lexicon locked + rename | Next session | Pending |
| Branding pass (palette, typography, logo) | Next session | Pending |
| Shareable preview links | After branding | Pending |
| Cofounder feedback incorporated | Ongoing | Pending |
| Remotion video export | After feedback | Pending |
| Production Clerk keys | Before public launch | Pending |
| Public beta | TBD | Pending |

---

## Research & References

| Date | Source | Key Takeaway | Applies To |
|------|--------|-------------|------------|
| 2026-03-29 | [Claude Code + Nano Banana 2 + FireCrawl = Epic $12k Websites](https://www.youtube.com/watch?v=2gvFLFl4xw8) (Jack Roberts) | FireCrawl competitive intelligence process: scrape competitor sites → analyze design/copy/trust signals/SEO → synthesize "winning blueprint" with color palettes and content patterns | Priority 2: Branding |
| 2026-03-29 | Same video | Scroll-triggered hero animation (before/after transformation on scroll) — for Scooby: raw text → finished video scene | Priority 2: Hero animation |
| 2026-03-29 | Same video | UI/UX audit skill: run hundreds of accessibility + SEO + design checks as final polish pass | Priority 2: UI/UX audit |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-25 | Monorepo structure (frontend/backend/remotion) | Simpler CI, shared types later |
| 2026-03-26 | Combined landing page + app (not separate sites) | MVP speed, single deploy |
| 2026-03-28 | Store assets as LargeBinary in Postgres (not S3) | Simpler for MVP, migrate to S3 later |
| 2026-03-28 | Railway for all services (not Vercel + Fly) | Single platform, simpler ops |
| 2026-03-29 | Slideshow preview instead of waiting for Remotion | Gets 80% of experience now |
| 2026-03-29 | Shareable links before team features | Solves the immediate need (feedback) without the complexity of multi-user |
| 2026-03-29 | Lexicon rename before adding series | Foundational — rename once, not twice |
