# How to Create Long AI Videos Step-by-Step (Topview Agent V2) — Complete Transcript Analysis

**Stream Title:** How to Create Long AI Videos Step-by-Step (Topview Agent V2)
**Date:** 2026-04-10
**Duration:** ~6:56 (416 seconds)
**Speaker:** Shafin Tech
**Channel:** Shafin Tech
**Video ID:** opamjXFm16g
**Upload Date:** 2026-04-10
**Platform:** YouTube
**Source URL:** https://www.youtube.com/watch?v=opamjXFm16g

---

## EXECUTIVE SUMMARY

A 7-minute walkthrough by the Shafin Tech channel demonstrating TopView's
**Agent V2** — a web-UI product layered on top of their Seedance 2.0 and
Seedance 2.0 Fast video models. The core claim is that Agent V2 makes
**long-form AI video creation practical** by combining a multi-scene
storyboard planner, per-scene prompt editing, a queued generation pipeline,
a clip-extension feature, and automatic concatenation into a single
long-form output — all inside one tool with no external editor needed.

The video is framed as a step-by-step how-to for creators, but from
Scooby's perspective it's a **product-teardown of a direct competitor's
orchestration layer**. Every capability shown (idea → multi-scene plan →
per-scene generation → long-form assembly) is what Scooby is already
building — Agent V2 is what Scooby could look like if we wrapped the
Claude scene-breakdown + provider-registry pipeline in a first-class
creator UI. The video does **not** reveal a new API endpoint or an
"infinite duration" model; the long-form effect is achieved through
orchestration of standard 4–15s generation calls, which is the approach
Scooby already uses.

---

## TIMESTAMPED SEGMENTS WITH DESCRIPTIONS

### 00:00 – 01:23 | Hook + Value Proposition

**Focus:** Establish that the entire demo video was itself made with the
tool being demonstrated.

- Opens with "This entire video you're watching was created using AI" —
  multi-scene, consistent visuals, no editing software.
- Frames the **biggest limitation of AI video tools**: short clips
  forcing manual stitching, inconsistent visuals, broken storytelling,
  messy workflow.
- Positions Agent V2 (powered by SeaDance 2.0 / SeaDance 2.0 Fast) as
  **built specifically for long-form video creation** — "think in full
  scenes and structured stories."
- **Key quote:** "Everything happens in one place."
- Sets up the step-by-step that follows (steps 1–7).

### 01:23 – 01:55 | Step 1 — Getting Started

**Focus:** Project entry point and — critically — a version toggle.

- User opens the TopView dashboard and clicks **"Start from scratch."**
- **Critical UI step:** select "Video Agent V2" at the top of the
  project. Missing this step = no access to the multi-scene workflow.
- Implication: V2 is a **separate mode/product** from TopView's
  legacy per-clip generator, not just a new model option.
- Once V2 is selected, the user is in the multi-scene flow.

### 01:55 – 03:10 | Step 2 — Writing Your Prompt + Reference Assets + Model Settings

**Focus:** Prompt construction and per-project settings.

- Users do **not need a full script** — just an idea. Example shown:
  "a cinematic underwater documentary with a smooth camera starting
  above the ocean, transitioning underwater into a coral reef with
  realistic lighting, fish movement, and a calm immersive atmosphere."
- **Reference asset upload is first-class** — images or videos can be
  uploaded to lock in style, specific characters, or visual look.
- Presenter uses an image generated with **Nano Banana Pro** as a
  reference. (Note: this is the same image-generation family Scooby
  already supports via the `nanobanana2` provider.)
- **Model settings panel:**
  - **Model:** Standard (uses SeaDance 2.0) or Fast (SeaDance 2.0 Fast)
  - **Mode:** standard or fast
  - **Aspect ratio:** 16:9 shown (vertical 9:16 presumably available)
  - **Duration:** per-scene setting
- Hit "Generate" to submit.

### 03:10 – 03:48 | Step 3 — Communicating with the Agent

**Focus:** The agent does not generate video immediately — it first
produces a plan for the user to refine.

- After clicking Generate, the system **creates a structured plan**
  before making any video.
- The plan **breaks the idea into multiple scenes with detailed
  descriptions** — essentially an AI-generated storyboard.
- **Interaction is conversational**: users can ask the agent to improve
  visual style, adjust actions, smooth transitions.
- **Key quote:** "This process feels less like using a tool and more
  like working with a creative assistant that helps shape your video
  step by step."
- This is **functionally identical to Scooby's YouTube-to-Series
  planner step** (Claude breaks a source story into multiple episodes/
  scenes, user approves/edits the plan before generation).

### 03:48 – 04:22 | Step 4 — Multi-Scene Workflow

**Focus:** The scene-list view where individual scene prompts can be
edited before generation.

- Scenes displayed in a **multi-scene view** — visible list/grid.
- Each scene has its **own prompt and duration**, individually editable.
- **"Enhanced" feature** — automatically improves prompts by adding
  cinematic detail: camera movement, shot composition. (This is a
  prompt-rewriter layer, similar to the upscaler/enhancer patterns in
  Midjourney and DALL-E prompts.)
- **Extensibility:** users can add more scenes to extend the story —
  "making it possible to create videos of almost any length."
- Again, the pattern maps directly onto Scooby's per-scene editing on
  the story-detail page.

### 04:22 – 04:44 | Step 5 — Generate Video Clips

**Focus:** Batch generation across the scene list.

- Clicking generate starts the full pipeline: platform **creates multiple
  clips based on your scenes, processing them one by one in the queue.**
- User does not manage timelines or switch tools — all orchestration
  happens inside TopView.
- Implicit efficiency claim vs "traditional workflows" (presumably
  CapCut/Premiere + separate AI tools).
- From API perspective: this is a **task queue** — likely the same
  Omni Reference / i2v / t2v endpoints called sequentially per scene,
  possibly with `boardId` grouping them as a project.

### 04:44 – 05:07 | Step 6 — Extend Clips to Build Longer Videos

**Focus:** The "extend" feature — the closest thing the UI has to
"long-form in one call."

- User can **add a new prompt describing how a scene should continue**
  and the AI generates an extension that "blends naturally with the
  original clip."
- **Key mechanism:** this is almost certainly the last frame of clip N
  being fed as the first frame of clip N+1 in a first-last-frame model
  (or scene-to-scene reference via Omni Reference's video-input feature).
- Framed as the way to gradually build longer and more detailed videos
  — confirming that **long-form is achieved through orchestration, not
  a single long call.**

### 05:07 – 05:31 | Step 7 — Combine into One Long-Form Video

**Focus:** Automatic concatenation.

- Once all clips are ready, the user can **combine them into a single
  long-form video** from within the UI.
- Platform "automatically arranges everything in sequence, creating a
  smooth and continuous flow."
- **Key quote:** "When you play it back, it feels like one cohesive
  video rather than a collection of separate clips."
- Technically this is standard MP4 concatenation (ffmpeg-equivalent).
  TopView likely serves the combined file as a single download.

### 05:31 – 06:08 | Use Cases + Honest Opinion

**Focus:** Positioning — where this tool fits in the creator's workflow.

- Use cases listed: **YouTube storytelling, marketing videos, product
  demos, educational content, social media.**
- No specific mention of vertical drama (Scooby's wedge) — the
  positioning is horizontal, workflow-focused.
- **Presenter's honest opinion:** "This is one of the first AI tools
  that actually makes long-form video creation practical." The
  **biggest advantage is the workflow** — idea to final output in one
  place; multi-scene system makes videos feel structured and
  professional.

### 06:08 – 06:56 | Main Tip + Sales Outro

**Focus:** Prompt quality advice and subscription pitch.

- **Main tip:** "Be as detailed as possible with your prompts — that
  directly impacts the quality of your results." Standard advice but
  consistent with what we saw in our eval (vague prompts produced
  generic motion; specific cinematic prompts produced better results).
- Sales: **Business annual plan** — 365 days of unlimited SeaDance 2.0
  and SeaDance 2.0 Fast usage.
- Closing CTA: like, subscribe, next video.

---

## COMPREHENSIVE SUMMARY — 12 KEY BULLET POINTS

1. **Agent V2 is a web-UI orchestration layer, not a new API endpoint.**
   Everything shown (storyboard planning, multi-scene queue, clip
   extension, auto-concat) is a UI wrapper around the same 4–15s
   per-call generation primitives exposed by the TopView API. There is
   no "infinite duration" model hiding in here.
2. **Seedance 2.0 + Seedance 2.0 Fast are the underlying models** —
   confirmed in the video as "SeaDance 2.0" (phonetic transcription)
   and cross-referenced in the API docs as `Standard` / `Fast` on the
   Omni Reference endpoint (`/v1/common_task/omni_reference/task/submit`).
3. **The "Select Video Agent V2" UI toggle is a separate mode** from
   legacy TopView — implying TopView runs two product surfaces in
   parallel (classic per-clip generator vs Agent V2 multi-scene
   orchestrator).
4. **Prompt → structured plan → user refines → generate** is the core
   UX pattern. This is **identical to Scooby's YouTube-to-Series flow**
   (Claude generates episode plan, user approves, generator runs).
   Scooby has no product differentiation on this step alone.
5. **Reference asset upload is built into the prompt stage** — images
   OR videos, used for "consistent style, specific characters, visual
   look." This maps to the Omni Reference endpoint's `<<<ImageN>>>` /
   `<<<VideoN>>>` syntax we discovered during the Seedance 2.0 eval gap.
6. **"Enhanced" is a prompt-rewriter feature** that auto-adds cinematic
   detail (camera movement, shot composition). Scooby could easily add
   this as a Claude-based preprocessor on scene prompts before sending
   to the image/video provider — low-effort win for quality uplift.
7. **Per-scene prompt + duration editing** is the core multi-scene view.
   Scooby's scene preview UX already supports per-scene prompt editing;
   duration control is worth adding to the Episode model if variable
   clip lengths improve pacing.
8. **"Extend clip" is first-last-frame chaining or video-reference
   continuity** — not a magic longer-call API. Scooby could implement
   the same pattern by passing scene N's final frame as the first
   frame of scene N+1 (for first-last-frame models like Seedance 1.5
   pro or Veo 3.1) or as `<<<Video1>>>` via Omni Reference.
9. **Auto-concat of clips is a standard MP4 join** (ffmpeg-equivalent).
   This is what Remotion or a simple ffmpeg step in Scooby's Celery
   worker would do. Nothing proprietary.
10. **Use case positioning is horizontal (YouTube, marketing, demos,
    education)** — TopView does NOT specifically target vertical drama.
    Scooby's wedge (drama for non-technical writers, character-driven
    stories) remains uncontested.
11. **Sales model is per-year subscription** with "unlimited" Seedance
    2.0 usage on the business plan — suggests TopView is optimizing
    for high-volume creator accounts, not per-API-call pricing.
12. **Presenter's own workflow:** uses Nano Banana Pro to generate
    reference images first, then feeds them to Agent V2. This is
    **exactly Scooby's "image first, animate second" flow** —
    Shafin's workflow validates our architectural choice.

---

## TOOLS & TECHNOLOGIES USED

### AI Video Generation
- **TopView Agent V2** — web-UI product for multi-scene long-form video
  creation. Not directly exposed as a single API endpoint.
- **SeaDance 2.0 (Standard)** — underlying premium video model.
- **SeaDance 2.0 Fast** — underlying fast-tier video model. Free
  native audio on both.

### Reference Image Generation
- **Nano Banana Pro** — used by presenter to create reference images
  before uploading to Agent V2. (Scooby already supports this family
  as the `nanobanana2` image provider.)

### Platform / Workflow
- **TopView Dashboard** — project entry point.
- **Multi-scene view / storyboard** — per-scene prompt editor.
- **Queue processor** — batch generation across scenes.
- **Extend clip + auto-concat** — long-form assembly pipeline.

---

## KEY PROMPTS USED

### Prompt #1: Scene Idea (Top-Level Prompt to the Agent)

**Context:** 02:10 (roughly) — Step 2, Writing Your Prompt.
**Exact Prompt (Via Text):**
> "A cinematic underwater documentary with a smooth camera starting
> above the ocean, transitioning underwater into a coral reef with
> realistic lighting, fish movement, and a calm immersive atmosphere."

**Result:** The agent generates a **structured multi-scene plan** —
not a video — which the user then refines scene-by-scene. This is
consumed by the "Communicating with the agent" step.

---

## CRITICAL INSIGHTS

### Competitive Framing for Scooby

TopView Agent V2 is the **closest existing product to what Scooby is
building**, but the overlap is at the orchestration/UX layer, not on
the underlying video generation. Observations:

| Dimension | TopView Agent V2 | Scooby |
|---|---|---|
| Input | Single prompt / idea | Story text OR YouTube URL |
| Planner | "Agent creates structured plan" (opaque) | Claude-driven scene/episode breakdown (auditable) |
| Refinement | Conversational chat with agent | Direct editing of scene fields |
| Reference assets | Images + videos, prompt-bound via UI | Images (generated by Nanobanana / Stability), currently 1:1 scene binding |
| Model | SeaDance 2.0 / Fast only | Pluggable provider registry (Stability, Nanobanana, Kling, now TopView) |
| Target user | General creators (YouTube, marketing, edu) | Non-technical fiction writers |
| Vertical drama wedge | No explicit positioning | Core differentiation |
| Ownership model | SaaS subscription, TopView's UI | Scooby owns the orchestration, writers own the stories |

### What Scooby Should Steal (low cost, high value)

1. **Prompt-enhancement preprocessor** (the "Enhanced" toggle). Add a
   Claude-powered step that takes a user's terse scene description and
   rewrites it with explicit camera direction, lighting, and shot type
   before sending to the video provider. ~1 day of work.
2. **Per-scene duration control.** Right now Scooby likely has a default
   clip duration; exposing it per scene lets writers pace dramatic beats
   (shorter for quick cuts, longer for emotional holds).
3. **Clip-extension path** using first-last-frame chaining on models
   that support it (Seedance 1.5 pro, Veo 3.1, Kling V3). Bridge
   scene N's ending frame into scene N+1's starting frame for smooth
   transitions. Already architecturally supported by the pluggable
   provider registry — just needs scheduling logic.

### What Scooby Should NOT Copy

- **General-purpose positioning.** TopView's "works for anything"
  framing is wide but shallow — they can't beat a specialist tool for
  any one use case. Scooby's vertical-drama wedge should sharpen, not
  soften.
- **Opaque agent planner.** Scooby shows the writer every step of the
  scene breakdown and lets them edit directly. TopView's black-box
  "communicate with the agent" chat feels magical in a demo but would
  frustrate a writer who wants precise control over their own story.

### Next Steps for Our TopView Eval

Given this analysis, the original Seedance 2.0 Omni Reference eval
(scripts/test_topview_omni_reference.py, committed but not yet run)
becomes **more important, not less.** Specifically:

- **Run the two pending Omni Reference tests** — Seedance 2.0 Fast
  (single-image) and Seedance 2.0 Standard (two-image character
  consistency). These test the actual underlying models that Agent V2
  exposes; if the output quality is strong, Scooby can integrate them
  as premium-tier providers and build our own orchestration on top.
- **Do NOT spend effort reverse-engineering Agent V2's UI** — it is a
  wrapper around the same primitives Scooby already orchestrates.
- **Consider the "Enhanced" prompt-rewriter** as a concrete follow-up
  task independent of the TopView decision.

---

*Analysis compiled from ~7-minute Shafin Tech walkthrough video,
focused on extracting competitive-positioning signal and API/UX
patterns relevant to Scooby's platform architecture.*
