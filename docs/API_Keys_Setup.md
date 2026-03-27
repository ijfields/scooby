# API Keys Setup Guide

Everything you need to get Scooby running. Total setup time: ~20 minutes.

---

## 1. Clerk (Authentication)

**What it does:** Handles user sign-up, sign-in, and session management.

**Sign up:** https://dashboard.clerk.com/sign-up

**Steps:**
1. Create a Clerk account (free)
2. Create a new application — name it "Scooby"
3. Choose sign-in methods (Email + Google recommended)
4. Go to **API Keys** in the sidebar

**Keys you need:**

| Key | Where to find | Goes in |
|-----|---------------|---------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | API Keys → Publishable key (`pk_test_...`) | Frontend (Vercel) |
| `CLERK_SECRET_KEY` | API Keys → Secret key (`sk_test_...`) | Frontend (Vercel) |
| `CLERK_ISSUER_URL` | Sessions → Your issuer URL (`https://xxx.clerk.accounts.dev`) | Backend (Railway) |

**Also configure in Clerk dashboard:**
- Allowed redirect URLs: add your Vercel frontend URL
- Allowed origins: add your Vercel frontend URL

**Cost:** Free tier = 10,000 monthly active users. More than enough for MVP.

---

## 2. Anthropic / Claude (AI Scene Breakdown)

**What it does:** Breaks your story text into 5-7 dramatic scenes with visual descriptions and narration.

**Sign up:** https://console.anthropic.com/

**Steps:**
1. Create an Anthropic account
2. Add a payment method (required even for free credits)
3. Go to **API Keys** → Create key

**Key you need:**

| Key | Format | Goes in |
|-----|--------|---------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` | Backend (Railway) |

**Cost:**
- Free credit: $5 on sign-up
- Per scene breakdown: ~$0.01-0.03 (uses Claude 3.5 Sonnet)
- **~$0.02 per episode** on average
- Pay-as-you-go after free credit

---

## 3. Stability AI (Image Generation)

**What it does:** Generates scene images from visual descriptions using SDXL.

**Sign up:** https://platform.stability.ai/

**Steps:**
1. Create a Stability AI account
2. Go to **API Keys** → Create API key
3. Check your credit balance under Billing

**Key you need:**

| Key | Format | Goes in |
|-----|--------|---------|
| `STABILITY_API_KEY` | `sk-...` | Backend (Railway) |

**Cost:**
- Free credit: 25 credits on sign-up (~400 images)
- Per image: ~$0.03-0.06 (SDXL 1024x1024)
- **~$0.18-0.36 per episode** (6 scenes) — this is the biggest cost
- $10 = ~160 images = ~26 episodes

---

## 4. ElevenLabs (Voice / TTS)

**What it does:** Generates narration voiceovers from scene text.

**Sign up:** https://elevenlabs.io/

**Steps:**
1. Create an ElevenLabs account
2. Go to **Profile + API Key** (click your avatar → Profile)
3. Copy your API key

**Key you need:**

| Key | Format | Goes in |
|-----|--------|---------|
| `ELEVENLABS_API_KEY` | 32-character hex string | Backend (Railway) |

**Cost:**
- Free tier: 10,000 characters/month (~3-4 episodes)
- Starter plan ($5/mo): 30,000 chars/month (~10-12 episodes)
- **~$0.06-0.18 per episode** on paid plan
- Each scene narration is typically 50-150 characters

---

## 5. S3-Compatible Storage (Optional for MVP)

**What it does:** Stores generated images, audio, and video files permanently. Currently files are stored on the server's temp directory — S3 is needed for production persistence.

**Recommended:** Cloudflare R2 (cheaper, no egress fees)

**Sign up:** https://dash.cloudflare.com/ → R2 Object Storage

**Steps (Cloudflare R2):**
1. Create a Cloudflare account
2. Go to R2 → Create bucket → name it `scooby-assets`
3. Go to R2 → Manage R2 API Tokens → Create API token
4. Copy the Access Key ID and Secret Access Key

**Keys you need:**

| Key | Example | Goes in |
|-----|---------|---------|
| `S3_ENDPOINT_URL` | `https://<account-id>.r2.cloudflarestorage.com` | Backend (Railway) |
| `S3_ACCESS_KEY_ID` | From R2 API token | Backend (Railway) |
| `S3_SECRET_ACCESS_KEY` | From R2 API token | Backend (Railway) |
| `S3_BUCKET_NAME` | `scooby-assets` | Backend (Railway) |
| `S3_PUBLIC_URL` | Your R2 public URL or custom domain | Backend (Railway) |

**Cost:** R2 free tier = 10GB storage + 10M reads/month. Plenty for MVP.

**Note:** S3 storage is NOT required for local development or initial testing. The app falls back to local temp files.

---

## Cost Summary

| Service | Per Episode | Monthly (50 episodes) | Free Tier |
|---------|------------|----------------------|-----------|
| Clerk | $0 | $0 | 10K users |
| Claude | ~$0.02 | ~$1 | $5 credit |
| Stability AI | ~$0.27 | ~$13.50 | 25 credits |
| ElevenLabs | ~$0.12 | ~$6 | 10K chars |
| R2 Storage | ~$0.001 | ~$0.05 | 10GB free |
| **Total** | **~$0.41** | **~$20.55** | |

**To get started for free:** Sign up for all services, use free tiers. You can generate ~10-15 episodes before needing to pay anything.

---

## Where to Set Keys

### Railway (Backend)
```bash
cd "C:\data\cousin ingrid\git hub\scooby"
railway service backend
railway variables --set 'ANTHROPIC_API_KEY=sk-ant-...'
railway variables --set 'STABILITY_API_KEY=sk-...'
railway variables --set 'ELEVENLABS_API_KEY=...'
railway variables --set 'CLERK_ISSUER_URL=https://xxx.clerk.accounts.dev'
```

Or use the Railway dashboard: https://railway.com → scooby → backend → Variables

### Vercel (Frontend)
Go to https://vercel.com → frontend → Settings → Environment Variables:
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` = `pk_test_...`
- `CLERK_SECRET_KEY` = `sk_test_...`
- `NEXT_PUBLIC_API_URL` = `https://backend-production-67a9.up.railway.app`

After adding, redeploy: Vercel dashboard → Deployments → Redeploy

---

## Quick Checklist

- [ ] Clerk account created, app configured
- [ ] `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` set in Vercel
- [ ] `CLERK_SECRET_KEY` set in Vercel
- [ ] `CLERK_ISSUER_URL` set in Railway
- [ ] Anthropic account created
- [ ] `ANTHROPIC_API_KEY` set in Railway
- [ ] Stability AI account created
- [ ] `STABILITY_API_KEY` set in Railway
- [ ] ElevenLabs account created
- [ ] `ELEVENLABS_API_KEY` set in Railway
- [ ] (Optional) R2 bucket created and S3 vars set in Railway
