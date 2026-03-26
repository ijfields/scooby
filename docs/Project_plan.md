# Scooby — Phased Project Plan

> **Version:** 0.1 (MVP)
> **Last updated:** 2026-03-25
> **Focus:** Phase 1 — Combined Landing Page + Core Wizard Flow

---

## Phase 1: Landing Page + Core Flow (MVP)

The first deliverable is a combined landing page and application entry point. The hero section presents the value proposition, a "Start your story" CTA takes the user into the wizard flow, and the full story-to-video pipeline works end to end.

---

### 1.1 Environment & Repository Setup

| # | Task | Details |
|---|------|---------|
| 1 | Initialize monorepo | Create repo structure: `frontend/`, `backend/`, `remotion/`, `docs/`, `scripts/` |
| 2 | Frontend scaffolding | `npx create-next-app@latest` with App Router, TypeScript, Tailwind CSS, ESLint |
| 3 | Backend scaffolding | Python project with FastAPI, `pyproject.toml`, virtual env, Alembic for migrations |
| 4 | Remotion sidecar | `npx create-video@latest` in `remotion/` directory |
| 5 | Database setup | PostgreSQL local dev + Docker Compose config, initial migration with all tables from Schemas.md |
| 6 | Redis setup | Redis via Docker Compose for Celery broker |
| 7 | Environment config | `.env.example` with all required variables (API keys, DB URL, Redis, S3) |
| 8 | CI basics | GitHub Actions: lint + type-check on PR |

**Definition of done:** `npm run dev` serves frontend, `uvicorn` serves backend, DB migrations run, Redis connects.

---

### 1.2 Landing Page Build

| # | Task | Details |
|---|------|---------|
| 1 | Hero section | Headline: "Your stories deserve to be seen." Subheadline explaining the concept. Large "Start Your Story" CTA button. Background: subtle video or gradient animation. |
| 2 | How It Works section | 3-step visual strip: **Write** (story icon) → **Edit** (cards icon) → **Share** (play icon). Short description under each step. |
| 3 | Features section | 4 feature cards with icons: AI Scene Breakdown, Visual Style Presets, One-Click Video, Instant Export. Brief description per card. |
| 4 | Demo / Social Proof | Embedded demo video or animated GIF showing the wizard flow. Placeholder for testimonials. |
| 5 | Footer | Navigation links, copyright, "Built for writers" tagline. |
| 6 | Responsive design | Mobile-first (the landing page itself should look great on phones). |
| 7 | SEO & meta | Page title, description, Open Graph tags, favicon. |

**Definition of done:** Landing page renders at `/`, all sections visible, responsive on mobile/tablet/desktop, CTA scrolls or navigates to wizard.

---

### 1.3 Authentication (Clerk)

| # | Task | Details |
|---|------|---------|
| 1 | Clerk project setup | Create Clerk application, configure sign-in methods (email + Google) |
| 2 | Frontend integration | `@clerk/nextjs` provider, sign-in/sign-up components, protected routes |
| 3 | Backend JWT verification | FastAPI middleware to verify Clerk JWT from Authorization header |
| 4 | User sync endpoint | `POST /api/v1/auth/sync` — on first login, create local user record from Clerk data |
| 5 | Auth guard | Wizard pages require authentication; landing page is public |

**Definition of done:** User can sign up, sign in, and access wizard. Backend verifies JWT. User record synced to PostgreSQL.

---

### 1.4 Story Intake UI + API

| # | Task | Details |
|---|------|---------|
| 1 | Story input page | Full-width textarea with character count. Inline guidance text. Title input field. |
| 2 | Validation | Client-side: min 100 chars, max 5000 chars, title required. Server-side: same checks. |
| 3 | API endpoint | `POST /api/v1/stories` — creates story record, returns story ID |
| 4 | Stories list | `GET /api/v1/stories` — paginated list for user dashboard (simple card layout) |
| 5 | "Break down my story" CTA | Button that triggers scene generation, navigates to scene editor |

**Definition of done:** User types/pastes a story, clicks submit, story is saved to DB, user proceeds to scene breakdown.

---

### 1.5 AI Scene Breakdown Integration

| # | Task | Details |
|---|------|---------|
| 1 | Claude API integration | `anthropic` Python SDK, structured prompt for story → beats breakdown |
| 2 | Prompt engineering | System prompt instructing 5-7 beat structure (hook, setup, escalation 1-3, climax, button). Output as structured JSON. |
| 3 | Celery task | `generate_scene_breakdown` task — calls Claude, parses response, creates scene records |
| 4 | API endpoint | `POST /api/v1/episodes/:id/generate-breakdown` — triggers Celery task, returns job ID |
| 5 | Progress feedback | Polling or WebSocket — "Analyzing your story..." loading state in UI |
| 6 | Error handling | Retry on transient failures, user-friendly error if breakdown fails |

**Definition of done:** User clicks "Break down", Claude generates 5-7 beat cards, scenes appear in the editor within 10-30 seconds.

---

### 1.6 Scene Editor UI

| # | Task | Details |
|---|------|---------|
| 1 | Card layout | Vertical stack of scene cards, each showing: beat label, visual description, narration text |
| 2 | Inline editing | Click-to-edit on visual description and narration text fields |
| 3 | Tone buttons | Per-card: "More Dramatic", "Simpler Language", "Shorter" — call Claude to rewrite that beat |
| 4 | Card actions | Delete scene, merge with next scene |
| 5 | Add scene | "Add a scene" button inserts blank card at chosen position |
| 6 | Drag-and-drop reorder | React DnD for reordering cards |
| 7 | Auto-save | Debounced PATCH calls to save edits |
| 8 | Proceed button | "Choose style & generate" → navigates to style selection |

**Definition of done:** User sees beat cards, can edit/delete/reorder/add scenes, changes persist to DB.

---

### 1.7 Style & Voice Selection

| # | Task | Details |
|---|------|---------|
| 1 | Style presets API | `GET /api/v1/style-presets` — returns visual, voice, and music presets |
| 2 | Seed data | Insert 4 visual styles, 3 voice presets, 4 music moods into DB |
| 3 | Selection UI | Grid of style cards with thumbnails/previews. Radio selection per category. |
| 4 | Duration toggle | 60s or 90s toggle |
| 5 | Audio preview | Play voice sample and music sample inline |
| 6 | Save selections | `PATCH /api/v1/episodes/:id` — save style/voice/music/duration choices |

**Definition of done:** User selects visual style, voice, music mood, and duration. Choices saved to episode record.

---

### 1.8 Video Generation Pipeline

| # | Task | Details |
|---|------|---------|
| 1 | Image generation task | Celery task calling Stability AI for each scene (parallel group). 1080×1920 vertical images. |
| 2 | Voiceover generation task | Celery task calling ElevenLabs for each scene's narration (parallel group). |
| 3 | Remotion composition builder | Generate `composition.json` from scenes + assets. Map scenes to Remotion sequences with timing. |
| 4 | Remotion render task | Celery task that shells out to `npx remotion render` with the composition config. |
| 5 | Pipeline orchestration | Celery chain: images (group) → voiceovers (group) → compose → render → finalize |
| 6 | Progress tracking | Redis pub/sub → WebSocket. Report stage and percentage to frontend. |
| 7 | Asset upload | Upload generated images, audio, and final video to S3. |
| 8 | Error handling | Per-scene retry (max 3), overall pipeline failure handling with user notification. |

**Definition of done:** Clicking "Generate" kicks off the full pipeline. User sees real-time progress. Final MP4 is produced and stored.

---

### 1.9 Preview & Export

| # | Task | Details |
|---|------|---------|
| 1 | Video player | In-browser 9:16 video player with play/pause/scrub. Styled to show vertical format. |
| 2 | Per-scene regeneration | "Regenerate visuals" and "Regenerate VO" buttons per scene in preview mode |
| 3 | Final render | "Render Final" button triggers final high-quality render |
| 4 | Download MP4 | Direct download link from S3 |
| 5 | Script PDF export | Generate and download beat-by-beat script as PDF |
| 6 | Share link | (Stretch) Generate a public shareable link for the video |

**Definition of done:** User previews their episode, can regenerate individual scenes, and downloads the final MP4.

---

### 1.10 Testing & Polish

| # | Task | Details |
|---|------|---------|
| 1 | E2E happy path test | Playwright test: story input → scene breakdown → edit → style select → generate → download |
| 2 | API tests | pytest for all backend endpoints |
| 3 | Error states | Graceful handling of API failures, empty states, loading states |
| 4 | Performance | Optimize image loading, lazy load heavy components |
| 5 | Accessibility | Keyboard navigation, ARIA labels, color contrast |
| 6 | Mobile testing | Test wizard flow on mobile devices |
| 7 | Copy & UX review | Review all user-facing text, button labels, guidance messages |

**Definition of done:** All tests pass. No critical bugs. A non-technical user can complete the full flow unassisted.

---

## Phase 2: Collaborative Writers' Room (Future)

| Feature | Description |
|---------|-------------|
| Projects & series | Group episodes into series/seasons with shared character bibles |
| Shared workspace | Invite co-writers and editors with role-based access |
| Style presets library | User-created and shared style configurations |
| "In the style of" editing | AI-assisted tone/style transformation of scenes |
| Comments & annotations | Per-scene commenting and suggestion threads |
| Version history | Track changes across edits with rollback |

---

## Phase 3: Distribution & Analytics (Future)

| Feature | Description |
|---------|-------------|
| Platform publishing | Direct publish to TikTok, YouTube Shorts, Instagram Reels |
| Story analytics | Episode-level metrics: completion rate, drop-off, engagement |
| Marketing tools | Auto-generate thumbnails, titles, hashtags, descriptions |
| Monetization | Premium drops, licensing tools, crowdfunding integration |
| Multi-format output | Same story → vertical drama, audio drama, book format, pitch deck |

---

## Timeline Estimate

| Phase | Scope | Status |
|-------|-------|--------|
| **Phase 1** | Landing page + full wizard flow + pipeline | **Current** |
| **Phase 2** | Collaboration, projects, advanced editing | Planned |
| **Phase 3** | Distribution, analytics, monetization | Future |
