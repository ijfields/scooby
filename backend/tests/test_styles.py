"""Style presets endpoint tests."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.style_preset import StylePreset


async def test_list_styles_empty(client: AsyncClient):
    resp = await client.get("/api/v1/styles")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_list_styles_with_data(client: AsyncClient, db_session: AsyncSession):
    preset = StylePreset(
        name="Test Visual",
        category="visual",
        description="A test style",
        config={"style_prompt_suffix": "test"},
    )
    db_session.add(preset)
    await db_session.commit()

    resp = await client.get("/api/v1/styles")
    assert resp.status_code == 200
    data = resp.json()
    assert any(s["name"] == "Test Visual" for s in data)


async def test_list_styles_filter_category(client: AsyncClient, db_session: AsyncSession):
    for cat in ["visual", "voice", "music"]:
        preset = StylePreset(
            name=f"Filter {cat}",
            category=cat,
            config={},
        )
        db_session.add(preset)
    await db_session.commit()

    resp = await client.get("/api/v1/styles?category=voice")
    assert resp.status_code == 200
    data = resp.json()
    assert all(s["category"] == "voice" for s in data)
