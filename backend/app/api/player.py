from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.api.serializers import player_out, quest_out, realm_out
from app.core.database import get_db
from app.models import PlayerProfile, Quest, QuestCompletion, Realm, User

router = APIRouter(prefix="/player", tags=["Player"])


async def profile_for(db: AsyncSession, user: User) -> PlayerProfile:
    return await db.scalar(select(PlayerProfile).where(PlayerProfile.user_id == user.id))


@router.get("/profile", summary="Get the central player snapshot")
async def profile(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    return player_out(user, await profile_for(db, user))


@router.get("/dashboard", summary="Get home-screen state in one request")
async def dashboard(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    profile = await profile_for(db, user)
    quests = (await db.scalars(select(Quest).where(Quest.created_by == user.id, Quest.status == "ACTIVE").order_by(Quest.created_at.desc()))).all()
    realms = (await db.scalars(select(Realm).order_by(Realm.order_index))).all()
    return {"player": player_out(user, profile), "active_quests": [quest_out(q) for q in quests], "realms": [realm_out(r, profile.level) for r in realms]}


@router.get("/progression", summary="Get backend-derived weekly progression")
async def progression(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    p = await profile_for(db, user)
    since = datetime.now(timezone.utc) - timedelta(days=7)
    completions = (await db.scalars(select(QuestCompletion).where(QuestCompletion.user_id == user.id, QuestCompletion.completed_at >= since))).all()
    gains = {key: sum(c.attribute_gain for c in completions if c.attribute_awarded == key) for key in ("CRAFT", "FOCUS", "VIGOR", "WILL")}
    strongest = max(gains, key=gains.get)
    return {"strongest_attribute": strongest, "strongest_gain": gains[strongest], "current_archetype": p.archetype, "next_archetype": "THE MASTER ARCHITECT" if p.archetype == "THE BUILDER" else "THE EVOLVED SELF", "next_archetype_tip": "Complete real-world quests consistently to evolve.", "craft": p.craft, "focus": p.focus, "vigor": p.vigor, "will": p.will, "craft_last_week": gains["CRAFT"], "focus_last_week": gains["FOCUS"], "vigor_last_week": gains["VIGOR"], "will_last_week": gains["WILL"], "quests_this_week": len(completions), "xp_this_week": sum(c.xp_awarded for c in completions), "embers_this_week": sum(c.embers_awarded for c in completions), "streak": p.current_streak}
