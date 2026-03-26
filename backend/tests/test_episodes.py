"""Episode endpoint tests."""

import uuid
from unittest.mock import MagicMock, patch

from httpx import AsyncClient

FAKE_UUID = str(uuid.uuid4())


async def test_create_episode_from_story(client: AsyncClient):
    text = "F " * 60
    story_resp = await client.post(
        "/api/v1/stories",
        json={"title": "Episode Test Story", "raw_text": text},
    )
    story_id = story_resp.json()["id"]

    with patch("app.tasks.ai.generate_scene_breakdown_task") as mock_task:
        mock_task.delay = MagicMock()
        resp = await client.post(f"/api/v1/episodes/from-story/{story_id}")

    assert resp.status_code == 201
    data = resp.json()
    assert data["story_id"] == story_id
    assert data["status"] == "draft"


async def test_get_episode(client: AsyncClient):
    text = "G " * 60
    story_resp = await client.post(
        "/api/v1/stories",
        json={"title": "Get Ep Story", "raw_text": text},
    )
    story_id = story_resp.json()["id"]

    with patch("app.tasks.ai.generate_scene_breakdown_task") as mock_task:
        mock_task.delay = MagicMock()
        create_resp = await client.post(f"/api/v1/episodes/from-story/{story_id}")
    episode_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/episodes/{episode_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == episode_id


async def test_update_episode(client: AsyncClient):
    text = "H " * 60
    story_resp = await client.post(
        "/api/v1/stories",
        json={"title": "Patch Ep Story", "raw_text": text},
    )
    story_id = story_resp.json()["id"]

    with patch("app.tasks.ai.generate_scene_breakdown_task") as mock_task:
        mock_task.delay = MagicMock()
        create_resp = await client.post(f"/api/v1/episodes/from-story/{story_id}")
    episode_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/episodes/{episode_id}",
        json={"target_duration_sec": 60},
    )
    assert resp.status_code == 200
    assert resp.json()["target_duration_sec"] == 60


async def test_list_jobs(client: AsyncClient):
    text = "I " * 60
    story_resp = await client.post(
        "/api/v1/stories",
        json={"title": "Jobs Story", "raw_text": text},
    )
    story_id = story_resp.json()["id"]

    with patch("app.tasks.ai.generate_scene_breakdown_task") as mock_task:
        mock_task.delay = MagicMock()
        create_resp = await client.post(f"/api/v1/episodes/from-story/{story_id}")
    episode_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/episodes/{episode_id}/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


async def test_get_nonexistent_episode(client: AsyncClient):
    resp = await client.get(f"/api/v1/episodes/{FAKE_UUID}")
    assert resp.status_code == 404
