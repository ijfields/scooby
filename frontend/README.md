# Scooby — Frontend

Next.js 16 App Router frontend for the Scooby story-to-video platform.

For project-wide setup, see the [root README](../README.md). For deployment, see [DEPLOY.md](../DEPLOY.md).

## Local development

```bash
npm install
npm run dev    # → http://localhost:3001 (port 3000 is usually occupied)
```

The dev server expects the backend at `http://localhost:8000`. Set `NEXT_PUBLIC_API_URL` in `.env.local` to point elsewhere.

## Important: Next.js 16 conventions

This project uses **Next.js 16**, which has breaking changes from earlier versions you may know. APIs, conventions, and file structure may differ from training data. Read the relevant guide in `node_modules/next/dist/docs/` before changing anything significant. Heed deprecation notices.

## Auth

Authentication is via Clerk. Required env vars:

- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` — publishable (client-safe) key
- `CLERK_SECRET_KEY` — secret key, used server-side by Next.js middleware
- `NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in`
- `NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up`

User identity flows: Clerk JWT → backend `get_current_user` → user record keyed on `clerk_id`. The backend separately fetches the real email/name/avatar from Clerk's Backend API (see [backend/app/core/auth.py](../backend/app/core/auth.py)).

## Linting / typechecking

```bash
npm run lint          # ESLint
npx tsc --noEmit      # Type check (matches CI)
```
