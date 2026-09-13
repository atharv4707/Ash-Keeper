"""Idempotently seed static AshKeeper catalog content; never creates player data."""
import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Achievement, Item, NetworkProfile, Realm, SharedQuest

ITEMS = [
    {"name": "Ashen Sigil", "description": "A glowing metallic talisman etched with the Ashkeeper crest.", "lore": "It hums whenever deliberate work begins.", "effect": "+5% XP across all actions", "category": "RELIC", "slot": "relic", "price": 120, "rarity": "Rare", "stat": "xp", "stat_value": 5, "level_requirement": 1, "icon": "Sparkles"},
    {"name": "Iron Will", "description": "A carved tungsten core that stabilizes impulsive thoughts.", "lore": "Forged under extreme gravitational pressure.", "effect": "+10 Will", "category": "RELIC", "slot": "talisman", "price": 200, "rarity": "Epic", "stat": "will", "stat_value": 10, "level_requirement": 2, "icon": "Shield"},
    {"name": "Obsidian Stylus", "description": "A precision chisel for digital architecture.", "lore": "Cuts through cognitive fog.", "effect": "+8 Craft", "category": "WEAPON", "slot": "weapon", "price": 240, "rarity": "Rare", "stat": "craft", "stat_value": 8, "level_requirement": 3, "icon": "Code"},
    {"name": "Astral Crown", "description": "A crown of hovering starlight filaments.", "lore": "Reserved for realm wardens.", "effect": "+30 Focus", "category": "RELIC", "slot": "aura", "price": 2200, "rarity": "Legendary", "stat": "focus", "stat_value": 30, "level_requirement": 10, "icon": "Crown"},
]

REALMS = [
    {"name": "THE KEEP", "title": "The Primordial Bastion", "description": "The central citadel where all keepers assemble.", "lore": "A beacon for intentional living.", "attribute": "ALL", "level_requirement": 1, "coordinates_x": 50, "coordinates_y": 52, "order_index": 1},
    {"name": "THE FORGE", "title": "The Foundry of Creation", "description": "A realm for making ideas real.", "lore": "Builders thrive under its pressure.", "attribute": "CRAFT", "level_requirement": 3, "coordinates_x": 26, "coordinates_y": 74, "order_index": 2},
    {"name": "THE ARCHIVE", "title": "The Crystalline Spire", "description": "A sanctuary for deep focus.", "lore": "Knowledge compounds here.", "attribute": "FOCUS", "level_requirement": 5, "coordinates_x": 22, "coordinates_y": 26, "order_index": 3},
    {"name": "THE TEMPLE", "title": "The Summit of Physicality", "description": "A mountain sanctuary for physical resilience.", "lore": "Its steps demand consistency.", "attribute": "VIGOR", "level_requirement": 8, "coordinates_x": 78, "coordinates_y": 22, "order_index": 4},
    {"name": "THE SANCTUM", "title": "The Astral Void", "description": "A realm for absolute discipline.", "lore": "Only steady keepers enter.", "attribute": "WILL", "level_requirement": 10, "coordinates_x": 80, "coordinates_y": 72, "order_index": 5},
]

ACHIEVEMENTS = [
    {"title": "FIRST SPARK", "description": "Complete your first real-life quest.", "category": "Progression", "requirement_type": "quest_count", "requirement_value": 1, "ember_reward": 50, "icon": "Sparkle"},
    {"title": "UNBROKEN", "description": "Reach a seven-day streak.", "category": "Consistency", "requirement_type": "streak", "requirement_value": 7, "ember_reward": 150, "icon": "Flame"},
    {"title": "THE GRINDER", "description": "Complete 25 quests.", "category": "Progression", "requirement_type": "quest_count", "requirement_value": 25, "ember_reward": 250, "icon": "CheckCircle2"},
    {"title": "ASCENSION", "description": "Reach level 10.", "category": "Progression", "requirement_type": "level", "requirement_value": 10, "ember_reward": 500, "icon": "Award"},
]

NETWORK_PROFILES = [
    {"name": "Riya", "level": 6, "archetype": "THE SCHOLAR", "status": "Deep in OS Kernel study", "avatar": "", "craft": 48, "focus": 86, "vigor": 39, "will": 55},
    {"name": "Kabir", "level": 8, "archetype": "THE WARRIOR", "status": "Finishing a rowing split", "avatar": "", "craft": 52, "focus": 44, "vigor": 82, "will": 63},
    {"name": "Aarav", "level": 7, "archetype": "THE BALANCED", "status": "Aligning weekly pillars", "avatar": "", "craft": 71, "focus": 68, "vigor": 70, "will": 69},
]

SHARED_QUESTS = [{"title": "THE BUILDERS' RUN", "description": "A cooperative multi-day expedition to manifest a shared prototype.", "objective": "Build something deliberate for five consecutive days.", "target_days": 5, "reward_xp": 500, "reward_embers": 200}]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        for model, records in ((Item, ITEMS), (Realm, REALMS), (Achievement, ACHIEVEMENTS)):
            for record in records:
                field = model.title if model is Achievement else model.name
                value = record["title"] if model is Achievement else record["name"]
                if not await session.scalar(select(model).where(field == value)):
                    session.add(model(**record))
        for record in NETWORK_PROFILES:
            if not await session.scalar(select(NetworkProfile).where(NetworkProfile.name == record["name"])):
                session.add(NetworkProfile(**record))
        for record in SHARED_QUESTS:
            if not await session.scalar(select(SharedQuest).where(SharedQuest.title == record["title"])):
                session.add(SharedQuest(**record))
        await session.commit()
    print("Static AshKeeper game content seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
