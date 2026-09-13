from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.api.player import profile_for
from app.core.database import get_db
from app.models import NetworkProfile, SharedQuest, SharedQuestParticipant, User
from app.services.progression import apply_xp, calculate_archetype

router = APIRouter(tags=["Network"])


async def shared_out(db: AsyncSession, quest: SharedQuest, user: User) -> dict:
    participants = (await db.scalars(select(SharedQuestParticipant).where(SharedQuestParticipant.shared_quest_id == quest.id))).all()
    profile = await profile_for(db, user)
    players = [{"id": p.id, "name": user.username if p.user_id == user.id else "Ashkeeper", "level": profile.level if p.user_id == user.id else 1, "archetype": profile.archetype if p.user_id == user.id else "THE BALANCED", "avatar": profile.avatar if p.user_id == user.id else "", "contribution": p.contribution} for p in participants]
    total = sum(p.contribution for p in participants)
    return {"id": quest.id, "title": quest.title, "description": quest.description, "objective": quest.objective, "target_days": quest.target_days, "current_day": quest.current_day, "progress_percent": min(100, total), "status": quest.status, "reward_xp": quest.reward_xp, "reward_embers": quest.reward_embers, "players": players}


@router.get("/network")
async def network(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    profiles = (await db.scalars(select(NetworkProfile).order_by(NetworkProfile.name))).all()
    quest = await db.scalar(select(SharedQuest).where(SharedQuest.status == "ACTIVE").order_by(SharedQuest.created_at))
    players = [{"id": p.id, "name": p.name, "level": p.level, "archetype": p.archetype, "status": p.status, "avatar": p.avatar, "attributes": {"craft": p.craft, "focus": p.focus, "vigor": p.vigor, "will": p.will}} for p in profiles]
    return {"players": players, "shared_quest": await shared_out(db, quest, user) if quest else None}


@router.post("/shared-quests/{quest_id}/join")
async def join(quest_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    quest = await db.scalar(select(SharedQuest).where(SharedQuest.id == quest_id, SharedQuest.status == "ACTIVE"))
    if not quest: raise HTTPException(404, detail={"error": "SHARED_QUEST_NOT_FOUND", "message": "That expedition is no longer active."})
    if not await db.scalar(select(SharedQuestParticipant).where(SharedQuestParticipant.shared_quest_id == quest_id, SharedQuestParticipant.user_id == user.id)):
        db.add(SharedQuestParticipant(shared_quest_id=quest_id, user_id=user.id))
        await db.commit()
    return await shared_out(db, quest, user)


@router.post("/shared-quests/{quest_id}/contribute")
async def contribute(quest_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    participant = await db.scalar(select(SharedQuestParticipant).where(SharedQuestParticipant.shared_quest_id == quest_id, SharedQuestParticipant.user_id == user.id).with_for_update())
    quest = await db.scalar(select(SharedQuest).where(SharedQuest.id == quest_id, SharedQuest.status == "ACTIVE"))
    if not quest or not participant: raise HTTPException(409, detail={"error": "NOT_A_PARTICIPANT", "message": "Join this expedition before contributing."})
    participant.contribution += 10
    profile = await profile_for(db, user)
    profile.embers += 15
    apply_xp(profile, 40)
    profile.archetype = calculate_archetype(profile)
    await db.commit()
    return await shared_out(db, quest, user)
