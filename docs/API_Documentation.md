# Scooby — API Documentation

**Version:** 0.1 (MVP)
**Date:** 2026-03-25
**Base URL:** `/api/v1`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Standard Error Response](#standard-error-response)
4. [HTTP Status Codes](#http-status-codes)
5. [Endpoints](#endpoints)
   - [Auth](#1-auth)
   - [Stories](#2-stories)
   - [Episodes](#3-episodes)
   - [Scenes / Beats](#4-scenes--beats)
   - [Style Presets](#5-style-presets)
   - [Video Generation Pipeline](#6-video-generation-pipeline)
   - [WebSocket: Generation Progress](#7-websocket-generation-progress)
   - [Export / Download](#8-export--download)

---

## Overview

Scooby is a "Canva for stories" web application that enables non-technical writers to transform raw story text into finished 60-90 second vertical drama videos (9:16 aspect ratio).

**Tech Stack:**

| Layer | Technology |
|---|---|
| Frontend | Next.js 14+ |
| Backend | Python / FastAPI |
| Database | PostgreSQL |
| Task Queue | Redis / Celery |
| Video Rendering | Remotion |
| AI Text Processing | Claude API (Anthropic) |
| Image Generation | Stability AI |
| Voice Synthesis | ElevenLabs |

**Database Tables:** `users`, `stories`, `style_presets`, `episodes`, `scenes`, `video_assets`, `generation_jobs`

All entity IDs are **UUIDs** (v4).

---

## Authentication

All API requests (except where noted) require a valid **Clerk JWT** token in the `Authorization` header.

```
Authorization: Bearer <clerk_jwt_token>
```

Tokens are issued by Clerk on the frontend and validated by the FastAPI backend on every request. Unauthenticated requests receive a `401 Unauthorized` response.

---

## Standard Error Response

All errors follow a consistent JSON envelope:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

| Field | Type | Description |
|---|---|---|
| `error.code` | `string` | Machine-readable error code (e.g., `"validation_error"`, `"not_found"`) |
| `error.message` | `string` | Human-readable description of the error |
| `error.details` | `object` | Optional additional context (field-level validation errors, etc.) |

**Example:**

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request body failed validation.",
    "details": {
      "fields": {
        "title": "Title must be between 1 and 200 characters.",
        "raw_text": "This field is required."
      }
    }
  }
}
```

---

## HTTP Status Codes

| Code | Meaning | Usage |
|---|---|---|
| `200` | OK | Successful GET, PATCH, or DELETE request |
| `201` | Created | Successful POST that creates a new resource |
| `400` | Bad Request | Malformed request syntax or invalid parameters |
| `401` | Unauthorized | Missing or invalid authentication token |
| `403` | Forbidden | Authenticated user lacks permission for this resource |
| `404` | Not Found | Resource does not exist |
| `409` | Conflict | Request conflicts with current state (e.g., duplicate creation, generation already in progress) |
| `422` | Unprocessable Entity | Request body is well-formed but contains semantic validation errors |
| `500` | Internal Server Error | Unexpected server-side failure |

---

## Endpoints

---

### 1. Auth

Base path: `/api/v1/auth`

---

#### `GET /auth/me`

Returns the profile of the currently authenticated user.

**Request:**

| Component | Value |
|---|---|
| Method | `GET` |
| Path | `/api/v1/auth/me` |
| Headers | `Authorization: Bearer <token>` |
| Body | _None_ |

**Response: `200 OK`**

```json
{
  "id": "b7e2c1a0-4d3f-4e8b-9a1c-5f6d7e8a9b0c",
  "clerk_id": "user_2nXKp9qR5tLmYvWz",
  "email": "maya.johnson@example.com",
  "display_name": "Maya Johnson",
  "avatar_url": "https://img.clerk.com/avatars/maya-johnson.jpg",
  "plan": "free",
  "credits_remaining": 10,
  "created_at": "2026-03-10T14:30:00Z",
  "updated_at": "2026-03-25T09:15:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `404` | `user_not_found` | Clerk user exists but local DB record has not been synced yet |

---

#### `POST /auth/sync`

Synchronizes the Clerk user record into the local database. Called automatically on first login from the frontend.

**Request:**

| Component | Value |
|---|---|
| Method | `POST` |
| Path | `/api/v1/auth/sync` |
| Headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |

**Request Body:**

```json
{
  "clerk_id": "user_2nXKp9qR5tLmYvWz",
  "email": "maya.johnson@example.com",
  "display_name": "Maya Johnson",
  "avatar_url": "https://img.clerk.com/avatars/maya-johnson.jpg"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `clerk_id` | `string` | Yes | Clerk user ID |
| `email` | `string` | Yes | User email address |
| `display_name` | `string` | No | User display name |
| `avatar_url` | `string` | No | URL to user avatar image |

**Response: `201 Created`** (first sync) or **`200 OK`** (subsequent syncs)

```json
{
  "id": "b7e2c1a0-4d3f-4e8b-9a1c-5f6d7e8a9b0c",
  "clerk_id": "user_2nXKp9qR5tLmYvWz",
  "email": "maya.johnson@example.com",
  "display_name": "Maya Johnson",
  "avatar_url": "https://img.clerk.com/avatars/maya-johnson.jpg",
  "plan": "free",
  "credits_remaining": 10,
  "created_at": "2026-03-10T14:30:00Z",
  "updated_at": "2026-03-25T09:15:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `422` | `validation_error` | Required fields missing or invalid |

---

### 2. Stories

Base path: `/api/v1/stories`

---

#### `POST /stories`

Create a new story from raw text.

**Request:**

| Component | Value |
|---|---|
| Method | `POST` |
| Path | `/api/v1/stories` |
| Headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |

**Request Body:**

```json
{
  "title": "The Last Lighthouse Keeper",
  "raw_text": "Margaret had kept the lighthouse running for forty years. The night the storm took the power grid down, she climbed the spiral stairs one last time, oil lamp in hand. The ships in the harbor needed her. They always had.\n\nShe didn't know that tonight, one of those ships carried her estranged daughter home."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `string` | Yes | Story title (1-200 characters) |
| `raw_text` | `string` | Yes | Raw story text (1-50,000 characters) |

**Response: `201 Created`**

```json
{
  "id": "a3f1b2c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c",
  "user_id": "b7e2c1a0-4d3f-4e8b-9a1c-5f6d7e8a9b0c",
  "title": "The Last Lighthouse Keeper",
  "raw_text": "Margaret had kept the lighthouse running for forty years. The night the storm took the power grid down, she climbed the spiral stairs one last time, oil lamp in hand. The ships in the harbor needed her. They always had.\n\nShe didn't know that tonight, one of those ships carried her estranged daughter home.",
  "word_count": 58,
  "status": "draft",
  "created_at": "2026-03-25T10:00:00Z",
  "updated_at": "2026-03-25T10:00:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `422` | `validation_error` | Title or raw_text fails validation constraints |

---

#### `GET /stories`

List all stories belonging to the authenticated user. Results are paginated.

**Request:**

| Component | Value |
|---|---|
| Method | `GET` |
| Path | `/api/v1/stories` |
| Headers | `Authorization: Bearer <token>` |

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | `integer` | `1` | Page number (1-indexed) |
| `per_page` | `integer` | `20` | Items per page (max 100) |
| `sort` | `string` | `updated_at` | Sort field: `created_at`, `updated_at`, `title` |
| `order` | `string` | `desc` | Sort order: `asc`, `desc` |
| `status` | `string` | _all_ | Filter by status: `draft`, `processing`, `completed` |

**Example:** `GET /api/v1/stories?page=1&per_page=10&sort=updated_at&order=desc`

**Response: `200 OK`**

```json
{
  "data": [
    {
      "id": "a3f1b2c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c",
      "user_id": "b7e2c1a0-4d3f-4e8b-9a1c-5f6d7e8a9b0c",
      "title": "The Last Lighthouse Keeper",
      "raw_text": "Margaret had kept the lighthouse running for forty years...",
      "word_count": 58,
      "status": "draft",
      "episode_count": 1,
      "created_at": "2026-03-25T10:00:00Z",
      "updated_at": "2026-03-25T10:30:00Z"
    },
    {
      "id": "c8d9e0f1-2a3b-4c5d-6e7f-8a9b0c1d2e3f",
      "user_id": "b7e2c1a0-4d3f-4e8b-9a1c-5f6d7e8a9b0c",
      "title": "Midnight in the Garden District",
      "raw_text": "The jazz funeral procession turned the corner onto Prytania Street...",
      "word_count": 312,
      "status": "completed",
      "episode_count": 3,
      "created_at": "2026-03-20T08:00:00Z",
      "updated_at": "2026-03-24T16:45:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_items": 2,
    "total_pages": 1
  }
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `400` | `invalid_parameter` | Invalid query parameter value |

---

#### `GET /stories/:id`

Retrieve a single story by ID.

**Request:**

| Component | Value |
|---|---|
| Method | `GET` |
| Path | `/api/v1/stories/:id` |
| Headers | `Authorization: Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | `UUID` | Story ID |

**Example:** `GET /api/v1/stories/a3f1b2c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c`

**Response: `200 OK`**

```json
{
  "id": "a3f1b2c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c",
  "user_id": "b7e2c1a0-4d3f-4e8b-9a1c-5f6d7e8a9b0c",
  "title": "The Last Lighthouse Keeper",
  "raw_text": "Margaret had kept the lighthouse running for forty years. The night the storm took the power grid down, she climbed the spiral stairs one last time, oil lamp in hand. The ships in the harbor needed her. They always had.\n\nShe didn't know that tonight, one of those ships carried her estranged daughter home.",
  "word_count": 58,
  "status": "draft",
  "episode_count": 1,
  "episodes": [
    {
      "id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
      "episode_number": 1,
      "title": "Episode 1",
      "status": "draft",
      "target_duration_sec": 75
    }
  ],
  "created_at": "2026-03-25T10:00:00Z",
  "updated_at": "2026-03-25T10:30:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this story |
| `404` | `not_found` | Story with this ID does not exist |

---

#### `PATCH /stories/:id`

Update an existing story's title or raw text.

**Request:**

| Component | Value |
|---|---|
| Method | `PATCH` |
| Path | `/api/v1/stories/:id` |
| Headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | `UUID` | Story ID |

**Request Body** (all fields optional):

```json
{
  "title": "The Last Lighthouse Keeper — Revised",
  "raw_text": "Margaret had kept the lighthouse running for forty years. The night the storm took the power grid down, she climbed the spiral stairs one last time, oil lamp in hand. The ships in the harbor needed her. They always had.\n\nShe didn't know that tonight, one of those ships carried her estranged daughter home. And her daughter didn't come alone."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `string` | No | Updated title (1-200 characters) |
| `raw_text` | `string` | No | Updated raw story text (1-50,000 characters) |

**Response: `200 OK`**

```json
{
  "id": "a3f1b2c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c",
  "user_id": "b7e2c1a0-4d3f-4e8b-9a1c-5f6d7e8a9b0c",
  "title": "The Last Lighthouse Keeper — Revised",
  "raw_text": "Margaret had kept the lighthouse running for forty years. The night the storm took the power grid down, she climbed the spiral stairs one last time, oil lamp in hand. The ships in the harbor needed her. They always had.\n\nShe didn't know that tonight, one of those ships carried her estranged daughter home. And her daughter didn't come alone.",
  "word_count": 64,
  "status": "draft",
  "created_at": "2026-03-25T10:00:00Z",
  "updated_at": "2026-03-25T11:00:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this story |
| `404` | `not_found` | Story with this ID does not exist |
| `422` | `validation_error` | Field value fails validation constraints |

---

#### `DELETE /stories/:id`

Delete a story and all associated episodes, scenes, and assets.

**Request:**

| Component | Value |
|---|---|
| Method | `DELETE` |
| Path | `/api/v1/stories/:id` |
| Headers | `Authorization: Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | `UUID` | Story ID |

**Response: `200 OK`**

```json
{
  "message": "Story deleted successfully.",
  "id": "a3f1b2c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this story |
| `404` | `not_found` | Story with this ID does not exist |

---

### 3. Episodes

Base path: `/api/v1/stories/:story_id/episodes` (collection) and `/api/v1/episodes/:id` (individual)

---

#### `POST /stories/:story_id/episodes`

Create a new episode within a story. An episode represents a single 60-90 second video segment.

**Request:**

| Component | Value |
|---|---|
| Method | `POST` |
| Path | `/api/v1/stories/:story_id/episodes` |
| Headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `story_id` | `UUID` | Parent story ID |

**Request Body:**

```json
{
  "title": "The Storm",
  "target_duration_sec": 75,
  "text_selection": {
    "start_char": 0,
    "end_char": 220
  },
  "style_preset_ids": {
    "visual": "e1f2a3b4-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
    "voice": "f2a3b4c5-6d7e-8f9a-0b1c-2d3e4f5a6b7c",
    "music": "a3b4c5d6-7e8f-9a0b-1c2d-3e4f5a6b7c8d"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `string` | No | Episode title (auto-generated if omitted) |
| `target_duration_sec` | `integer` | Yes | Target video duration in seconds (60-90) |
| `text_selection` | `object` | No | Character range from the story's raw_text to use for this episode. If omitted, the full raw_text is used. |
| `text_selection.start_char` | `integer` | Yes (if `text_selection` provided) | Start character index (inclusive) |
| `text_selection.end_char` | `integer` | Yes (if `text_selection` provided) | End character index (exclusive) |
| `style_preset_ids` | `object` | No | Style preset IDs by category |
| `style_preset_ids.visual` | `UUID` | No | Visual style preset ID |
| `style_preset_ids.voice` | `UUID` | No | Voice style preset ID |
| `style_preset_ids.music` | `UUID` | No | Music style preset ID |

**Response: `201 Created`**

```json
{
  "id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "story_id": "a3f1b2c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c",
  "episode_number": 1,
  "title": "The Storm",
  "target_duration_sec": 75,
  "text_selection": {
    "start_char": 0,
    "end_char": 220
  },
  "style_presets": {
    "visual": {
      "id": "e1f2a3b4-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
      "name": "Cinematic Noir",
      "category": "visual"
    },
    "voice": {
      "id": "f2a3b4c5-6d7e-8f9a-0b1c-2d3e4f5a6b7c",
      "name": "Deep Narrator",
      "category": "voice"
    },
    "music": {
      "id": "a3b4c5d6-7e8f-9a0b-1c2d-3e4f5a6b7c8d",
      "name": "Ambient Tension",
      "category": "music"
    }
  },
  "status": "draft",
  "scene_count": 0,
  "created_at": "2026-03-25T10:05:00Z",
  "updated_at": "2026-03-25T10:05:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own the parent story |
| `404` | `not_found` | Story with this ID does not exist |
| `422` | `validation_error` | Invalid duration range, invalid text_selection bounds, or invalid style preset IDs |

---

#### `GET /stories/:story_id/episodes`

List all episodes for a given story.

**Request:**

| Component | Value |
|---|---|
| Method | `GET` |
| Path | `/api/v1/stories/:story_id/episodes` |
| Headers | `Authorization: Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `story_id` | `UUID` | Parent story ID |

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | `integer` | `1` | Page number |
| `per_page` | `integer` | `20` | Items per page (max 100) |

**Response: `200 OK`**

```json
{
  "data": [
    {
      "id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
      "story_id": "a3f1b2c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c",
      "episode_number": 1,
      "title": "The Storm",
      "target_duration_sec": 75,
      "status": "draft",
      "scene_count": 6,
      "created_at": "2026-03-25T10:05:00Z",
      "updated_at": "2026-03-25T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 1,
    "total_pages": 1
  }
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own the parent story |
| `404` | `not_found` | Story with this ID does not exist |

---

#### `GET /episodes/:id`

Retrieve a single episode with its full scene list.

**Request:**

| Component | Value |
|---|---|
| Method | `GET` |
| Path | `/api/v1/episodes/:id` |
| Headers | `Authorization: Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | `UUID` | Episode ID |

**Response: `200 OK`**

```json
{
  "id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "story_id": "a3f1b2c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c",
  "episode_number": 1,
  "title": "The Storm",
  "target_duration_sec": 75,
  "text_selection": {
    "start_char": 0,
    "end_char": 220
  },
  "style_presets": {
    "visual": {
      "id": "e1f2a3b4-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
      "name": "Cinematic Noir",
      "category": "visual"
    },
    "voice": {
      "id": "f2a3b4c5-6d7e-8f9a-0b1c-2d3e4f5a6b7c",
      "name": "Deep Narrator",
      "category": "voice"
    },
    "music": {
      "id": "a3b4c5d6-7e8f-9a0b-1c2d-3e4f5a6b7c8d",
      "name": "Ambient Tension",
      "category": "music"
    }
  },
  "status": "scenes_ready",
  "scenes": [
    {
      "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "scene_number": 1,
      "narration_text": "Margaret had kept the lighthouse running for forty years.",
      "image_prompt": "An elderly woman with weathered hands stands inside a lighthouse lantern room, golden light from the lens illuminating her face, dramatic chiaroscuro lighting, cinematic noir style",
      "duration_sec": 12.5,
      "status": "ready"
    },
    {
      "id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
      "scene_number": 2,
      "narration_text": "The night the storm took the power grid down, she climbed the spiral stairs one last time, oil lamp in hand.",
      "image_prompt": "A dark spiral staircase inside a lighthouse, an elderly woman ascending with a glowing oil lamp casting long shadows on stone walls, rain visible through a small window, cinematic noir style",
      "duration_sec": 15.0,
      "status": "ready"
    },
    {
      "id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
      "scene_number": 3,
      "narration_text": "The ships in the harbor needed her.",
      "image_prompt": "Ships with dimly lit windows rocking in a stormy harbor at night, waves crashing against the pier, a distant lighthouse beam cutting through rain, cinematic noir style",
      "duration_sec": 8.0,
      "status": "ready"
    },
    {
      "id": "4d5e6f7a-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
      "scene_number": 4,
      "narration_text": "They always had.",
      "image_prompt": "Close-up of the lighthouse beam sweeping across dark ocean waters, illuminating whitecaps and rain, timeless and resolute, cinematic noir style",
      "duration_sec": 6.0,
      "status": "ready"
    },
    {
      "id": "5e6f7a8b-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
      "scene_number": 5,
      "narration_text": "She didn't know that tonight, one of those ships carried her estranged daughter home.",
      "image_prompt": "A young woman standing at the bow of a ship in a storm, looking toward a distant lighthouse beam, her coat soaked with rain, emotional determination on her face, cinematic noir style",
      "duration_sec": 16.0,
      "status": "ready"
    },
    {
      "id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
      "scene_number": 6,
      "narration_text": "And her daughter didn't come alone.",
      "image_prompt": "Two silhouettes on the deck of a ship approaching a lighthouse, the beam illuminating them from above, mysterious and foreboding atmosphere, cinematic noir style",
      "duration_sec": 8.0,
      "status": "ready"
    }
  ],
  "video_url": null,
  "created_at": "2026-03-25T10:05:00Z",
  "updated_at": "2026-03-25T10:30:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this episode's parent story |
| `404` | `not_found` | Episode with this ID does not exist |

---

#### `PATCH /episodes/:id`

Update episode settings such as title, target duration, or style presets.

**Request:**

| Component | Value |
|---|---|
| Method | `PATCH` |
| Path | `/api/v1/episodes/:id` |
| Headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | `UUID` | Episode ID |

**Request Body** (all fields optional):

```json
{
  "title": "The Storm Approaches",
  "target_duration_sec": 80,
  "style_preset_ids": {
    "visual": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d"
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `string` | No | Updated episode title |
| `target_duration_sec` | `integer` | No | Updated target duration (60-90) |
| `style_preset_ids` | `object` | No | Style preset IDs to update (partial update: only specified categories are changed) |

**Response: `200 OK`**

```json
{
  "id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "story_id": "a3f1b2c4-5d6e-7f8a-9b0c-1d2e3f4a5b6c",
  "episode_number": 1,
  "title": "The Storm Approaches",
  "target_duration_sec": 80,
  "style_presets": {
    "visual": {
      "id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
      "name": "Watercolor Dream",
      "category": "visual"
    },
    "voice": {
      "id": "f2a3b4c5-6d7e-8f9a-0b1c-2d3e4f5a6b7c",
      "name": "Deep Narrator",
      "category": "voice"
    },
    "music": {
      "id": "a3b4c5d6-7e8f-9a0b-1c2d-3e4f5a6b7c8d",
      "name": "Ambient Tension",
      "category": "music"
    }
  },
  "status": "scenes_ready",
  "scene_count": 6,
  "created_at": "2026-03-25T10:05:00Z",
  "updated_at": "2026-03-25T11:15:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this episode's parent story |
| `404` | `not_found` | Episode with this ID does not exist |
| `422` | `validation_error` | Invalid duration range or invalid style preset IDs |

---

#### `DELETE /episodes/:id`

Delete an episode and all associated scenes and generated assets.

**Request:**

| Component | Value |
|---|---|
| Method | `DELETE` |
| Path | `/api/v1/episodes/:id` |
| Headers | `Authorization: Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | `UUID` | Episode ID |

**Response: `200 OK`**

```json
{
  "message": "Episode deleted successfully.",
  "id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this episode's parent story |
| `404` | `not_found` | Episode with this ID does not exist |

---

### 4. Scenes / Beats

Base path: `/api/v1/episodes/:episode_id/scenes` (collection) and `/api/v1/scenes/:id` (individual)

---

#### `POST /episodes/:episode_id/generate-breakdown`

Triggers an AI-powered scene breakdown. The Claude API analyzes the episode's text selection and produces an ordered list of narration segments paired with image prompts. This is an asynchronous operation that returns a generation job.

**Request:**

| Component | Value |
|---|---|
| Method | `POST` |
| Path | `/api/v1/episodes/:episode_id/generate-breakdown` |
| Headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `episode_id` | `UUID` | Episode ID |

**Request Body** (optional):

```json
{
  "max_scenes": 8,
  "tone_guidance": "Suspenseful and melancholic, building to a hopeful reveal"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `max_scenes` | `integer` | No | Maximum number of scenes to generate (default: calculated from target duration) |
| `tone_guidance` | `string` | No | Additional tone/mood guidance for the AI breakdown |

**Response: `201 Created`**

```json
{
  "job_id": "9a0b1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d",
  "episode_id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "type": "scene_breakdown",
  "status": "queued",
  "created_at": "2026-03-25T10:10:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this episode's parent story |
| `404` | `not_found` | Episode with this ID does not exist |
| `409` | `conflict` | A scene breakdown is already in progress for this episode |
| `422` | `validation_error` | Episode has no text content to break down |

---

#### `GET /episodes/:episode_id/scenes`

List all scenes for an episode in display order.

**Request:**

| Component | Value |
|---|---|
| Method | `GET` |
| Path | `/api/v1/episodes/:episode_id/scenes` |
| Headers | `Authorization: Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `episode_id` | `UUID` | Episode ID |

**Response: `200 OK`**

```json
{
  "data": [
    {
      "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "episode_id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
      "scene_number": 1,
      "narration_text": "Margaret had kept the lighthouse running for forty years.",
      "image_prompt": "An elderly woman with weathered hands stands inside a lighthouse lantern room, golden light from the lens illuminating her face, dramatic chiaroscuro lighting, cinematic noir style",
      "duration_sec": 12.5,
      "image_url": null,
      "voiceover_url": null,
      "status": "ready",
      "created_at": "2026-03-25T10:12:00Z",
      "updated_at": "2026-03-25T10:12:00Z"
    },
    {
      "id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
      "episode_id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
      "scene_number": 2,
      "narration_text": "The night the storm took the power grid down, she climbed the spiral stairs one last time, oil lamp in hand.",
      "image_prompt": "A dark spiral staircase inside a lighthouse, an elderly woman ascending with a glowing oil lamp casting long shadows on stone walls, rain visible through a small window, cinematic noir style",
      "duration_sec": 15.0,
      "image_url": null,
      "voiceover_url": null,
      "status": "ready",
      "created_at": "2026-03-25T10:12:00Z",
      "updated_at": "2026-03-25T10:12:00Z"
    }
  ]
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this episode's parent story |
| `404` | `not_found` | Episode with this ID does not exist |

---

#### `PATCH /scenes/:id`

Update a scene's narration text, image prompt, or estimated duration.

**Request:**

| Component | Value |
|---|---|
| Method | `PATCH` |
| Path | `/api/v1/scenes/:id` |
| Headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | `UUID` | Scene ID |

**Request Body** (all fields optional):

```json
{
  "narration_text": "For forty years, Margaret had been the keeper of the light.",
  "image_prompt": "An elderly woman silhouetted against a massive lighthouse lens, warm amber glow, dust particles floating in light beams, cinematic noir style",
  "duration_sec": 14.0
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `narration_text` | `string` | No | Updated narration/voiceover text |
| `image_prompt` | `string` | No | Updated image generation prompt |
| `duration_sec` | `number` | No | Updated estimated duration in seconds |

**Response: `200 OK`**

```json
{
  "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "episode_id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "scene_number": 1,
  "narration_text": "For forty years, Margaret had been the keeper of the light.",
  "image_prompt": "An elderly woman silhouetted against a massive lighthouse lens, warm amber glow, dust particles floating in light beams, cinematic noir style",
  "duration_sec": 14.0,
  "image_url": null,
  "voiceover_url": null,
  "status": "ready",
  "created_at": "2026-03-25T10:12:00Z",
  "updated_at": "2026-03-25T11:30:00Z"
}
```

> **Note:** Updating `narration_text` or `image_prompt` will invalidate any previously generated voiceover or image assets for this scene. The `image_url` and `voiceover_url` fields will be set to `null` and must be regenerated.

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this scene's parent story |
| `404` | `not_found` | Scene with this ID does not exist |
| `422` | `validation_error` | Field value fails validation constraints |

---

#### `DELETE /scenes/:id`

Delete a single scene. Remaining scenes are automatically renumbered.

**Request:**

| Component | Value |
|---|---|
| Method | `DELETE` |
| Path | `/api/v1/scenes/:id` |
| Headers | `Authorization: Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | `UUID` | Scene ID |

**Response: `200 OK`**

```json
{
  "message": "Scene deleted successfully.",
  "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this scene's parent story |
| `404` | `not_found` | Scene with this ID does not exist |

---

#### `POST /episodes/:episode_id/scenes/reorder`

Reorder scenes within an episode. The request body must contain all scene IDs for the episode in the desired order.

**Request:**

| Component | Value |
|---|---|
| Method | `POST` |
| Path | `/api/v1/episodes/:episode_id/scenes/reorder` |
| Headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `episode_id` | `UUID` | Episode ID |

**Request Body:**

```json
{
  "scene_ids": [
    "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
    "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
    "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
    "5e6f7a8b-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
    "4d5e6f7a-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
    "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c"
  ]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `scene_ids` | `UUID[]` | Yes | Complete ordered list of all scene IDs belonging to this episode |

**Response: `200 OK`**

```json
{
  "message": "Scenes reordered successfully.",
  "episode_id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "scene_order": [
    { "id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e", "scene_number": 1 },
    { "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d", "scene_number": 2 },
    { "id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f", "scene_number": 3 },
    { "id": "5e6f7a8b-9c0d-1e2f-3a4b-5c6d7e8f9a0b", "scene_number": 4 },
    { "id": "4d5e6f7a-8b9c-0d1e-2f3a-4b5c6d7e8f9a", "scene_number": 5 },
    { "id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c", "scene_number": 6 }
  ]
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this episode's parent story |
| `404` | `not_found` | Episode with this ID does not exist |
| `422` | `validation_error` | Scene IDs list is incomplete, contains duplicates, or includes IDs that do not belong to this episode |

---

### 5. Style Presets

Base path: `/api/v1/style-presets`

Style presets are system-managed configurations for visual style (image generation), voice (ElevenLabs voice selection), and music (background audio). They are read-only for end users.

---

#### `GET /style-presets`

List all active style presets, optionally filtered by category.

**Request:**

| Component | Value |
|---|---|
| Method | `GET` |
| Path | `/api/v1/style-presets` |
| Headers | `Authorization: Bearer <token>` |

**Query Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `category` | `string` | _all_ | Filter by category: `visual`, `voice`, `music` |

**Example:** `GET /api/v1/style-presets?category=visual`

**Response: `200 OK`**

```json
{
  "data": [
    {
      "id": "e1f2a3b4-5c6d-7e8f-9a0b-1c2d3e4f5a6b",
      "name": "Cinematic Noir",
      "category": "visual",
      "description": "High-contrast black and white with deep shadows and dramatic lighting. Inspired by classic film noir cinematography.",
      "thumbnail_url": "https://assets.scooby.app/presets/visual/cinematic-noir-thumb.jpg",
      "config": {
        "negative_prompt": "bright colors, cheerful, cartoon, anime",
        "style_suffix": "cinematic noir style, high contrast, deep shadows, dramatic lighting, black and white",
        "cfg_scale": 7.5,
        "sampler": "DPM++ 2M Karras"
      },
      "is_active": true,
      "created_at": "2026-03-01T00:00:00Z"
    },
    {
      "id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
      "name": "Watercolor Dream",
      "category": "visual",
      "description": "Soft watercolor aesthetics with gentle color washes and organic textures. Evokes a dreamy, nostalgic atmosphere.",
      "thumbnail_url": "https://assets.scooby.app/presets/visual/watercolor-dream-thumb.jpg",
      "config": {
        "negative_prompt": "photorealistic, sharp lines, digital art",
        "style_suffix": "watercolor painting style, soft edges, color washes, organic textures, dreamy atmosphere",
        "cfg_scale": 8.0,
        "sampler": "DPM++ 2M Karras"
      },
      "is_active": true,
      "created_at": "2026-03-01T00:00:00Z"
    },
    {
      "id": "b1c2d3e4-f5a6-b7c8-d9e0-f1a2b3c4d5e6",
      "name": "Comic Book Pop",
      "category": "visual",
      "description": "Bold outlines, halftone dots, and vivid primary colors. Classic American comic book aesthetic.",
      "thumbnail_url": "https://assets.scooby.app/presets/visual/comic-book-pop-thumb.jpg",
      "config": {
        "negative_prompt": "photorealistic, muted colors, watercolor",
        "style_suffix": "comic book style, bold outlines, halftone dots, vivid primary colors, dynamic composition",
        "cfg_scale": 7.0,
        "sampler": "Euler a"
      },
      "is_active": true,
      "created_at": "2026-03-01T00:00:00Z"
    }
  ]
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `400` | `invalid_parameter` | Invalid category value (must be `visual`, `voice`, or `music`) |

---

#### `GET /style-presets/:id`

Retrieve a single style preset with full configuration details.

**Request:**

| Component | Value |
|---|---|
| Method | `GET` |
| Path | `/api/v1/style-presets/:id` |
| Headers | `Authorization: Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `id` | `UUID` | Style preset ID |

**Response: `200 OK`**

```json
{
  "id": "f2a3b4c5-6d7e-8f9a-0b1c-2d3e4f5a6b7c",
  "name": "Deep Narrator",
  "category": "voice",
  "description": "A deep, resonant male voice with a warm, authoritative tone. Ideal for dramatic narration and storytelling.",
  "thumbnail_url": "https://assets.scooby.app/presets/voice/deep-narrator-thumb.jpg",
  "config": {
    "elevenlabs_voice_id": "pNInz6obpgDQGcFmaJgB",
    "stability": 0.75,
    "similarity_boost": 0.80,
    "style": 0.35,
    "use_speaker_boost": true
  },
  "is_active": true,
  "created_at": "2026-03-01T00:00:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `404` | `not_found` | Style preset with this ID does not exist |

---

### 6. Video Generation Pipeline

These endpoints trigger the multi-step video generation pipeline: image generation (Stability AI), voiceover synthesis (ElevenLabs), and video composition (Remotion). All generation operations are asynchronous and tracked via generation jobs.

---

#### `POST /episodes/:episode_id/generate`

Start the full video generation pipeline for an episode. This creates images for all scenes, generates voiceovers, composes background music, and renders the final video. Requires that scene breakdown has already been completed.

**Request:**

| Component | Value |
|---|---|
| Method | `POST` |
| Path | `/api/v1/episodes/:episode_id/generate` |
| Headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `episode_id` | `UUID` | Episode ID |

**Request Body** (optional):

```json
{
  "image_resolution": "1080x1920",
  "voice_speed": 1.0,
  "include_captions": true,
  "caption_style": "word_highlight"
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `image_resolution` | `string` | No | `"1080x1920"` | Output image resolution (must be 9:16 aspect ratio) |
| `voice_speed` | `number` | No | `1.0` | Voiceover speed multiplier (0.5-2.0) |
| `include_captions` | `boolean` | No | `true` | Whether to burn captions into the video |
| `caption_style` | `string` | No | `"word_highlight"` | Caption style: `word_highlight`, `full_sentence`, `karaoke` |

**Response: `201 Created`**

```json
{
  "job_id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "episode_id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "type": "full_pipeline",
  "status": "queued",
  "stages": [
    { "name": "image_generation", "status": "pending", "progress": 0 },
    { "name": "voiceover_synthesis", "status": "pending", "progress": 0 },
    { "name": "video_composition", "status": "pending", "progress": 0 }
  ],
  "created_at": "2026-03-25T11:00:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this episode's parent story |
| `404` | `not_found` | Episode with this ID does not exist |
| `409` | `conflict` | A generation pipeline is already running for this episode |
| `422` | `validation_error` | Episode has no scenes (scene breakdown must be completed first) |

---

#### `POST /scenes/:scene_id/regenerate-image`

Regenerate the image for a single scene using Stability AI. Useful when the writer has edited the image prompt and wants to preview the result without re-running the entire pipeline.

**Request:**

| Component | Value |
|---|---|
| Method | `POST` |
| Path | `/api/v1/scenes/:scene_id/regenerate-image` |
| Headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `scene_id` | `UUID` | Scene ID |

**Request Body** (optional):

```json
{
  "seed": 42,
  "image_resolution": "1080x1920"
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `seed` | `integer` | No | _random_ | Random seed for reproducibility |
| `image_resolution` | `string` | No | `"1080x1920"` | Output image resolution |

**Response: `201 Created`**

```json
{
  "job_id": "c0d1e2f3-4a5b-6c7d-8e9f-0a1b2c3d4e5f",
  "scene_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "type": "image_regeneration",
  "status": "queued",
  "created_at": "2026-03-25T11:10:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this scene's parent story |
| `404` | `not_found` | Scene with this ID does not exist |
| `409` | `conflict` | Image generation is already in progress for this scene |
| `422` | `validation_error` | Scene has no image_prompt defined |

---

#### `POST /scenes/:scene_id/regenerate-voiceover`

Regenerate the voiceover audio for a single scene using ElevenLabs. Useful when the writer has edited the narration text.

**Request:**

| Component | Value |
|---|---|
| Method | `POST` |
| Path | `/api/v1/scenes/:scene_id/regenerate-voiceover` |
| Headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `scene_id` | `UUID` | Scene ID |

**Request Body** (optional):

```json
{
  "voice_speed": 1.1,
  "stability": 0.80,
  "similarity_boost": 0.85
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `voice_speed` | `number` | No | `1.0` | Voiceover speed multiplier (0.5-2.0) |
| `stability` | `number` | No | _from preset_ | ElevenLabs stability setting (0.0-1.0) |
| `similarity_boost` | `number` | No | _from preset_ | ElevenLabs similarity boost (0.0-1.0) |

**Response: `201 Created`**

```json
{
  "job_id": "d1e2f3a4-5b6c-7d8e-9f0a-1b2c3d4e5f6a",
  "scene_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "type": "voiceover_regeneration",
  "status": "queued",
  "created_at": "2026-03-25T11:12:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this scene's parent story |
| `404` | `not_found` | Scene with this ID does not exist |
| `409` | `conflict` | Voiceover generation is already in progress for this scene |
| `422` | `validation_error` | Scene has no narration_text defined |

---

#### `GET /jobs/:job_id`

Retrieve the current status and progress of a generation job. Poll this endpoint if WebSocket is not available.

**Request:**

| Component | Value |
|---|---|
| Method | `GET` |
| Path | `/api/v1/jobs/:job_id` |
| Headers | `Authorization: Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `job_id` | `UUID` | Generation job ID |

**Response: `200 OK`**

```json
{
  "id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "episode_id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "type": "full_pipeline",
  "status": "processing",
  "progress": 45.0,
  "current_stage": "voiceover_synthesis",
  "stages": [
    { "name": "image_generation", "status": "completed", "progress": 100, "completed_at": "2026-03-25T11:03:00Z" },
    { "name": "voiceover_synthesis", "status": "processing", "progress": 60, "started_at": "2026-03-25T11:03:01Z" },
    { "name": "video_composition", "status": "pending", "progress": 0 }
  ],
  "result": null,
  "error": null,
  "created_at": "2026-03-25T11:00:00Z",
  "updated_at": "2026-03-25T11:04:30Z"
}
```

**When the job is completed, the `result` field is populated:**

```json
{
  "id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "episode_id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "type": "full_pipeline",
  "status": "completed",
  "progress": 100.0,
  "current_stage": null,
  "stages": [
    { "name": "image_generation", "status": "completed", "progress": 100, "completed_at": "2026-03-25T11:03:00Z" },
    { "name": "voiceover_synthesis", "status": "completed", "progress": 100, "completed_at": "2026-03-25T11:05:00Z" },
    { "name": "video_composition", "status": "completed", "progress": 100, "completed_at": "2026-03-25T11:08:00Z" }
  ],
  "result": {
    "video_url": "https://assets.scooby.app/videos/d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a/preview.mp4",
    "duration_sec": 74.5,
    "file_size_bytes": 15728640,
    "resolution": "1080x1920",
    "scenes_generated": 6
  },
  "error": null,
  "created_at": "2026-03-25T11:00:00Z",
  "updated_at": "2026-03-25T11:08:00Z"
}
```

**When the job has failed, the `error` field is populated:**

```json
{
  "id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "episode_id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "type": "full_pipeline",
  "status": "failed",
  "progress": 33.0,
  "current_stage": "voiceover_synthesis",
  "stages": [
    { "name": "image_generation", "status": "completed", "progress": 100, "completed_at": "2026-03-25T11:03:00Z" },
    { "name": "voiceover_synthesis", "status": "failed", "progress": 20, "error": "ElevenLabs API rate limit exceeded" },
    { "name": "video_composition", "status": "pending", "progress": 0 }
  ],
  "result": null,
  "error": {
    "code": "external_service_error",
    "message": "ElevenLabs API rate limit exceeded. Please try again in a few minutes.",
    "failed_at": "2026-03-25T11:04:00Z"
  },
  "created_at": "2026-03-25T11:00:00Z",
  "updated_at": "2026-03-25T11:04:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own the resource associated with this job |
| `404` | `not_found` | Job with this ID does not exist |

---

### 7. WebSocket: Generation Progress

**Endpoint:** `wss://<host>/api/v1/ws/jobs/:job_id`

Provides real-time progress updates for a generation job via WebSocket. This is the preferred method for tracking generation progress in the frontend.

---

#### Connection

**URL:** `wss://<host>/api/v1/ws/jobs/:job_id`

**Authentication:** Pass the Clerk JWT as a query parameter:

```
wss://api.scooby.app/api/v1/ws/jobs/8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e?token=<clerk_jwt_token>
```

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `job_id` | `UUID` | Generation job ID |

**Connection Lifecycle:**

1. Client opens WebSocket connection with a valid job ID and JWT token.
2. Server validates the token and confirms the user owns the associated resource.
3. Server begins sending progress messages as the job advances.
4. Server sends a terminal message (`completed` or `error`) and closes the connection.

---

#### Message Types

All messages are JSON-encoded. The `type` field determines the message structure.

---

##### `progress`

Sent periodically as the job advances through stages.

```json
{
  "type": "progress",
  "job_id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "progress": 45.0,
  "stage": "Generating images (3/6)",
  "stage_key": "image_generation",
  "detail": {
    "scenes_completed": 3,
    "scenes_total": 6
  },
  "timestamp": "2026-03-25T11:02:30Z"
}
```

| Field | Type | Description |
|---|---|---|
| `type` | `string` | Always `"progress"` |
| `job_id` | `UUID` | The generation job ID |
| `progress` | `number` | Overall progress percentage (0.0-100.0) |
| `stage` | `string` | Human-readable description of the current stage |
| `stage_key` | `string` | Machine-readable stage identifier: `image_generation`, `voiceover_synthesis`, `video_composition` |
| `detail` | `object` | Stage-specific detail (varies by stage) |
| `timestamp` | `string` | ISO 8601 timestamp |

---

##### `completed`

Sent once when the job finishes successfully. The WebSocket connection is closed after this message.

```json
{
  "type": "completed",
  "job_id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "video_url": "https://assets.scooby.app/videos/d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a/preview.mp4",
  "duration_sec": 74.5,
  "file_size_bytes": 15728640,
  "timestamp": "2026-03-25T11:08:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `type` | `string` | Always `"completed"` |
| `job_id` | `UUID` | The generation job ID |
| `video_url` | `string` | URL to the generated preview video |
| `duration_sec` | `number` | Final video duration in seconds |
| `file_size_bytes` | `integer` | File size in bytes |
| `timestamp` | `string` | ISO 8601 timestamp |

---

##### `error`

Sent if the job fails. The WebSocket connection is closed after this message.

```json
{
  "type": "error",
  "job_id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "message": "Image generation failed: Stability AI content policy violation for scene 3. Please revise the image prompt.",
  "code": "content_policy_violation",
  "failed_stage": "image_generation",
  "timestamp": "2026-03-25T11:02:45Z"
}
```

| Field | Type | Description |
|---|---|---|
| `type` | `string` | Always `"error"` |
| `job_id` | `UUID` | The generation job ID |
| `message` | `string` | Human-readable error description |
| `code` | `string` | Machine-readable error code |
| `failed_stage` | `string` | The pipeline stage that failed |
| `timestamp` | `string` | ISO 8601 timestamp |

---

#### WebSocket Error Codes

| Code | Description |
|---|---|
| `4001` | Authentication failed (invalid or expired token) |
| `4003` | Forbidden (user does not own the associated resource) |
| `4004` | Job not found |
| `4008` | Connection timeout (no job activity for 10 minutes) |

---

#### Client Example (JavaScript)

```javascript
const socket = new WebSocket(
  `wss://api.scooby.app/api/v1/ws/jobs/${jobId}?token=${clerkToken}`
);

socket.onmessage = (event) => {
  const message = JSON.parse(event.data);

  switch (message.type) {
    case "progress":
      console.log(`Progress: ${message.progress}% — ${message.stage}`);
      updateProgressBar(message.progress);
      break;
    case "completed":
      console.log(`Video ready: ${message.video_url}`);
      showVideoPlayer(message.video_url);
      break;
    case "error":
      console.error(`Generation failed: ${message.message}`);
      showErrorNotification(message.message);
      break;
  }
};

socket.onclose = (event) => {
  if (event.code >= 4000) {
    console.error(`WebSocket closed with code ${event.code}`);
  }
};
```

---

### 8. Export / Download

Base path: `/api/v1/episodes/:episode_id`

These endpoints handle final rendering and downloading of completed episode assets.

---

#### `POST /episodes/:episode_id/render-final`

Trigger a final high-quality MP4 render for an episode. The preview video generated during the pipeline is suitable for in-app playback, but the final render applies additional quality settings for distribution.

**Request:**

| Component | Value |
|---|---|
| Method | `POST` |
| Path | `/api/v1/episodes/:episode_id/render-final` |
| Headers | `Authorization: Bearer <token>`, `Content-Type: application/json` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `episode_id` | `UUID` | Episode ID |

**Request Body** (optional):

```json
{
  "quality": "high",
  "include_captions": true,
  "caption_style": "word_highlight",
  "watermark": false
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `quality` | `string` | No | `"high"` | Render quality: `"standard"` (720x1280, 30fps), `"high"` (1080x1920, 30fps), `"ultra"` (1080x1920, 60fps) |
| `include_captions` | `boolean` | No | `true` | Whether to include captions in the final render |
| `caption_style` | `string` | No | `"word_highlight"` | Caption style: `word_highlight`, `full_sentence`, `karaoke` |
| `watermark` | `boolean` | No | `false` | Whether to include a Scooby watermark (free plan has this forced to `true`) |

**Response: `201 Created`**

```json
{
  "job_id": "e2f3a4b5-6c7d-8e9f-0a1b-2c3d4e5f6a7b",
  "episode_id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "type": "final_render",
  "status": "queued",
  "quality": "high",
  "created_at": "2026-03-25T12:00:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this episode's parent story |
| `404` | `not_found` | Episode with this ID does not exist |
| `409` | `conflict` | A final render is already in progress for this episode |
| `422` | `validation_error` | Episode has not completed video generation pipeline yet |

---

#### `GET /episodes/:episode_id/download/video`

Download the final rendered MP4 video file. Returns a redirect to a time-limited signed URL.

**Request:**

| Component | Value |
|---|---|
| Method | `GET` |
| Path | `/api/v1/episodes/:episode_id/download/video` |
| Headers | `Authorization: Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `episode_id` | `UUID` | Episode ID |

**Response: `200 OK`**

```json
{
  "download_url": "https://assets.scooby.app/videos/d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a/final.mp4?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...&X-Amz-Expires=3600&X-Amz-Signature=...",
  "filename": "the-storm-final.mp4",
  "file_size_bytes": 31457280,
  "duration_sec": 74.5,
  "resolution": "1080x1920",
  "expires_at": "2026-03-25T13:00:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this episode's parent story |
| `404` | `not_found` | Episode with this ID does not exist, or no final render exists |
| `409` | `conflict` | Final render is still in progress |

---

#### `GET /episodes/:episode_id/download/script`

Download the episode script as a PDF document. Includes scene numbers, narration text, image descriptions, and timing notes.

**Request:**

| Component | Value |
|---|---|
| Method | `GET` |
| Path | `/api/v1/episodes/:episode_id/download/script` |
| Headers | `Authorization: Bearer <token>` |

**Path Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `episode_id` | `UUID` | Episode ID |

**Response: `200 OK`**

```json
{
  "download_url": "https://assets.scooby.app/scripts/d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a/script.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...&X-Amz-Expires=3600&X-Amz-Signature=...",
  "filename": "the-storm-script.pdf",
  "file_size_bytes": 245760,
  "page_count": 3,
  "expires_at": "2026-03-25T13:00:00Z"
}
```

**Errors:**

| Status | Code | Description |
|---|---|---|
| `401` | `unauthorized` | Missing or invalid JWT token |
| `403` | `forbidden` | User does not own this episode's parent story |
| `404` | `not_found` | Episode with this ID does not exist, or episode has no scenes |

---

## Rate Limiting

All API endpoints are rate-limited per user. Rate limit headers are included in every response:

| Header | Description |
|---|---|
| `X-RateLimit-Limit` | Maximum requests allowed in the current window |
| `X-RateLimit-Remaining` | Requests remaining in the current window |
| `X-RateLimit-Reset` | Unix timestamp when the current window resets |

**Default limits:**

| Plan | General Endpoints | Generation Endpoints |
|---|---|---|
| Free | 100 requests/minute | 5 requests/hour |
| Pro | 500 requests/minute | 50 requests/hour |

When a rate limit is exceeded, the API returns `429 Too Many Requests`:

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Too many requests. Please try again in 45 seconds.",
    "details": {
      "retry_after_sec": 45
    }
  }
}
```

---

## Pagination

All list endpoints return paginated results with the following envelope:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_items": 42,
    "total_pages": 3
  }
}
```

| Field | Type | Description |
|---|---|---|
| `pagination.page` | `integer` | Current page number (1-indexed) |
| `pagination.per_page` | `integer` | Number of items per page |
| `pagination.total_items` | `integer` | Total number of matching items |
| `pagination.total_pages` | `integer` | Total number of pages |

---

## Changelog

### v0.1 (MVP) — 2026-03-25

- Initial API release
- Auth sync with Clerk
- Story CRUD operations
- Episode management with style presets
- AI-powered scene breakdown via Claude API
- Full video generation pipeline (Stability AI + ElevenLabs + Remotion)
- Real-time progress tracking via WebSocket
- Video and script export/download
