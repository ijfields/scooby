# Scooby — Product Requirements Document (PRD)

> **Codename:** Scooby
> **Version:** 0.2
> **Last updated:** 2026-03-31

---

## 1. Product Vision

**Scooby** is a "Canva for stories" — a multi-use web platform that transforms content into finished 60–90 second vertical drama videos (9:16 format for TikTok, Reels, and Shorts). Creators can paste original story text *or* import a YouTube video URL, and AI handles the rest: breaking content into scenes, generating imagery, voiceover, and assembled video. No editing software, no prompt engineering, no production skills required.

### Elevator Pitch

> Writers have stories. Creators have videos. Neither has a production team. Scooby turns written stories *or* YouTube videos into a series of vertical drama episodes — no AI expertise, no video editing, just your content reimagined on screen.

### Two Input Paths, One Output

| Input Path | Source | What AI Does | Output |
|-----------|--------|-------------|--------|
| **Write a Story** | Paste 300-800 words of original text | Breaks into 5-7 dramatic beats | 1 episode (60-90s vertical video) |
| **Import from YouTube** | Paste a YouTube URL | Fetches transcript, plans a multi-episode series, breaks each episode into beats | 3-8 episodes (a complete series) |

Both paths produce the same high-quality output: AI-generated imagery, narrated voiceover, animated captions, and assembled MP4. The difference is that YouTube import creates a *series* of standalone visual stories from a single source.

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

### Secondary Persona: The Content Repurposer

| Attribute | Detail |
|-----------|--------|
| **Who** | YouTubers, podcasters, educators, commentators |
| **Has** | Existing long-form video content (10-60+ minutes) |
| **Wants** | To repurpose their content into short-form vertical video for TikTok/Reels/Shorts |
| **Lacks** | Time to manually clip, edit, and produce short-form content from each video |
| **Motivation** | Reach new audiences, maximize content ROI, grow across platforms |

### Tertiary Personas (Post-MVP)

- Poets, diarists, bloggers experimenting with visual storytelling
- Writing teachers and coaches creating demo content
- Screenwriters prototyping micro-drama concepts
- Small creative teams collaborating on series

---

## 4. MVP Scope

**Two input paths. One beautiful output.**

### What's IN the MVP

- Story text input (paste or type) — original content path
- **YouTube URL import** — content repurposing path
- **AI series planner** — breaks long-form video into 3-8 standalone episode outlines
- AI-powered scene breakdown into 5–7 beat cards (per episode)
- Card-based scene editing (no timeline, no keyframes)
- Style and voice preset selection
- AI video generation (images + VO + composition)
- Preview player with per-scene regeneration
- MP4 export (1080×1920, 9:16)
- Optional script PDF export

### What's explicitly NOT in the MVP

- Collaborators, comments, or team roles
- Analytics, distribution integrations, or marketing tools
- Complex timeline editing
- Voice-to-text story input (dictation) — deferred to Phase 1.5
- Importing from non-YouTube sources (podcasts, articles) — deferred

---

## 5. User Flow

### Flow A: Write a Story (Original Content)

```
Landing Page (Hero + CTA)
    │
    ▼
[1] Story Intake (tab: "Write a Story")
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
    │   - Visual style preset (3–4 options)
    │   - Narration voice (3–4 options)
    ▼
[4] Generation & Preview
    │   - Progress indicator with stage labels
    │   - Preview player (9:16 in-browser)
    │   - Per-scene controls:
    │     "Regenerate visuals", "Regenerate VO"
    ▼
[5] Export
        - Download MP4 (1080×1920)
        - Optional: Download script PDF
        - Share link
```

### Flow B: Import from YouTube (Content Repurposing)

```
Landing Page (Hero + CTA)
    │
    ▼
[1] YouTube Import (tab: "Import from YouTube")
    │   - Paste YouTube URL
    │   - Fair use acknowledgment checkbox
    │   - "Import & Plan Series" button
    ▼
[2] Transcript Extraction (automatic)
    │   - Progress: "Fetching transcript..."
    │   - Shows video metadata (title, channel, duration)
    ▼
[3] Series Plan Review
    │   - AI presents 3-8 episode outlines:
    │     Each with title, angle/thesis, key content
    │   - Creator can edit titles, remove unwanted episodes,
    │     reorder, or adjust angles
    │   - "Approve & Generate Series" button
    ▼
[4] Per-Episode Breakdown (parallel)
    │   - Each approved episode goes through the standard
    │     scene breakdown → scene editor → style → generate flow
    │   - Progress shown for all episodes
    ▼
[5] Series Preview & Export
        - Preview each episode individually
        - Download individual MP4s
        - Share individual episodes or the series
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

**Tab: Write a Story**
- **Input:** Multi-line text area with character count
- **Validation:** Min 100 chars, max 5000 chars
- **Guidance:** Inline tips shown below the text area
- **Action:** "Break down my story" → POST to `/api/stories` then `/api/episodes/{id}/generate-breakdown`

**Tab: Import from YouTube**
- **Input:** YouTube URL field with format validation
- **Fair use:** Checkbox — "I confirm I have the right to create derivative content from this video"
- **Action:** "Import & Plan Series" → POST to `/api/youtube/import`
- **Feedback:** Progress stepper showing transcript fetch → series planning → review

### 6.2.1 AI Series Planner (YouTube Import)

The series planner is the core differentiator from clip-based tools. It:
- Analyzes the full video transcript for argument structure, themes, and narrative arc
- Plans 3-8 standalone episodes, each with a unique angle and dramatic structure
- Ensures each episode is self-contained (watchable without seeing others)
- Allocates relevant transcript excerpts to each episode
- Suggests a viewing order that builds toward the overall thesis

### 6.2.2 Competitive Differentiation

| Tool | Approach | Output | Limitation |
|------|----------|--------|------------|
| **Opus Clip** | Algorithmic "viral moment" detection | Clips from original footage | No narrative arc, just slicing |
| **CapCut** | Manual timeline editing with AI assists | Edited video | Requires editing skills |
| **Descript** | Edit video by editing transcript | Modified original footage | Still the original footage |
| **Scooby** | AI reimagines content as visual storytelling | Series of new visual stories | Transformative, not derivative |

Scooby doesn't clip the original video. It *reimagines* the content as a series of standalone visual stories with AI-generated imagery, rewritten narration, and dramatic beat structure.

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

## 6.7 Content Ethics & Attribution

Scooby creates transformative content — AI-generated imagery and rewritten narration, not clips from the original video. But credit and ethics are foundational to the platform's integrity.

### Attribution Requirements

Every episode generated from a YouTube import must carry attribution:

| Where | What's Shown |
|-------|-------------|
| **Episode metadata** (stored in DB) | Original video title, channel name, YouTube URL, import date |
| **Preview page** | "Based on [Video Title] by [Channel Name]" with link to original |
| **Generated video** | End card: "Based on content by [Channel Name]" + original URL |
| **Share link** | Attribution visible to anyone viewing the shared preview |
| **Downloaded MP4** | End card burned into the last 3 seconds of the video |

Attribution is **automatic and non-removable** for YouTube-sourced content. Original story content (Write a Story path) does not carry attribution.

### Fair Use & Consent Framework

| Use Case | Legal Basis | Platform Guidance |
|----------|------------|-------------------|
| Creator imports their **own** YouTube content | Full rights — no issue | Best case. Future: "Verify your channel" feature |
| Commentary, education, or criticism of public content | Fair use (transformative) | Good case. Scooby's output is inherently transformative |
| Repurposing someone else's content for monetization | Requires permission | Gray area. UX should nudge toward getting permission |

### Import Flow Safeguards

1. **Fair use acknowledgment** (required checkbox): "I confirm that I am the creator of this content, have permission from the creator, or my use qualifies as fair use (commentary, education, criticism)"
2. **Relationship selector**: "What is your relationship to this content?" — options: "I created this video", "I have permission from the creator", "Fair use (commentary/education/criticism)"
3. **Acknowledgment timestamp** stored on the import record
4. **Creator opt-out**: DMCA-style takedown request process for creators who don't want their content reimagined

### Terms of Service Requirements

- Users are responsible for ensuring they have the legal right to create derivative works
- Scooby provides the tool; the user assumes responsibility for the legal basis of their use
- Scooby will comply with takedown requests from original content creators
- Generated content must retain attribution — removing it violates ToS

### Future: Creator Verification (Phase 2+)

- YouTubers verify channel ownership via OAuth
- Verified creators get a "Verified Source" badge on their series
- Verified imports skip the fair use acknowledgment (they own the content)
- Opens the door to creator partnerships and premium features

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
- **Phase 1.6 — More Input Sources:** Podcast RSS import, article/blog URL import, uploaded transcript files — expanding the "Canva with multi-use" model beyond YouTube
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
