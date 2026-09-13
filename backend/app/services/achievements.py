from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Achievement, PlayerProfile, QuestCompletion, UserAchievement


async def refresh_achievements(db: AsyncSession, user_id: str, profile: PlayerProfile) -> list[dict]:
    """Refresh achievement state during a progression transaction; does not award currency."""
    definitions = (await db.scalars(select(Achievement))).all()
    quest_count = await db.scalar(select(func.count()).select_from(QuestCompletion).where(QuestCompletion.user_id == user_id)) or 0
    values = {"quest_count": quest_count, "streak": profile.current_streak, "level": profile.level, "craft": profile.craft}
    newly_unlocked: list[dict] = []
    for achievement in definitions:
        state = await db.scalar(select(UserAchievement).where(UserAchievement.user_id == user_id, UserAchievement.achievement_id == achievement.id))
        if not state:
            state = UserAchievement(user_id=user_id, achievement_id=achievement.id)
            db.add(state)
        state.progress = min(values.get(achievement.requirement_type, 0), achievement.requirement_value)
        if not state.unlocked and state.progress >= achievement.requirement_value:
            state.unlocked, state.unlocked_at = True, datetime.now(timezone.utc)
            newly_unlocked.append({"id": achievement.id, "title": achievement.title, "description": achievement.description, "ember_reward": achievement.ember_reward})
    return newly_unlocked
