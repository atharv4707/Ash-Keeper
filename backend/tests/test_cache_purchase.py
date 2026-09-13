import asyncio
import sys
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.database import get_session_local
from app.main import app
from app.models import Inventory, Item, PlayerProfile, User


async def create_user_and_token(client: AsyncClient, suffix: str | None = None):
    unique = f"{suffix or 'cache'}_{uuid.uuid4().hex[:8]}"
    email = f"cache_purchase_{unique}@example.com"
    password = "Password123!"
    username = f"cache_purchase_{unique}"
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
    return token, email, username


async def set_profile_embers(user_id: str, embers: int, level: int = 1):
    async_session = get_session_local()
    async with async_session() as session:
        profile = await session.scalar(select(PlayerProfile).where(PlayerProfile.user_id == user_id))
        assert profile is not None
        profile.embers = embers
        profile.level = level
        await session.commit()


@pytest.mark.asyncio
async def test_cache_catalog_returns_owned_and_locked_flags():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, _, _ = await create_user_and_token(client, "catalog")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/cache/items", headers=headers)
        assert response.status_code == 200, response.text
        payload = response.json()
        assert len(payload) > 0
        assert any("level_requirement" in item for item in payload)
        assert any("locked" in item for item in payload)


@pytest.mark.asyncio
async def test_successful_purchase_deducts_embers_and_creates_inventory_record():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, _, username = await create_user_and_token(client, "purchase_success")
        headers = {"Authorization": f"Bearer {token}"}

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            await set_profile_embers(user.id, 300, 1)

        item_response = await client.get("/cache/items", headers=headers)
        item_id = next(i["id"] for i in item_response.json() if i["name"] == "Ashen Sigil")

        response = await client.post(f"/cache/items/{item_id}/purchase", headers=headers)
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["new_embers"] == 180
        assert payload["item"]["owned"] is True

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            inventory = await session.scalar(select(Inventory).where(Inventory.user_id == user.id, Inventory.item_id == item_id))
            assert inventory is not None
            profile = await session.scalar(select(PlayerProfile).where(PlayerProfile.user_id == user.id))
            assert profile is not None
            assert profile.embers == 180


@pytest.mark.asyncio
async def test_insufficient_embers_is_rejected_without_purchasing():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, _, username = await create_user_and_token(client, "insufficient")
        headers = {"Authorization": f"Bearer {token}"}

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            await set_profile_embers(user.id, 30, 1)

        item_response = await client.get("/cache/items", headers=headers)
        item_id = next(i["id"] for i in item_response.json() if i["name"] == "Ashen Sigil")

        response = await client.post(f"/cache/items/{item_id}/purchase", headers=headers)
        assert response.status_code == 400, response.text
        assert response.json()["error"] == "INSUFFICIENT_EMBERS"

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            profile = await session.scalar(select(PlayerProfile).where(PlayerProfile.user_id == user.id))
            assert profile is not None
            assert profile.embers == 30
            count = await session.scalar(select(Inventory).where(Inventory.user_id == user.id, Inventory.item_id == item_id))
            assert count is None


@pytest.mark.asyncio
async def test_duplicate_purchase_is_blocked():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, _, username = await create_user_and_token(client, "duplicate")
        headers = {"Authorization": f"Bearer {token}"}

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            await set_profile_embers(user.id, 300, 1)

        item_response = await client.get("/cache/items", headers=headers)
        item_id = next(i["id"] for i in item_response.json() if i["name"] == "Ashen Sigil")

        first = await client.post(f"/cache/items/{item_id}/purchase", headers=headers)
        assert first.status_code == 200, first.text

        second = await client.post(f"/cache/items/{item_id}/purchase", headers=headers)
        assert second.status_code == 409, second.text
        assert second.json()["error"] == "ITEM_OWNED"


@pytest.mark.asyncio
async def test_level_locked_purchase_is_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, _, username = await create_user_and_token(client, "level_lock")
        headers = {"Authorization": f"Bearer {token}"}

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            await set_profile_embers(user.id, 2000, 1)

        item_response = await client.get("/cache/items", headers=headers)
        item_id = next(i["id"] for i in item_response.json() if i["name"] == "Astral Crown")

        response = await client.post(f"/cache/items/{item_id}/purchase", headers=headers)
        assert response.status_code == 403, response.text
        assert response.json()["error"] == "LEVEL_LOCKED"


@pytest.mark.asyncio
async def test_nonexistent_item_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, _, _ = await create_user_and_token(client, "missing_item")
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post("/cache/items/does-not-exist/purchase", headers=headers)
        assert response.status_code == 404, response.text
        assert response.json()["error"] == "ITEM_NOT_FOUND"


@pytest.mark.asyncio
async def test_atomic_failure_does_not_leave_partial_state():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, _, username = await create_user_and_token(client, "atomic")
        headers = {"Authorization": f"Bearer {token}"}

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            await set_profile_embers(user.id, 100, 1)

        item_response = await client.get("/cache/items", headers=headers)
        item_id = next(i["id"] for i in item_response.json() if i["name"] == "Ashen Sigil")

        response = await client.post(f"/cache/items/{item_id}/purchase", headers=headers)
        assert response.status_code == 400, response.text

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            profile = await session.scalar(select(PlayerProfile).where(PlayerProfile.user_id == user.id))
            assert profile is not None
            assert profile.embers == 100
            inventory_count = await session.scalar(select(Inventory).where(Inventory.user_id == user.id, Inventory.item_id == item_id))
            assert inventory_count is None


@pytest.mark.asyncio
async def test_ownership_status_is_visible_in_inventory_response():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, _, username = await create_user_and_token(client, "inventory")
        headers = {"Authorization": f"Bearer {token}"}

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            await set_profile_embers(user.id, 300, 1)

        item_response = await client.get("/cache/items", headers=headers)
        item_id = next(i["id"] for i in item_response.json() if i["name"] == "Ashen Sigil")

        purchase = await client.post(f"/cache/items/{item_id}/purchase", headers=headers)
        assert purchase.status_code == 200, purchase.text

        inventory = await client.get("/inventory", headers=headers)
        assert inventory.status_code == 200, inventory.text
        payload = inventory.json()
        assert any(entry["item"]["id"] == item_id for entry in payload)


@pytest.mark.asyncio
async def test_equip_owned_item_persists_and_is_visible_in_cache_catalog():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, _, username = await create_user_and_token(client, "equip_persist")
        headers = {"Authorization": f"Bearer {token}"}

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            await set_profile_embers(user.id, 300, 1)

        item_response = await client.get("/cache/items", headers=headers)
        item_id = next(i["id"] for i in item_response.json() if i["name"] == "Ashen Sigil")
        purchase = await client.post(f"/cache/items/{item_id}/purchase", headers=headers)
        assert purchase.status_code == 200, purchase.text

        equip = await client.post(f"/inventory/{item_id}/equip", headers=headers)
        assert equip.status_code == 200, equip.text
        assert equip.json()["equipped"] is True

        catalog = await client.get("/cache/items", headers=headers)
        assert catalog.status_code == 200, catalog.text
        assert next(i["equipped"] for i in catalog.json() if i["id"] == item_id) is True

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            inventory = await session.scalar(select(Inventory).where(Inventory.user_id == user.id, Inventory.item_id == item_id))
            assert inventory is not None and inventory.equipped is True


@pytest.mark.asyncio
async def test_unequip_persists_and_clears_equipped_state():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, _, username = await create_user_and_token(client, "unequip_persist")
        headers = {"Authorization": f"Bearer {token}"}

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            await set_profile_embers(user.id, 300, 1)

        item_response = await client.get("/cache/items", headers=headers)
        item_id = next(i["id"] for i in item_response.json() if i["name"] == "Ashen Sigil")
        purchase = await client.post(f"/cache/items/{item_id}/purchase", headers=headers)
        assert purchase.status_code == 200, purchase.text

        equip = await client.post(f"/inventory/{item_id}/equip", headers=headers)
        assert equip.status_code == 200, equip.text

        unequip = await client.post(f"/inventory/{item_id}/unequip", headers=headers)
        assert unequip.status_code == 200, unequip.text
        assert unequip.json()["equipped"] is False

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            inventory = await session.scalar(select(Inventory).where(Inventory.user_id == user.id, Inventory.item_id == item_id))
            assert inventory is not None and inventory.equipped is False


@pytest.mark.asyncio
async def test_cannot_equip_unowned_or_level_locked_item():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, _, username = await create_user_and_token(client, "equip_guard")
        headers = {"Authorization": f"Bearer {token}"}

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            await set_profile_embers(user.id, 40, 1)

        item_response = await client.get("/cache/items", headers=headers)
        owned_item_id = next(i["id"] for i in item_response.json() if i["name"] == "Ashen Sigil")
        locked_item_id = next(i["id"] for i in item_response.json() if i["name"] == "Astral Crown")

        missing = await client.post("/inventory/does-not-exist/equip", headers=headers)
        assert missing.status_code == 404, missing.text

        unowned = await client.post(f"/inventory/{owned_item_id}/equip", headers=headers)
        assert unowned.status_code == 404, unowned.text

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            await set_profile_embers(user.id, 2000, 1)

        locked = await client.post(f"/inventory/{locked_item_id}/equip", headers=headers)
        assert locked.status_code == 403, locked.text


@pytest.mark.asyncio
async def test_same_slot_replacement_unequips_previous_item():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token, _, username = await create_user_and_token(client, "same_slot")
        headers = {"Authorization": f"Bearer {token}"}

        async_session = get_session_local()
        async with async_session() as session:
            user = await session.scalar(select(User).where(User.username == username))
            assert user is not None
            await set_profile_embers(user.id, 2000, 10)

            item_one = await session.scalar(select(Item).where(Item.name == "Ashen Sigil"))
            assert item_one is not None
            item_two = Item(
                name=f"Echo Sigil {uuid.uuid4().hex[:8]}",
                description="Test duplicate-slot item",
                lore="For slot replacement tests",
                effect="+1 Focus",
                category="RELIC",
                slot="relic",
                price=10,
                rarity="Rare",
                stat="focus",
                stat_value=1,
                level_requirement=1,
                icon="Sparkles",
            )
            session.add(item_two)
            await session.commit()
            assert item_two.id is not None

            session.add(Inventory(user_id=user.id, item_id=item_one.id, equipped=False))
            session.add(Inventory(user_id=user.id, item_id=item_two.id, equipped=False))
            await session.commit()

        first = await client.post(f"/inventory/{item_one.id}/equip", headers=headers)
        assert first.status_code == 200, first.text

        second = await client.post(f"/inventory/{item_two.id}/equip", headers=headers)
        assert second.status_code == 200, second.text

        async_session = get_session_local()
        async with async_session() as session:
            inventory_rows = (await session.scalars(select(Inventory).where(Inventory.user_id == user.id, Inventory.item_id.in_([item_one.id, item_two.id])))).all()
            eq_map = {row.item_id: row.equipped for row in inventory_rows}
            assert eq_map[item_one.id] is False
            assert eq_map[item_two.id] is True
