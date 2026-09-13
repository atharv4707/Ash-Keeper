import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_quest_lifecycle_respects_attribute_and_blocks_double_completion():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        suffix = uuid.uuid4().hex[:8]
        email = f"quest_lifecycle_test_{suffix}@example.com"
        password = "Password123!"
        username = f"quest_lifecycle_test_{suffix}"

        signup = await client.post(
            "/auth/signup",
            json={"username": username, "email": email, "password": password},
        )
        assert signup.status_code == 201, signup.text

        login = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post(
            "/quests",
            json={
                "title": "Build the real quest test",
                "description": "Verify attribute-driven rewards and persistence.",
                "category": "MAIN",
                "difficulty": "MEDIUM",
                "attribute": "CRAFT",
            },
            headers=headers,
        )
        assert create.status_code == 201, create.text
        quest = create.json()
        assert quest["attribute"] == "CRAFT"

        list_response = await client.get("/quests", headers=headers)
        assert list_response.status_code == 200, list_response.text
        assert any(item["id"] == quest["id"] for item in list_response.json())

        complete = await client.post(f"/quests/{quest['id']}/complete", headers=headers)
        assert complete.status_code == 200, complete.text
        payload = complete.json()
        assert payload["attribute_change"]["craft"] == 2
        assert payload["rewards"]["xp"] == 60
        assert payload["rewards"]["embers"] == 20

        profile = await client.get("/player/profile", headers=headers)
        assert profile.status_code == 200, profile.text
        prof = profile.json()
        assert prof["craft"] >= 12
        assert prof["level"] >= 1

        double = await client.post(f"/quests/{quest['id']}/complete", headers=headers)
        assert double.status_code == 409, double.text
        assert double.json()["error"] == "QUEST_ALREADY_COMPLETED"
