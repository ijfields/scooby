# Scooby — TopView AI Evaluation

> **Started:** 2026-04-17
> **Purpose:** Decide whether TopView AI is a good fit for Scooby's video
> generation stage — either as an alternative/replacement for Remotion
> (still unbuilt) or as a pluggable animation provider alongside Kling 3.0.
> **Eval scripts:** `scripts/test_topview_image2video.py`, `scripts/test_topview_text2video.py`, `scripts/test_topview_omni_reference.py`
> **Review page builder:** `scripts/build_topview_review_page.py`
> **Raw data:** `test_generations/topview_results.csv` (local, gitignored)
> **Status:** Phase 0 partner review in progress; Seedance 2.0 eval queued
> **Partner review URL:** https://scooby-video-review.netlify.app
> **Runs:** 6 successful (3 i2v + 3 t2v) + 1 moderation block. 2 Seedance 2.0 runs pending via Omni Reference endpoint.

---

## Why Scooby is considering TopView

Scooby needs to turn a static scene image + voiceover into a short (5–10s)
vertical drama clip for each scene in a 60–90s episode. Current options:

1. **Remotion** (planned) — self-hosted Node.js compositing. Full control,
   no per-video fee, but requires adding Node to the Celery worker and
   writing a compositor.
2. **Kling 3.0 via WaveSpeed** (built, untested) — animates Scooby's
   generated image. Already in the pluggable provider registry as `kling_std`.
3. **TopView AI (this eval)** — Pro plan ($X/mo, credit-based). Offers
   Image-to-Video and Text-to-Video with a wide model catalog (Kling, Sora,
   Veo, Vidu, Seedance, Topview's own models).

The question this doc answers: **should TopView be wired into the provider
registry (and at what tier), or does its drama-genre output quality not
justify the per-scene cost?**

---

## Evaluation methodology

Two scripts drive the eval:

- **`test_topview_image2video.py <image> --model <name>`** — upload a scene
  image, animate it. This matches Scooby's default flow (image stage
  preserves scene-preview UX for non-technical writers).
- **`test_topview_text2video.py --model <name>`** — skip the image stage
  entirely, go prompt → video. A cheaper/faster path that trades away
  the scene-preview UX; potentially useful for a future "express" tier.

**Test input:**
- **Image** (i2v): `test_scene.png` — a Scooby-style vertical scene, kitchen
  at night, woman at table with letter.
- **Prompt** (t2v): the same "dimly lit apartment kitchen at night…"
  description Scooby's image stage would produce.

**What we measure per run** (auto-logged to
`test_generations/topview_results.csv`):
- Model name + display
- Generation time (seconds)
- Credits spent
- Output dimensions
- File size

**What we judge by watching each MP4:**
- Does it hold 9:16 vertical framing?
- Does it look like *drama* (cinematic, emotional) vs ad-tuned output?
- Is the motion subtle/purposeful or distracting?
- Does native audio (where available) fit the scene?

---

## Credit cost reference

From [docs.topview.ai/docs/billing-rules](https://docs.topview.ai/docs/billing-rules) —
credits shared with the topview.ai web account, tier-based.

Per-second cost so far (credits ÷ duration):

| Model | Credits/sec | Source run |
|---|---|---|
| Kling 2.6 (i2v, 5s) | 0.65 | `kling_2.6_5s.mp4` |
| Kling V3 (t2v, 5s) | 0.80 | `kling_v3_5s.mp4` |
| Vidu Q3 Pro (i2v, 8s) | 0.90 | `vidu_q3_pro_8s.mp4` |
| Sora 2 Pro (t2v, 8s) | 1.68 | `sora_2_pro_8s.mp4` |
| Sora 2 Pro (i2v, 8s) | — | **blocked by moderation** (see below) |

**Back-of-envelope for a full Scooby episode** (8 scenes × 5s each = 40s
of output):

| Model | Credits / episode | Roughly |
|---|---|---|
| Kling 2.6 | ~26 | cheap tier |
| Kling V3 | ~32 | mid tier |
| Vidu Q3 Pro | ~36 | mid tier w/ audio |
| Sora 2 Pro | ~67 | premium (t2v only — see finding below) |

Compare against TopView's Pro subscription credit allowance to compute
break-even episodes/month.

---

## Results — Image-to-Video

One row per model. Fill qualitative notes after watching each MP4.

### Kling 2.6 ✅

- **Task ID:** `b423f606ddbb40ce92c4a2fab5a2c6c5`
- **Output:** `test_generations/topview/kling_2.6_5s.mp4`
- **Dims:** 1088x1904 (true 9:16 — matches source image)
- **Duration:** 5s with native audio
- **Gen time:** 90s
- **Credits:** 3.25
- **Prompt:** "Emotional close-up, subtle breathing motion, soft light shift from warm to cool, intimate moment."

**Qualitative notes** (fill in after watching):

- [ ] Motion quality (subtle/natural vs distracting):
- [ ] Preserves character/setting from source image?
- [ ] Audio quality (if on):
- [ ] Drama aesthetic match:
- [ ] Would I ship this in an episode?

### Vidu Q3 Pro ✅

- **Task ID:** `a2626eed2afb41be9d9be4cd1bf595fb`
- **Output:** `test_generations/topview/vidu_q3_pro_8s.mp4`
- **Dims:** 724x1268 (9:16)
- **Duration:** 8s with native audio
- **Gen time:** 150s
- **Credits:** 7.2
- **Prompt:** "Slow cinematic push in, warm amber light flickers, atmospheric dust floats. Moody drama."

**Qualitative notes** (fill in after watching):

- [ ] Motion quality:
- [ ] Preserves character/setting from source image?
- [ ] Audio quality:
- [ ] Drama aesthetic vs Kling 2.6:
- [ ] 8s long enough to feel like a real scene beat?

### Sora 2 Pro ❌ (blocked by moderation)

- **Task ID:** `c2719978cca04b3aa99b63f242ba21e3`
- **Status:** `failed` after 320s polling
- **Error:** "Your request was blocked by our moderation system. credits have been refunded"

**Finding — significant for Scooby:**

Sora 2 Pro's model card states it "does not support generating realistic
humans." The same kitchen-scene prompt worked in **t2v** (where the model
interprets loosely), but **i2v** on a source image actually containing
a person's face is flagged by moderation.

**Implication:** Sora 2 Pro is effectively unusable for Scooby's default
i2v pipeline, because almost every story scene involves a character.
It remains viable for:

- **Text-to-Video mode** (proven: the t2v run succeeded)
- **Scene beats with no humans** — establishing shots, objects, locations

**Workaround if we still want Sora quality for character scenes:** use
`Sora 2 Pro` only on non-character scenes (e.g. environment establishing
shots), and a character-safe model (Kling 2.6, Vidu Q3 Pro) for the rest.
This adds routing logic to the provider registry — not worth it unless
Sora's output is *dramatically* better in the t2v comparison.

### Seedance 1.0 Pro Fast ✅

- **Task ID:** `2a499c3bd3f242d581f84fc4e5f19054`
- **Output:** `test_generations/topview/seedance_1.0_pro_fast_10s.mp4`
- **Dims:** 704x1248 (9:16)
- **Duration:** 10s, no audio
- **Gen time:** 70s (fastest of the i2v runs)
- **Credits:** 0.7 — **roughly 10× cheaper per second than Kling 2.6**
- **Prompt:** "Slow dolly in, cinematic handheld feel, warm key light drifts across the subject, film grain, moody drama."

**Headline finding:** at 0.07 credits/sec, this is dramatically cheaper
than every other model tested. For an 8-scene × 5s episode, Seedance Fast
costs ~3 credits vs Kling 2.6's ~26. If partner review finds the quality
acceptable, this changes the unit economics of Scooby's video pipeline.

**Qualitative notes** (fill in after partner review):

- [ ] Motion quality (ByteDance drama aesthetic vs Kling/Vidu):
- [ ] Preserves character/setting from source image?
- [ ] 10s feels like a usable scene beat?
- [ ] Worth making this the default with music/voiceover layered on top?

---

## Results — Text-to-Video

Same scene as a prompt, no source image.

### Kling V3 ✅

- **Task ID:** `fc36c2fff2944e9b831a95c39db40ede`
- **Output:** `test_generations/topview_t2v/kling_v3_5s.mp4`
- **Dims:** 720x1280 (9:16)
- **Duration:** 5s with native audio
- **Gen time:** 70s
- **Credits:** 4.0

**Qualitative notes:**

- [ ] Does the scene match the prompt description?
- [ ] Character/setting plausibility:
- [ ] Motion/cinematography:
- [ ] Audio quality:
- [ ] Compare vs i2v Kling 2.6 — which is more controllable?

### Sora 2 Pro ✅

- **Task ID:** `436909c50db84fb694953dad07793bf2`
- **Output:** `test_generations/topview_t2v/sora_2_pro_8s.mp4`
- **Dims:** 720x1280 (9:16)
- **Duration:** 8s, no audio
- **Gen time:** 270s (≈4.5 min — notably slower than Kling)
- **Credits:** 13.44

**Qualitative notes:**

- [ ] Scene coherence vs prompt:
- [ ] Motion realism (Sora's known strength):
- [ ] Worth ~3× Kling V3's credit cost?
- [ ] Would we ever use it for narration scenes (no audio is a limit)?

### Seedance 1.5 pro ✅

- **Task ID:** `ced9a4a7fc0f4636a41a19edbe303755`
- **Output:** `test_generations/topview_t2v/seedance_1.5_pro_8s.mp4`
- **Dims:** 720x1280 (9:16)
- **Duration:** 8s with native audio
- **Gen time:** 80s
- **Credits:** 2.0 — **cheaper and faster than Kling V3** (which cost 4.0 for 5s)

**Note:** Seedance 1.5 pro i2v requires first+last frame pair (same
constraint as Kling V3 and Veo 3.1), so it's only usable via t2v for
Scooby's single-image flow.

**Qualitative notes** (fill in after partner review):

- [ ] Scene interpretation quality:
- [ ] Audio — does Seedance generate better ambient/dialogue than Kling V3?
- [ ] 8s pacing vs 5s Kling V3:
- [ ] Strong enough to be the prompt-direct (t2v) default?

---

## Results — Omni Reference (Seedance 2.0)

**New finding post-v0.5.1:** Seedance 2.0 is accessible via TopView's
**Omni Reference** endpoint (`POST /v1/common_task/omni_reference/task/submit`)
— a completely different endpoint from the i2v/t2v endpoints we used
in the first pass. In the API, Seedance 2.0 is labeled **"Standard"** and
**"Fast"** (not "Seedance 2.0"), which is why we missed it on the first
scrape.

### Why this matters for Scooby

Omni Reference takes up to **9 reference images** and 3 reference videos
via `<<<Image1>>>`, `<<<Image2>>>` syntax in the prompt. The interesting
capability for a character-driven drama platform is **multi-image
reference** — pass a character lookbook once and keep the character
consistent across all 8 scenes of an episode.

### Seedance 2.0 Fast ⏳ (pending)

_Single-image reference test. Direct quality comparison against Kling 2.6
and Vidu Q3 Pro at similar price._

_Command:_
```
python scripts/test_topview_omni_reference.py "C:\Data\Cousin Ingrid\Git Hub\scooby\test_scene.png" --model seedance_2.0_fast
```

- Expected cost: ~4.8 credits (5s, 720p, with free audio)
- Expected dims: true 9:16 (720x1280 or similar)

**Qualitative notes** (fill in after watching):

- [ ] Quality vs Kling 2.6 at similar price point:
- [ ] Audio quality (sound is free on Seedance 2.0):
- [ ] Does `<<<Image1>>>` reference feel substantively different from
      passing the image as a first-frame anchor?

### Seedance 2.0 Standard — character consistency ⏳ (pending)

_Two-image reference: scene setting + character portrait. This is the
killer-feature test._

_Command:_
```
python scripts/test_topview_omni_reference.py "C:\Data\Cousin Ingrid\Git Hub\scooby\test_scene.png" "path/to/character.png" --model seedance_2.0_standard
```

- Expected cost: ~6 credits (5s, 720p, with free audio)
- You'll need a second image: any existing Scooby-generated character
  portrait, or a clean portrait photo

**Qualitative notes** (fill in after watching):

- [ ] Does the character in the output look like the `<<<Image2>>>` reference?
- [ ] Does the scene setting still look like `<<<Image1>>>`?
- [ ] Is the result coherent, or does mixing references produce artifacts?
- [ ] If character consistency holds up, this is the premium tier for
      full-episode generation — worth the ~48 credits/episode?

---

## Open questions

- **First & Last Frame models** (Veo 3.1, Kling V3 i2v, Seedance 1.5 pro)
  require two images — could Scooby render scene_N_end and scene_N+1_start
  as bridging frames? Worth another Phase 0 experiment if interstitial
  quality matters.
- **Per-user credit quotas** at scale — how many episodes/month fit in
  Pro plan? Need to re-read billing rules after a week of usage.
- **Latency for worker pipeline** — 90s (Kling) to 270s (Sora) per scene.
  At 8 scenes/episode, Sora alone is ~36 min/episode. Kling tier is ~12 min.
  Compare against Kling via WaveSpeed (already built).

---

## Decision matrix (filled in after all runs + manual viewing)

| Criterion | Remotion (planned) | Kling 3.0 (WaveSpeed) | TopView |
|---|---|---|---|
| Per-scene cost | ~$0 (infra only) | ? | 0.65–1.68 credits/sec |
| Setup complexity | High (Node on worker) | Low (already built) | Medium (upload flow) |
| 9:16 vertical quality | N/A (compositing only) | ? | ✅ confirmed |
| Native audio | No | No | Kling 2.6, V3 = yes |
| Drama aesthetic | N/A | ? | TBD |
| Vendor lock-in | None | Low | Medium |

---

## Recommendation (updated live)

**As of 2026-04-18 (3 i2v + 3 t2v runs complete, 1 i2v blocked):**

Phase 0 infrastructure shipped. 9:16 output is genuine 9:16 across every
working model. Per-episode credit costs range from ~3 (Seedance Fast) to
~67 (Sora 2 Pro), giving a real cost/quality ladder to choose from.

### Two headline findings

1. **Sora 2 Pro i2v is blocked by moderation** on any source image with
   a human face. Scooby's stories are character-driven, so Sora 2 Pro is
   out for the default i2v pipeline. Still viable for the t2v prompt-direct
   path and environment-only scenes.

2. **Seedance 1.0 Pro Fast is an economic outlier** at 0.07 credits/sec
   — roughly 10× cheaper than Kling 2.6. If partner review confirms the
   quality is usable (even without native audio, which we can layer on via
   ElevenLabs + music), this becomes the obvious default tier.

### Current tier recommendation (pending partner review)

| Tier | Default pipeline (i2v) | Prompt-direct mode (t2v) |
|---|---|---|
| **Budget** | Seedance Fast (~3 cr/ep) | Seedance 1.5 pro (~10 cr/ep) |
| **Mid** | Kling 2.6 (~26 cr/ep) | Kling V3 (~32 cr/ep) |
| **Premium** | Vidu Q3 Pro (~36 cr/ep) | Sora 2 Pro (~67 cr/ep) |

### Next steps

1. **Partner review** at https://scooby-video-review.netlify.app — get
   gut-feel feedback on which videos feel like drama vs marketing-ad.
2. **Fill the `[ ]` qualitative checklists** above with partner feedback
   and your own viewing notes.
3. **Commit to a Budget + Mid + Premium tier** per mode. Update the
   Decision Matrix below with the winners.
4. **Generate a comparable Kling 3.0 / WaveSpeed sample** to fairly
   compare against the current `kling_std` animation provider before
   deciding whether TopView replaces or augments it.
5. **If TopView wins any tier:** add provider registry entries to
   `backend/app/services/generation/providers.py` and expose the new
   options via `generation_tier` on the Episode model.
6. **Optional further runs** (post-partner-review, if they reveal gaps):
   - `Topview Pro` / `Topview Lite` (TopView's own models, likely
     cheapest on their side)
   - Seedance 1.5 pro on an environment-only image to confirm single-image
     bypass works for non-human scenes
   - Veo 3.1 Fast with first=end frame as a workaround — highest audio
     quality tier if it renders without weird artifacts
