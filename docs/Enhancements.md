# Scooby — Enhancements & Out-of-Scope Items

> **Last updated:** 2026-03-25

Items below are explicitly out of scope for the MVP but represent the product roadmap. They are organized by phase and priority.

---

## Phase 1.5: Veo Movie Mode

> **Prerequisite:** MVP (Phase 1) ships with Storyboard Mode (static images + Ken Burns). Movie Mode adds AI-generated video clips as a premium alternative.

### Generation Mode Toggle

The wizard gains a mode selector at the Style & Voice step:

| Mode | Pipeline | Output | Cost Tier |
|------|----------|--------|-----------|
| **Storyboard Mode** (default) | Stability AI images → Remotion Ken Burns composition | Static images with pan/zoom, VO, captions | Standard (included) |
| **Movie Mode** | Veo video clips → Remotion clip stitching | AI-generated video clips with VO overlay and captions | Premium (paid) |

### Character Bible

Before scene generation, the writer describes their main characters once:

- **Name**, **appearance** (physical description, clothing, distinguishing features), **voice/personality notes**
- Stored per-story and embedded into every Veo prompt to maintain visual consistency across scenes
- Characters are referenced by name in scene descriptions; the system expands each reference into the full character description before sending to Veo
- MVP character bible supports up to 4 characters per story

### Cinematic Script Generation (Claude)

In Movie Mode, the Claude breakdown prompt changes to produce a **cinematic script** instead of a narration + visual description pair:

| Field | Storyboard Mode | Movie Mode |
|-------|-----------------|------------|
| `visual_description` | Static scene description for image generation | **Camera direction** — shot type, movement, framing (e.g., "Close-up, slow dolly in on Maria's face as she reads the letter") |
| `narration` | Voiceover narration text | Voiceover narration text (same) |
| `dialogue` | *(not present)* | **On-screen dialogue** — character lines with speaker labels, emotional direction |
| `character_refs` | *(not present)* | **Character references** — list of character bible entries appearing in this scene |

### Veo Video Clip Generation

Each scene's cinematic script is sent to the **Gemini / Veo API** for video generation:

- **Model:** Veo 2 (or latest available) via Google's Generative AI API
- **Output:** ~8-second video clip per scene, 1080×1920 (9:16 vertical)
- **Prompt construction:** Combines camera direction + character descriptions from bible + scene context + style preset
- **Consistency:** Character bible descriptions are prepended to every prompt; style preset keywords (e.g., "cinematic dark", "warm indie film") are appended
- **Retry logic:** If a clip fails content safety filters, auto-retry with softened prompt (up to 2 retries)
- **Storage:** Generated clips stored in S3-compatible storage alongside image assets

### Clip Composition (Remotion)

Instead of composing static images with Ken Burns effects, Remotion stitches Veo clips:

- **Input:** Ordered list of ~8-second video clips + VO audio + caption data
- **Transitions:** Crossfade (default), cut, or dip-to-black between clips
- **VO overlay:** Narration audio mixed over clip audio (clip audio ducked or muted based on user preference)
- **Captions:** Same caption overlay system as Storyboard Mode
- **Output:** Single MP4, 1080×1920, 60–90 seconds

### Cost & Pricing Implications

| Item | Estimated Cost | Notes |
|------|---------------|-------|
| Veo clip generation | ~$0.10–0.50 per 8s clip | Pricing TBD based on Google API rates at launch |
| 6 scenes × 1 clip each | ~$0.60–3.00 per episode | vs. ~$0.06–0.12 for Stability AI images |
| Per-scene regeneration | Same per-clip cost | User can regenerate individual clips |

Movie Mode is positioned as a **premium feature** — free tier gets Storyboard Mode, paid tier unlocks Movie Mode. Exact pricing determined after API cost stabilization.

---

## Phase 2: Collaborative Writers' Room

### Projects & Series Management
- **Series structure:** Group episodes into series with seasons and episode ordering
- **Character bible:** Shared character profiles (name, description, visual reference, voice) reused across episodes
- **World bible:** Setting descriptions, rules, tone guides that persist across a series
- **Continuity tracker:** Flag inconsistencies in character behavior or plot across episodes

### Shared Workspace
- **Invite collaborators:** Share a project via email invite or link
- **Role-based access:**
  - *Writer* — create and edit story text and scenes
  - *Editor* — suggest edits, leave comments, approve changes
  - *Producer* — manage style settings, trigger generation, export
  - *Viewer* — read-only access to preview and download
- **Real-time collaboration:** Multiple users editing scenes simultaneously (CRDTs or OT)
- **Comments & annotations:** Per-scene comment threads, @mentions, resolution tracking

### Advanced Style & Editing
- **"In the style of" editing:** AI-assisted tone transformation — e.g., "Rewrite this scene in the style of Hitchcock suspense" or "Make this more literary"
- **Custom style presets:** Users create and save their own visual/voice/music configurations
- **Style preset marketplace:** Share or sell custom presets to other users
- **Version history:** Full edit history per scene with diff view and rollback
- **A/B scene variants:** Generate multiple versions of a scene, compare side by side

### Enhanced Scene Editor
- **Timeline view:** Optional timeline alongside card view for precise timing control
- **Transition editor:** Choose transition types between scenes (crossfade, cut, wipe, etc.)
- **Sound design:** Per-scene ambient sound effects (rain, traffic, heartbeat, etc.)
- **Caption styling:** Custom font, size, color, animation for on-screen text

---

## Phase 3: Distribution, Marketing & Analytics

### Platform Publishing
- **Direct publish:** Push finished episodes to TikTok, YouTube Shorts, Instagram Reels, Snapchat Spotlight
- **Scheduling:** Schedule episode releases across platforms
- **Platform-specific optimization:** Auto-adjust captions, safe zones, and metadata per platform
- **Batch publishing:** Publish entire series across platforms in one action

### Story Analytics
- **Episode metrics:** View count, completion rate, drop-off points, average watch time
- **Audience insights:** Demographics, peak engagement times, geographic breakdown
- **Content analysis:** Which hooks retain viewers, which beat types get the most replays
- **Series tracking:** Episode-over-episode growth, subscriber conversion
- **A/B testing:** Test different hooks, thumbnails, or endings for the same story

### Marketing Tools
- **Auto-thumbnails:** AI-generated thumbnails from climax scene
- **Title & hashtag generator:** AI-suggested titles, descriptions, and hashtags per platform
- **Trailer generator:** Auto-cut a 15-second teaser from the episode
- **Shareable link pages:** Custom landing page per episode with embedded player

### Monetization
- **Premium content:** Gate episodes behind pay-per-view or subscription
- **Crowdfunding integration:** "Fund my next episode" campaigns
- **Licensing toolkit:** Package stories for licensing to studios or platforms
- **Ad integration:** Optional mid-roll or pre-roll ad placement for creators
- **Revenue dashboard:** Track earnings across platforms and monetization methods

---

## Beyond Phase 3: Multi-Format & Platform Expansion

### Multi-Format Output
- **Vertical drama series** (current MVP format)
- **Audio drama / podcast:** Same story, narrated with sound design, no video
- **Illustrated storybook:** Scene images + narration as a digital book (PDF or ePub)
- **Stage play script:** Reformatted for live performance with stage directions
- **Screenplay format:** Industry-standard screenplay from the same story
- **Pitch deck:** Auto-generate a pitch deck for the story concept (for studio pitches)
- **Interactive fiction:** Branching narrative version for web/app

### Advanced AI Features
- **Voice cloning:** Writers can clone their own voice for narration (with consent + safety checks)
- **Style transfer:** Apply the visual style of one episode to another
- **AI co-writer:** Interactive story development — AI suggests plot twists, dialogue options, pacing improvements
- **Auto-scoring:** AI composes original background music tailored to the scene mood

### Team & Enterprise
- **Organization accounts:** Multi-team workspaces with billing
- **Writers' room mode:** Real-time brainstorming with AI facilitation
- **Production pipeline:** Kanban board for tracking episodes through: writing → editing → production → review → publish
- **Asset library:** Shared library of images, music, voices across an organization
- **White-label:** Custom-branded version for studios or writing programs

### Community & Discovery
- **Public profile:** Writer profiles with published episode portfolio
- **Discovery feed:** Browse and watch episodes from other creators
- **Remix / adapt:** Fork another creator's story structure (with permission) and create your own version
- **Writing challenges:** Platform-hosted writing prompts and competitions
- **Feedback marketplace:** Request and give feedback on draft episodes

---

## Ideas Backlog (Unscoped)

These are raw ideas captured for future evaluation:

- Voice-to-story: speak your story aloud, AI transcribes and structures it
- AR/VR preview: preview your vertical drama in spatial format
- Merchandise generation: auto-create story-themed merch (posters, book covers)
- Story graph visualization: see your story's emotional arc as a graph
- Integration with writing tools (Scrivener, Google Docs, Notion)
- Accessibility: audio descriptions, sign language overlay generation
- Localization: auto-translate and generate episodes in multiple languages
- Story templates: pre-built story structures for common genres (romance, thriller, horror, comedy)
- Episode analytics heatmap: frame-by-frame engagement overlay
