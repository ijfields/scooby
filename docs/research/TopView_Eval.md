# Scooby — TopView AI Evaluation

> **Started:** 2026-04-17
> **Purpose:** Decide whether TopView AI is a good fit for Scooby's video
> generation stage — either as an alternative/replacement for Remotion
> (still unbuilt) or as a pluggable animation provider alongside Kling 3.0.
> **Eval scripts:** `scripts/test_topview_image2video.py`, `scripts/test_topview_text2video.py`
> **Raw data:** `test_generations/topview_results.csv` (local, gitignored)
> **Status:** In progress

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
  entirely, go prompt → video. Relevant for the future Freestyle Mode
  (see [Enhancements.md](../Enhancements.md)).

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

- **Freestyle / Text2Video mode** (proven: the t2v run succeeded)
- **Scene beats with no humans** — establishing shots, objects, locations

**Workaround if we still want Sora quality for character scenes:** use
`Sora 2 Pro` only on non-character scenes (e.g. environment establishing
shots), and a character-safe model (Kling 2.6, Vidu Q3 Pro) for the rest.
This adds routing logic to the provider registry — not worth it unless
Sora's output is *dramatically* better in the t2v comparison.

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

**As of 2026-04-18 (3 i2v + 2 t2v runs done — 1 blocked):**

Infra all works: upload, submit, poll, credit tracking. 9:16 output is
genuine 9:16 across all working models. Credit costs (~26–36 per episode
for viable models) are in an acceptable range for an indie platform.

**The Sora 2 Pro moderation block is the headline finding.** Scooby's
value prop is character-driven drama, so any model that rejects realistic
humans on i2v is a non-starter for the default pipeline. This narrows
the practical shortlist for Scooby to:

- **Kling 2.6** (cheap tier, audio, 5/10s) — leading candidate
- **Vidu Q3 Pro** (mid tier, audio, 1-16s) — flexible duration is a plus
- **Kling V3 t2v** (for Freestyle Mode, not default flow)

**Next steps:**

1. Watch the 4 viable MP4s side-by-side, fill in the `[ ]` notes above.
2. Based on qualitative review, pick the winner between Kling 2.6 and
   Vidu Q3 Pro for the default i2v tier.
3. Update the Decision Matrix below with observations vs Kling 3.0
   WaveSpeed (already built — need to generate a comparable sample).
4. Decide: **integrate TopView as a provider?** If yes, add
   `topview_kling_2_6` and `topview_vidu_q3_pro` entries to
   `app/services/generation/providers.py` and expose via
   `generation_tier` (standard / enhanced).
5. **Optional further runs:** try `Topview Pro` or `Topview Lite` (their
   own models, potentially cheapest), or re-test Sora 2 Pro i2v on a
   non-human scene (pure environment) to confirm the moderation trigger
   is specifically the human face.
