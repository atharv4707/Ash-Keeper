from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.api.player import profile_for
from app.core.database import get_db
from app.models import Achievement, User, UserAchievement

router = APIRouter(prefix="/achievements", tags=["Achievements"])


def out(achievement: Achievement, state: UserAchievement | None) -> dict:
    return {"id": achievement.id, "title": achievement.title, "description": achievement.description, "category": achievement.category, "requirement_type": achievement.requirement_type, "requirement_value": achievement.requirement_value, "ember_reward": achievement.ember_reward, "max_progress": achievement.requirement_value, "progress": state.progress if state else 0, "unlocked": state.unlocked if state else False, "claimed": state.claimed if state else False, "unlocked_at": state.unlocked_at.isoformat() if state and state.unlocked_at else None}


@router.get("")
async def list_achievements(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    definitions = (await db.scalars(select(Achievement).order_by(Achievement.title))).all()
    states = {s.achievement_id: s for s in (await db.scalars(select(UserAchievement).where(UserAchievement.user_id == user.id))).all()}
    return [out(achievement, states.get(achievement.id)) for achievement in definitions]


@router.post("/{achievement_id}/claim")
async def claim(achievement_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    achievement = await db.scalar(select(Achievement).where(Achievement.id == achievement_id))
    state = await db.scalar(select(UserAchievement).where(UserAchievement.user_id == user.id, UserAchievement.achievement_id == achievement_id).with_for_update())
    if not achievement or not state:
        raise HTTPException(404, detail={"error": "ACHIEVEMENT_NOT_FOUND", "message": "This achievement has not been unlocked."})
    if not state.unlocked:
        raise HTTPException(409, detail={"error": "ACHIEVEMENT_LOCKED", "message": "Complete its requirement before claiming this reward."})
    if state.claimed:
        raise HTTPException(409, detail={"error": "ACHIEVEMENT_ALREADY_CLAIMED", "message": "This reward has already been claimed."})
    profile = await profile_for(db, user)
    state.claimed = True
    profile.embers += achievement.ember_reward
    await db.commit()
    return {"achievement": out(achievement, state), "embers_awarded": achievement.ember_reward, "new_embers": profile.embers}
