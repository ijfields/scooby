"""Story CRUD endpoint tests."""

import uuid

from httpx import AsyncClient

FAKE_UUID = str(uuid.uuid4())


async def test_create_story(client: AsyncClient):
    text = "A " * 60  # > 100 chars
    resp = await client.post(
        "/api/v1/stories",
        json={"title": "Test Story", "raw_text": text},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Story"
    assert data["status"] == "draft"
    assert data["id"]
    return data["id"]


async def test_create_story_too_short(client: AsyncClient):
    resp = await client.post(
        "/api/v1/stories",
        json={"title": "Short", "raw_text": "Too short"},
    )
    assert resp.status_code == 422


async def test_list_stories(client: AsyncClient):
    # Create a story first
    text = "B " * 60
    await client.post(
        "/api/v1/stories",
        json={"title": "List Test", "raw_text": text},
    )
    resp = await client.get("/api/v1/stories")
    assert resp.status_code == 200
    data = resp.json()
    assert "stories" in data
    assert isinstance(data["stories"], list)
    assert len(data["stories"]) >= 1


async def test_get_story(client: AsyncClient):
    text = "C " * 60
    create_resp = await client.post(
        "/api/v1/stories",
        json={"title": "Get Test", "raw_text": text},
    )
    story_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/stories/{story_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Get Test"


async def test_update_story(client: AsyncClient):
    text = "D " * 60
    create_resp = await client.post(
        "/api/v1/stories",
        json={"title": "Update Test", "raw_text": text},
    )
    story_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/stories/{story_id}",
        json={"title": "Updated Title"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


async def test_delete_story(client: AsyncClient):
    text = "E " * 60
    create_resp = await client.post(
        "/api/v1/stories",
        json={"title": "Delete Test", "raw_text": text},
    )
    story_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/stories/{story_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/stories/{story_id}")
    assert resp.status_code == 404


async def test_get_nonexistent_story(client: AsyncClient):
    resp = await client.get(f"/api/v1/stories/{FAKE_UUID}")
    assert resp.status_code == 404
