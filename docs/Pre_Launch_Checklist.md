# Scooby — Pre-Launch Reliability & Cost Checklist

> **Last updated:** 2026-04-30
> **Status:** scoping doc — none of these are built yet

Four infra items worth doing before opening the platform to public users. Each is independently shippable; ranked by impact-vs-effort below. Effort estimates assume one focused day = ~6 hours of coding.

## Priority order (recommended)

| # | Item | Effort | Impact | Trigger |
|---|------|--------|--------|---------|
| 1 | Production Clerk keys | 2 hours | High — required for public launch | Before announcing publicly |
| 2 | Provider failover | 1-2 days | High — both Stability + Google AI Studio failed today | Before adding more users (already bitten by this twice in one day) |
| 3 | Cost-tracking per episode | 1 day | Medium — informs the self-host vs aggregator decision | Before any provider-migration decision |
| 4 | Observability (Sentry) | 1 day | Medium — catches silent failures | Before there's >1 paying user |

---

## 1. Production Clerk keys

**Why this is small but blocking.** You're on Clerk's `harmless-reindeer-82.clerk.accounts.dev` — that's a dev instance, intended for testing. Public users on a dev instance get unprofessional experience: dev branding in OAuth flows, shorter session lifetimes, lower limits, and Clerk reserves the right to throttle. No code change needed; this is purely Clerk dashboard work + 4 env-var swaps.

### Steps

1. **Clerk dashboard:** create a new "Production" instance for Scooby. Connect a custom domain (e.g., `auth.scooby.app` or whatever the production domain is).
2. **Configure OAuth providers:** re-add Google login (and any others) on the production instance. Each one needs a fresh OAuth client credential from Google Cloud Console pointing at the new Clerk callback URL.
3. **JWT template:** if there's a custom template on the dev instance, port it over to production.
4. **Session settings:** set production-appropriate session lengths and refresh policies.
5. **Swap Railway env vars:**
   - Backend: `CLERK_ISSUER_URL` (new prod URL), `CLERK_SECRET_KEY` (new `sk_live_...`)
   - Frontend: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (new `pk_live_...`), `CLERK_SECRET_KEY` (same new `sk_live_...`)
6. **Verify:** Ingrid + Joyce log in once each, check that the existing user records still match (clerk_id is the join key — but production clerk_ids will be **different from dev clerk_ids**). This is the hidden risk.

### Hidden risk: existing users

Production Clerk gives users **new clerk_ids**. The current DB has Ingrid as `user_3BZgEhYBLCcSITRozeViQGmV7tq` (dev). After migration she'll log in with a new `user_4xyz...` (prod). The backend won't find her record by `clerk_id` and will auto-create a new empty user — meaning **all her existing stories and episodes will be orphaned** unless we explicitly migrate.

Two ways to handle:

- **(A) Migrate before announcing:** for each user, look up the production clerk_id via Clerk's user-list API matched on email, then UPDATE the existing user row with the new clerk_id. ~30 lines of script. Safe. Recommended.
- **(B) Wipe and start over:** just nuke the dev user records and have everyone re-create. Simple but you lose Joyce's "Heart for Fun" episode and Ingrid's drafts.

### Acceptance criteria

- Clerk production instance live with custom domain
- Both `pk_live_` and `sk_live_` keys set on Railway
- Both existing users can log in and see their own stories/episodes
- No `*.clerk.accounts.dev` references anywhere in production env
- Decision documented (do we migrate dev clerk_ids → prod, or start fresh?)

### What this doesn't include

Custom email templates, custom-branded login pages, magic-link auth — all available on Clerk Pro tier but not blocking for MVP launch.

---

## 2. Provider failover

**Why this matters now.** Today alone, Stability AI returned a 429 mid-generation, then Google AI Studio returned 429 RESOURCE_EXHAUSTED, then we spent half an hour switching `IMAGE_PROVIDER` env vars on Railway by hand and re-deploying twice. With actual users on the system, that's an outage. Failover lets the second provider catch what the first drops, no human in the loop.

### Design

The provider registry at [backend/app/services/image/providers.py](backend/app/services/image/providers.py) already has 5 providers registered. Wrap `get_image_provider()` (or add a new `get_image_provider_chain()`) with a fallback chain configured per env var. On 429 / 5xx / TimeoutError, try the next provider in the chain. Log which provider succeeded so the cost-tracking work later (see #3) can attribute correctly.

### Suggested chain for production today

```
IMAGE_PROVIDER_CHAIN=topview_nano_banana_2,topview_imagen_4,stability
```

- Primary: TopView NB2 (cheap, currently active)
- First fallback: TopView Imagen 4 (different upstream model, same TopView account — covers TopView model-specific outages)
- Last resort: Stability AI (fully different vendor + billing — survives if TopView itself is down)

`nanobanana2` (Google direct) deliberately not in the chain because its credit pool is depleted; would just add latency before failing.

### Things to handle carefully

- **Rate-limit vs deterministic-error distinction.** A 400 ("invalid prompt") shouldn't trigger fallback — same prompt will fail on the next provider too, and we'd waste credits. Only retry on 429, 5xx, network errors, timeouts.
- **Per-attempt cost.** A failed attempt may still cost partial credits (depends on provider). The cost-tracking work (#3) needs to record attempts not just successful renders.
- **Circuit breaker (optional but worth considering):** if a provider fails 3 times in a row, skip it for the next 5 minutes. Otherwise we burn time + cost on a known-broken provider.

Apply the same pattern to **animation providers** (`backend/app/services/video/animation_providers/`) once that's exercised — Kling and TopView Seedance have been built but neither has had a real failure mode tested.

### Acceptance criteria

- Backend reads `IMAGE_PROVIDER_CHAIN` (comma-separated). If unset, falls back to `IMAGE_PROVIDER` (single) for backward compat.
- Image-gen task tries each provider in order, only falling through on transient errors.
- The actual provider that succeeded is logged on the `VideoAsset.metadata_["provider"]` field (already partially populated; just make sure failover-resolved provider name lands here, not the chain head).
- Unit test with mocked providers: chain `[fail, fail, succeed]` returns the third provider's image; chain `[fail, fail, fail]` raises.
- Test deployed and a deliberate failure (e.g., bad TopView key) verifies the fallback to Stability works.

### What this doesn't include

Failover for **non-AI** services (Postgres, Redis, ElevenLabs voice, Clerk auth) — those have their own resilience patterns and aren't blocking.

---

## 3. Cost-tracking per episode

**Why this matters before any infra migration.** Every architectural decision from here ("self-host Flux at ~100 daily users", "negotiate ElevenLabs at ~$1K/mo") needs actual cost numbers per episode broken down by stage. Today the data exists scattered across provider responses (`VideoAsset.metadata_["cost"]` partially) but isn't queryable. A single SQL view + a small admin endpoint solves it.

### Schema additions

One new column on `video_assets`:

```sql
ALTER TABLE video_assets ADD COLUMN cost_credits NUMERIC(8, 4);
```

(Already partially there as `metadata_["cost"]` JSON; promoting to a typed column makes per-episode aggregation trivial.) The `metadata_["provider"]` field stays — it tells you which provider was actually used (post-failover).

### Provider instrumentation

Each provider's `generate()` method already returns bytes; broaden the return shape to also return cost + provider info, OR have the caller record from a side-channel. Cleanest: provider returns a small `dict{bytes, cost_credits, provider_name, latency_ms}` instead of raw bytes. ~40 line change touching each of the 5 providers.

For TopView, cost comes back in the `result.costCredit` field of the query response (see `topview.py:_poll`). For Stability, the response header `Stability-Credits-Used` carries it. NB2 direct: there's no per-call cost from Google, but we can use the published rate × call count. Same for ElevenLabs (rate × character count).

### Read API + dashboard

```
GET /api/v1/admin/episodes/{id}/cost
→ {
    "episode_id": "...",
    "total_cost_credits": 6.4,
    "by_stage": {
      "image": 2.4,    // 6 scenes × 0.40 NB2/1K
      "voiceover": 0.6, // 6 narrations × ElevenLabs rate
      "animation": 3.6  // 6 Seedance clips × 0.6 cr each (if Movie Lite)
    },
    "by_provider": {
      "topview_nano_banana_2": 2.4,
      "elevenlabs_george": 0.6,
      "topview_seedance_1.5_pro": 3.6
    },
    "rough_usd": 0.64,  // credits * average $/credit conversion
  }
```

Admin endpoint = guarded by user `plan='admin'` or env-flag for the two existing user accounts.

### Acceptance criteria

- New `cost_credits` column populated by every successful image / animation / voiceover task (existing assets stay null — backfill optional)
- Per-episode cost endpoint returns a breakdown by stage and provider
- Light admin page at `/admin/episodes/{id}/cost` (or just JSON for now) shows the breakdown
- Sanity-check against three episodes: numbers within 10% of reality based on TopView dashboard / Stability dashboard / ElevenLabs dashboard

### What this doesn't include

User-facing pricing display, usage limits / quotas, billing — those are paid-tier features. This is **internal observability** only.

---

## 4. Observability (Sentry or Axiom)

**Why this matters.** Today's two 429 incidents both surfaced because Ingrid happened to be sitting at the screen. With public users, silent failures mean unhappy users who churn without saying anything. We need an alert when a Celery task fails or when the error rate on any endpoint spikes.

### Pick one: Sentry vs Axiom

**Recommendation: Sentry, free tier.** 5K events/month is plenty at current scale, free, and the error-tracking UX is good. Axiom is better at structured logs but worse at error grouping; Sentry's primary product is exactly what we need.

| | Sentry | Axiom |
|---|---|---|
| Strength | Error tracking, stack traces, alert routing | Structured logs, queries, dashboards |
| Free tier | 5K events/mo | 0.5 GB ingest/mo |
| Python SDK | Mature | Functional |
| Best fit for Scooby | ✓ — we want errors first | Fine, but secondary |

### What to instrument

**Backend (FastAPI + Celery):**
- FastAPI middleware — catches 5xx automatically
- Celery task instrumentation — catches task failures (right now we silently swallow some, like the orchestrator's bare `except Exception` blocks)
- Manual `capture_exception` calls in the provider failover paths (we want to know when fallbacks fire even though the user-facing request succeeded)

**Frontend (Next.js):**
- Auto-instrument `<ErrorBoundary>` for uncaught React errors
- Auto-instrument fetch failures
- One env var (`SENTRY_DSN`) to enable

### Alerts

Two to start:

1. **Any Celery task failure** → email + Slack (if you have Slack — otherwise just email)
2. **Error rate on `POST /api/v1/episodes/{id}/generate` over 10% in 5 min window** → email + Slack
3. **Optional:** alert when an episode has been in `'generating'` status for >30 min (catches the stuck-job class of bug we hit today)

### Acceptance criteria

- Sentry account + project for Scooby created
- `SENTRY_DSN` env var set on backend, worker, and frontend (separate DSNs per service for clean error grouping)
- Test exception thrown in dev shows up in Sentry within 30s
- Two alerts configured + delivery verified
- README mentions Sentry as the error/alert tracking system

### What this doesn't include

User-session replay, performance monitoring (APM), structured business metrics (signups, churn) — those are different tools (PostHog, Mixpanel) and not blocking.

---

## What I'd actually build first

If I had a free week, in order: **Clerk prod (2h)** → **Provider failover (1.5d)** → **Sentry (1d)** → **Cost-tracking (1d)**. Total ~5 working days.

The Clerk migration is small but blocking — every other item assumes you have public users. Provider failover is the highest-leverage reliability work — it would have prevented both of today's outages outright. Sentry is a force multiplier for the rest because it surfaces problems that are otherwise invisible. Cost-tracking is the one I'd defer last because it informs decisions you don't have to make until volume picks up.
