# Session 003 — Workstream 1.3: Authentication (Clerk)

**Date:** 2026-03-26
**Status:** Complete

## What was done

### Frontend
- Installed `@clerk/nextjs`
- Wrapped root layout with `<ClerkProvider>`
- Created Clerk middleware (`src/middleware.ts`) — protects `/stories` and `/episodes` routes
- Created `/sign-in` and `/sign-up` pages with Clerk components
- Extracted Nav into `src/components/nav.tsx` — shows Sign In (signed out) or UserButton + My Stories (signed in)
- Created `src/lib/api.ts` — API client utility with Bearer token injection

### Backend
- Created `app/core/auth.py` — Clerk JWT verification via JWKS endpoint, caches public keys
- `get_current_clerk_user_id` dependency — extracts and verifies Clerk JWT from Authorization header
- `get_current_user` dependency — resolves Clerk ID to local User model
- Created `app/api/v1/endpoints/auth.py`:
  - `POST /api/v1/auth/sync` — creates/updates local user record from Clerk data
  - `GET /api/v1/auth/me` — returns current user
- Added `CLERK_ISSUER_URL` to Settings config
- Wired auth router into v1 router
- Updated `.env.example` with Clerk env vars

### Fixes
- Added `from __future__ import annotations` + `TYPE_CHECKING` imports to all 6 model files to fix ruff F821 errors with forward references

## Notes
- Clerk project setup (creating the application on clerk.com) is a manual step for the user
- Backend uses JWKS endpoint for key rotation support — no shared secrets needed
