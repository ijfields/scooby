# Scooby — Product Requirements Document (PRD)

> **Codename:** Scooby
> **Version:** 0.1 (MVP)
> **Last updated:** 2026-03-25

---

## 1. Product Vision

**Scooby** is a "Canva for stories" — a web platform that lets non-technical writers turn raw story text into finished 60–90 second vertical drama videos (9:16 format for TikTok, Reels, and Shorts). Writers paste or dictate a story, AI breaks it into scenes, the writer reviews simple cards, picks a style, and the platform renders a ready-to-post MP4. No editing software, no prompt engineering, no production skills required.

### Elevator Pitch

> Writers have stories. They don't have production teams. Scooby lets any writer paste a story and walk away with a vertical drama episode — no AI expertise, no video editing, just their voice on screen.

---

## 2. Origin & Motivation

The idea originated from a real conversation with an unpublished writer who has a rich backlog of stories but no technical skills. She was excited about vertical dramas but overwhelmed by the manual workflow (Veo + CapCut + ElevenLabs + prompt engineering). Scooby automates that entire pipeline behind a simple guided interface.

See [`genesis.md`](./genesis.md) for the full evolution from manual workflow to platform concept.

---

## 3. Target Audience

### Primary Persona: The Unpublished Writer

| Attribute | Detail |
|-----------|--------|
| **Who** | Independent, unpublished, or early-stage fiction writers |
| **Has** | Finished short stories, scenes, or story ideas (300–800 words) |
| **Wants** | To see their story come to life as a shareable vertical video |
| **Lacks** | AI fluency, video editing skills, production budget |
| **Motivation** | Monetization, audience reach, creative satisfaction, preserving their work |

### Secondary Personas (Post-MVP)

- Poets, diarists, bloggers experimenting with visual storytelling
- Writing teachers and coaches creating demo content
- Screenwriters prototyping micro-drama concepts
- Small creative teams collaborating on series

---

## 4. MVP Scope

**Single writer. Single episode. Story in → video out.**

### What's IN the MVP

- Story text input (paste or type)
- AI-powered scene breakdown into 5–7 beat cards
- Card-based scene editing (no timeline, no keyframes)
- Style and voice preset selection
- AI video generation (images + VO + composition)
- Preview player with per-scene regeneration
- MP4 export (1080×1920, 9:16)
- Optional script PDF export

### What's explicitly NOT in the MVP

- Multi-episode projects or series
- Collaborators, comments, or team roles
- Analytics, distribution integrations, or marketing tools
- Complex timeline editing
- Voice-to-text story input (dictation) — deferred to Phase 1.5
- User accounts with saved projects (MVP can be sessionless or minimal auth)

---

## 5. User Flow

### Step-by-Step Wizard

```
Landing Page (Hero + CTA)
    │
    ▼
[1] Story Intake
    │   - Paste or type story text
    │   - Basic guidance shown ("Best results: 300–800 words,
    │     one main character, one clear turning point")
    │   - "Break down my story" button
    ▼
[2] Scene Cards (AI Breakdown)
    │   - 5–7 beat cards displayed:
    │     Hook → Setup → Escalation 1–3 → Climax → Button
    │   - Each card shows:
    │       • Visual description (1–2 sentences)
    │       • Narration/dialogue (1–2 lines)
    │   - Writer can edit text, delete/merge beats,
    │     or click tone buttons ("more dramatic", "simpler language")
    ▼
[3] Style & Voice Selection
    │   - Episode length: 60s or 90s
    │   - Visual style preset (3–4 options):
    │     "Soft Realistic", "Moody Graphic Novel",
    │     "Watercolor", "Cinematic Dark"
    │   - Narration voice (3–4 options):
    │     "Warm Female", "Calm Male", "Neutral Storyteller",
    │     "No VO — subtitles only"
    ▼
[4] Generation & Preview
    │   - Progress indicator with stage labels
    │   - Preview player (9:16 in-browser)
    │   - Per-scene controls:
    │     "Regenerate visuals", "Regenerate VO"
    │   - "Render final" button
    ▼
[5] Export
        - Download MP4 (1080×1920)
        - Optional: Download script PDF
        - Share link (optional, stretch goal)
```

---

## 6. Feature Specifications

### 6.1 Landing Page

The landing page doubles as the app entry point (combined landing + app in Phase 1).

| Section | Content |
|---------|---------|
| **Hero** | Headline, subheadline, "Start your story" CTA |
| **How It Works** | 3-step visual: Write → Edit → Export |
| **Features** | Key value props with icons |
| **Social Proof** | Placeholder for testimonials / demo video |
| **Footer** | Links, copyright |

### 6.2 Story Intake

- **Input:** Multi-line text area with character count
- **Validation:** Min 100 chars, max 5000 chars
- **Guidance:** Inline tips shown below the text area
- **Action:** "Break down my story" → POST to `/api/stories` then `/api/episodes/{id}/generate-breakdown`

### 6.3 Scene Card Editor

- **Layout:** Vertical stack of draggable cards
- **Each card contains:**
  - Scene number and beat label (e.g., "Scene 3 — Escalation")
  - Visual description (editable textarea)
  - Narration/dialogue (editable textarea)
  - Tone adjustment buttons: `[More Dramatic]` `[Simpler]` `[Shorter]`
  - Delete button, merge-with-next button
- **Add scene:** Button to insert a new blank card
- **Reorder:** Drag-and-drop

### 6.4 Style & Voice Selection

- **Visual style:** Radio button grid with preview thumbnails
- **Voice:** Radio button grid with audio preview snippets
- **Duration:** Toggle between 60s and 90s
- **Music mood:** Optional selector (e.g., "Tense", "Hopeful", "Melancholy", "None")

### 6.5 Video Generation Pipeline

- **Trigger:** User clicks "Generate Episode"
- **Backend stages:**
  1. Generate per-scene image prompts from visual descriptions
  2. Generate images in parallel (Stability AI / similar)
  3. Generate voiceover audio (ElevenLabs)
  4. Compose video (Remotion): images + pan/zoom + VO + music + captions
  5. Render MP4
- **Frontend:** WebSocket progress updates showing current stage
- **Per-scene regeneration:** User can regenerate visuals or VO for individual scenes without re-rendering the whole video

### 6.6 Preview & Export

- **Preview:** In-browser 9:16 video player with play/pause/scrub
- **Export:** Direct download link for MP4
- **Script PDF:** Optional download with beat structure and narration text

---

## 7. Technical Architecture (Recommended)

### Frontend

| Choice | Rationale |
|--------|-----------|
| **Next.js 14+ (App Router)** | Server components, API routes, fast iteration |
| **Tailwind CSS** | Rapid UI development, responsive by default |
| **Shadcn/ui** | Accessible component primitives |
| **React DnD** | Drag-and-drop for scene cards |

### Backend

| Choice | Rationale |
|--------|-----------|
| **Python / FastAPI** | Async-native, great for AI orchestration |
| **PostgreSQL** | Relational data (stories, episodes, scenes) |
| **Redis + Celery** | Async job queue for generation pipeline |
| **Remotion (Node.js sidecar)** | Programmatic video composition |

### External AI Services

| Service | Use |
|---------|-----|
| **Claude (Anthropic)** | Story → scene breakdown, prompt engineering |
| **Stability AI** | Image generation from scene descriptions |
| **ElevenLabs** | Text-to-speech voiceover |
| **Remotion** | Video composition and rendering |

### Infrastructure (MVP)

- Vercel (frontend) or single VPS
- Fly.io or Railway (backend)
- S3-compatible storage for assets (R2 / S3)
- WebSocket via FastAPI for real-time progress

---

## 8. Success Criteria

### MVP Launch Criteria

- [ ] A writer can go from pasted text to downloaded MP4 in < 15 minutes
- [ ] Generated video is 9:16, 60–90 seconds, with synced VO and captions
- [ ] Scene editing is intuitive enough for a non-technical user (no onboarding needed)
- [ ] End-to-end pipeline completes without manual intervention
- [ ] Per-scene regeneration works without full re-render

### Quality Metrics

| Metric | Target |
|--------|--------|
| Story → scenes breakdown quality | Writer accepts 70%+ of scenes without edits |
| Image generation relevance | Images match scene descriptions 80%+ of the time |
| VO sync accuracy | Audio aligns with scene transitions within 0.5s |
| Export quality | 1080×1920, ≥24fps, no artifacts |
| Pipeline completion rate | ≥90% of started generations complete successfully |

---

## 9. Constraints & Assumptions

### Constraints

- **Budget:** MVP built by a small team; minimize ongoing API costs
- **AI costs:** Image generation and TTS have per-unit costs — must estimate and potentially limit free usage
- **Rendering time:** Remotion render may take 1–5 minutes per episode; user must be informed
- **Content moderation:** AI-generated content needs basic safety checks

### Assumptions

- Writers will provide stories in English (MVP — i18n deferred)
- Stories are 300–800 words; longer works need manual splitting (deferred)
- Users have modern browsers (Chrome, Firefox, Safari, Edge — last 2 versions)
- External AI APIs (Claude, Stability AI, ElevenLabs) remain available and within budget

---

## 10. Future Vision (Post-MVP)

These are documented in detail in [`Enhancements.md`](./Enhancements.md):

- **Phase 1.5 — Veo Movie Mode:** Immediately after MVP, add an AI video clip pipeline as a premium alternative to static images. Writers toggle between "Storyboard Mode" (current MVP, static images with Ken Burns) and "Movie Mode" (Veo-generated ~8-second video clips per scene with cinematic camera directions, character consistency via a character bible, and clip-based composition). See [`Backend.md` §2.5](./Backend.md#25-movie-mode--veo-video-pipeline-phase-15) for technical details.
- **Phase 2:** Collaborative writers' room, projects/series, style presets, "in the style of" editing
- **Phase 3:** Distribution integrations, marketing/analytics dashboard, monetization tools
- **Beyond:** Multi-format output (book, play, film, audio drama), team roles, IP management

---

## References

- [Genesis Document](./genesis.md) — Original workflow and platform concept evolution
- [Backend Architecture](./Backend.md) — Detailed pipeline implementation
- [Database Schemas](./Schemas.md) — Data model
- [API Documentation](./API_Documentation.md) — Endpoint specifications
- [Project Plan](./Project_plan.md) — Phased implementation plan
