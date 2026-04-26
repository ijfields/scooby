# Scooby — Enhancements & Out-of-Scope Items

> **Last updated:** 2026-04-26

Items below are explicitly out of scope for the MVP but represent the product roadmap. They are organized by phase and priority.

---

## Phase 1.5: Veo Movie Mode

> **Prerequisite:** MVP (Phase 1) ships with Storyboard Mode (static images + Ken Burns via ffmpeg). Movie Mode adds AI-generated video clips as a premium alternative.

### Generation Mode Toggle

The wizard gains a mode selector at the Style & Voice step:

| Mode | Pipeline | Output | Cost Tier |
|------|----------|--------|-----------|
| **Storyboard Mode** (default) | Stability AI / Nanobanana 2 images → ffmpeg Ken Burns composition | Static images with pan/zoom, VO, captions | Standard (included) |
| **Movie Mode** | Veo video clips → ffmpeg clip stitching | AI-generated video clips with VO overlay and captions | Premium (paid) |

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

### Clip Composition (ffmpeg)

Instead of composing static images with Ken Burns effects, ffmpeg stitches Veo clips:

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

### Alternative Generation Models

> **Research basis:** [Video Analysis — Cinematic Websites](../Video%20Analysis%20-%20This%20AI%20Agent%20Builds%2015K%20Cinematic%20Websites%20on%20Autopilot.md) — RoboNuggets agent pipeline using Nanobanana 2 + Kling 3.0 for cinematic image-to-video.

Additional generation backends to evaluate alongside Stability AI (images) and Veo (video):

| Model | Type | Access | Cost | Notes |
|-------|------|--------|------|-------|
| **Nanobanana 2** | Image generation | Google Cloud APIs | Free ($300 credits/Gmail account) | Potential Stability AI replacement for scene images; no third-party reseller needed |
| **Kling 3.0** | Image-to-video | WaveSpeed API (pay-per-use) | ~$0.05-0.10/clip | Alternative to Veo; no monthly subscription; produces cinematic animated clips from static images |
| **Nanobanana Pro** | Image generation | Google Cloud APIs | Same free credits | Higher quality variant for premium scenes |

**Nanobanana 2 + Kling 3.0 pipeline** as a Storyboard-to-Movie bridge:
1. Generate scene image with Nanobanana 2 (free)
2. Animate scene image into ~8s video clip with Kling 3.0 (~$0.05-0.10)
3. Compose animated clips with ffmpeg (existing pipeline — same compositor as Storyboard Mode)

This hybrid approach could produce more cinematic results than Ken Burns on static images, at a lower cost than full Veo generation — a potential **"Movie Lite" tier** between Storyboard and full Movie Mode.

**Scroll-frame mapping technique** (from same source): Extract individual frames from a generated video and map to scroll position for interactive preview. Could enhance the scene preview experience before final export.

---

### Script Mode (Dialogue-Driven Episodes)

> **Status:** Needs full definition — see Ideas Backlog task below.

Script Mode adds a second **content mode** alongside the existing Narrated mode. Where Narrated mode uses a single narrator voice over images/video, Script Mode features character dialogue — like the vertical drama content on ReelShort, DramaBox, and the 67+ apps documented in [Vertical Drama App Ecosystem](research/Vertical_Drama_App_Ecosystem.md).

**Content mode is independent of visual quality tier:**

|                   | Storyboard (static) | Movie Lite (animated) | Movie (full video) |
|-------------------|--------------------|-----------------------|--------------------|
| **Narrated** (VO) | Current MVP        | NB2 + Kling 3.0      | Veo                |
| **Script** (dialogue) | Images + multi-voice | Animated + multi-voice | Veo + lip-sync |

**Key systems affected (needs detailed design):**
- Claude scene breakdown prompt → dialogue with speaker labels + emotional direction
- Character Bible (shared with Movie Mode) → name, appearance, voice mapping
- Multi-voice TTS → multiple ElevenLabs voices per episode, one per character
- Caption/subtitle formatting → speaker labels, dialogue vs narration styling
- Animation prompts → character acting direction for Kling/Veo

**Dependency:** Character Bible (already designed above for Movie Mode). Script Mode and Movie Mode share this component — design together, ship independently.

---

## Phase 1.7: Freestyle Mode (Conversational Series Direction)

> **Prerequisite:** YouTube-to-Series feature (Phase 1.6) shipped.

### The Problem

The YouTube-to-Series flow is rigid: AI plans episodes, user approves or removes. But real creative direction is conversational. In practice, creators say things like "add an epilogue with the book references," "make episode 3 more about the phone call," or "use Roland's actual voice for the closer." The current UI can't handle this.

### The Solution

A chat-based interface where the creator can direct the series through natural language after the initial AI plan:

| Action | Example User Input |
|--------|-------------------|
| Add episode | "Add an epilogue with all the book recommendations" |
| Modify angle | "Make episode 3 focus more on the JFK phone call" |
| Reorder | "Move the housing episode earlier, it sets up the thesis better" |
| Swap voice | "Try a different voice on episode 4" |
| Add source audio | "Use Roland's actual voice for the closing line" |
| Regenerate asset | "The image on scene 3 is wonky, try again" |
| Remove episode | "Cut episode 5, it's redundant with episode 2" |
| Add content | "He references 14 books — can we make a reading list episode?" |

### Implementation Concept

- Chat panel alongside the series plan review UI on the story detail page
- Each message is processed by Claude with the full series plan as context
- Claude outputs structured actions (`add_episode`, `modify_episode`, `regenerate_asset`, `extract_source_audio`, etc.)
- Actions update the plan in real-time; user sees changes immediately
- Full history of creative decisions preserved as a conversation log
- Source audio extraction (from original video) available as an action type

### Why This Matters

This emerged organically during the first YouTube-to-Series test. The user conversationally added an epilogue episode, adjusted a voice, fixed a wonky image, and requested the original creator's voice for a closing hook — all actions that the approve/reject UI couldn't handle. Freestyle mode makes the creator a **producer** directing the AI, not just a reviewer accepting or rejecting a plan.

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

### B2B Content Marketplace (Drama App Ecosystem)

> **Research basis:** [Vertical Drama App Ecosystem](research/Vertical_Drama_App_Ecosystem.md) — 67+ apps identified, all licensing from the same shared content pool at ~$50K for 50-60 shows.

The vertical short drama app market has 67+ distribution apps (ReelShort, DramaBox, ShortMax, etc.) that all license the **same low-budget drama catalogs** from production companies. There is no content differentiation — every app shows the same shows. Scooby-generated episodes could break this homogeneity.

- **Writer-to-app pipeline:** Writers create original episodes on Scooby → episodes are packaged for licensing to drama apps
- **Content licensing API:** Drama apps can browse and license Scooby-created content via API or marketplace
- **Revenue share:** Platform takes a cut, writers earn royalties per view/license
- **Quality gate:** Content must pass a quality threshold (resolution, duration, audio quality) to be listed
- **Exclusivity tiers:** Writers choose non-exclusive (lower fee, wider reach) or exclusive (higher fee, single app)
- **Catalog packaging:** Bundle episodes into series/collections for bulk licensing deals
- **Price anchoring:** Drama apps currently pay ~$1,000/show (1/50th of $50K production). Scooby content at $500-800/show with the advantage of **unique, exclusive content** is a compelling value proposition

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
- Research drama content licensing companies (who supplies the 67+ apps?) — potential B2B partnership targets
- skill.md pipeline pattern: encode Scooby episode pipeline as agent-readable markdown for Claude Code CLI automation and batch processing
- Cinematic modules for frontend: accordion sliders, reveal text, kinetic text effects for richer scene preview UI
- **TODO: Flesh out Script Mode definition** — full spec for dialogue-driven episodes: Claude prompt changes, multi-voice TTS mapping, character-voice assignment UI, caption formatting for dialogue vs narration, interaction with Character Bible and each visual quality tier
