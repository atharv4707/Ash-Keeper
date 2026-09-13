from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.api.player import profile_for
from app.api.serializers import archetype_info, quest_out
from app.core.database import get_db
from app.models import Quest, QuestCompletion, Realm, User
from app.schemas import QuestCreateRequest
from app.services.progression import apply_xp, calculate_archetype, update_streak, xp_for_level
from app.services.achievements import refresh_achievements

router = APIRouter(prefix="/quests", tags=["Quests"])

CATEGORY_ATTRIBUTES = {"CODING": "CRAFT", "CRAFT": "CRAFT", "STUDY": "FOCUS", "LEARNING": "FOCUS", "FOCUS": "FOCUS", "GYM": "VIGOR", "FITNESS": "VIGOR", "VIGOR": "VIGOR", "DISCIPLINE": "WILL", "PERSONAL": "WILL", "WILL": "WILL"}
REWARDS = {"EASY": (30, 10, 1), "MEDIUM": (60, 20, 2), "HARD": (100, 35, 3), "LEGENDARY": (180, 60, 5)}


@router.get("")
async def list_quests(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    quests = (await db.scalars(select(Quest).where(Quest.created_by == user.id).order_by(Quest.created_at.desc()))).all()
    return [quest_out(q) for q in quests]


@router.post("", status_code=201, summary="Create a real-life quest")
async def create_quest(body: QuestCreateRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    category, difficulty = body.category.strip().upper(), body.difficulty.strip().upper()
    if difficulty not in REWARDS:
        raise HTTPException(422, detail={"error": "INVALID_DIFFICULTY", "message": "Difficulty must be Easy, Medium, Hard, or Legendary."})

    attribute_value = (body.attribute or CATEGORY_ATTRIBUTES.get(category, "WILL")).strip().upper()
    if attribute_value not in {"CRAFT", "FOCUS", "VIGOR", "WILL"}:
        raise HTTPException(422, detail={"error": "INVALID_ATTRIBUTE", "message": "Attribute must be one of CRAFT, FOCUS, VIGOR, or WILL."})

    xp, embers, gain = REWARDS[difficulty]
    quest = Quest(
        title=body.title.strip(),
        description=body.description,
        category=category,
        quest_type="CUSTOM",
        difficulty=difficulty.title(),
        xp_reward=xp,
        ember_reward=embers,
        attribute=attribute_value,
        attribute_gain=gain,
        created_by=user.id,
    )
    db.add(quest)
    await db.commit()
    await db.refresh(quest)
    return quest_out(quest)


@router.post("/{quest_id}/complete", summary="Atomically complete a quest and award progression")
async def complete_quest(quest_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    quest = await db.scalar(select(Quest).where(Quest.id == quest_id, Quest.created_by == user.id).with_for_update())
    if not quest:
        raise HTTPException(404, detail={"error": "QUEST_NOT_FOUND", "message": "That quest does not belong to your journal."})
    if quest.status == "COMPLETED":
        raise HTTPException(409, detail={"error": "QUEST_ALREADY_COMPLETED", "message": "This quest has already been completed."})
    profile = await profile_for(db, user)
    old_level = profile.level
    quest.status, quest.completed_at = "COMPLETED", datetime.now(timezone.utc)
    setattr(profile, quest.attribute.lower(), getattr(profile, quest.attribute.lower()) + quest.attribute_gain)
    profile.embers += quest.ember_reward
    level_up, levels_gained = apply_xp(profile, quest.xp_reward)
    update_streak(profile, quest.completed_at)
    profile.archetype = calculate_archetype(profile)
    completion = QuestCompletion(user_id=user.id, quest_id=quest.id, xp_awarded=quest.xp_reward, embers_awarded=quest.ember_reward, attribute_awarded=quest.attribute, attribute_gain=quest.attribute_gain, level_before=old_level, level_after=profile.level)
    db.add(completion)
    await db.flush()
    achievements_unlocked = await refresh_achievements(db, user.id, profile)
    realms = (await db.scalars(select(Realm).where(Realm.level_requirement > old_level, Realm.level_requirement <= profile.level))).all()
    await db.commit()
    return {"quest": quest_out(quest), "rewards": {"xp": quest.xp_reward, "embers": quest.ember_reward}, "attribute_change": {quest.attribute.lower(): quest.attribute_gain}, "player": {"level": profile.level, "current_xp": profile.current_xp, "xp_max": xp_for_level(profile.level), "total_xp": profile.total_xp, "embers": profile.embers, "combo": profile.combo, "current_streak": profile.current_streak, "longest_streak": profile.longest_streak, "craft": profile.craft, "focus": profile.focus, "vigor": profile.vigor, "will": profile.will, "archetype": profile.archetype, "archetype_info": archetype_info(profile)}, "level_up": level_up, "levels_gained": levels_gained, "unlocked_realms": [r.name for r in realms], "achievements_unlocked": achievements_unlocked}
