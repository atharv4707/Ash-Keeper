from datetime import datetime

from app.models import Item, PlayerProfile, Quest, Realm, User
from app.services.progression import xp_for_level


def iso(value: datetime | None):
    return value.isoformat() if value else None


def archetype_info(profile: PlayerProfile) -> dict:
    meta = {
        "THE BUILDER": ("#FF9E40", "Creation and craft lead your growth.", "THE MASTER ARCHITECT", "Keep building deliberately."),
        "THE SCHOLAR": ("#60A5FA", "Focus and learning lead your growth.", "THE TRUE SCHOLAR", "Protect deep-work time."),
        "THE WARRIOR": ("#34D399", "Vigor and movement lead your growth.", "THE VANGUARD", "Train with consistency."),
        "THE KEEPER": ("#C084FC", "Will and discipline lead your growth.", "THE STEADFAST KEEPER", "Hold the line daily."),
        "THE BALANCED": ("#FBBF24", "Your pillars are in equilibrium.", "THE HARMONIC AVATAR", "Advance every pillar together."),
    }[profile.archetype]
    return {"name": profile.archetype, "color": meta[0], "description": meta[1], "next_archetype": meta[2], "next_archetype_tip": meta[3]}


def player_out(user: User, p: PlayerProfile) -> dict:
    return {"id": p.id, "user_id": user.id, "level": p.level, "current_xp": p.current_xp, "xp_max": xp_for_level(p.level), "total_xp": p.total_xp, "embers": p.embers, "combo": p.combo, "current_streak": p.current_streak, "longest_streak": p.longest_streak, "craft": p.craft, "focus": p.focus, "vigor": p.vigor, "will": p.will, "archetype": p.archetype, "archetype_info": archetype_info(p), "sound_enabled": p.sound_enabled, "reduced_motion": p.reduced_motion, "avatar": p.avatar, "username": user.username, "email": user.email, "joined_date": user.created_at.strftime("%B %Y"), "title": p.archetype.title()}


def quest_out(q: Quest) -> dict:
    return {"id": q.id, "title": q.title, "description": q.description, "category": q.category, "quest_type": q.quest_type, "difficulty": q.difficulty, "xp_reward": q.xp_reward, "ember_reward": q.ember_reward, "attribute": q.attribute, "attribute_gain": q.attribute_gain, "status": q.status, "completed_at": iso(q.completed_at), "created_at": iso(q.created_at), "is_template": q.is_template}


def item_out(item: Item, owned=False, equipped=False, locked=False) -> dict:
    return {"id": item.id, "name": item.name, "description": item.description, "lore": item.lore, "effect": item.effect, "category": item.category, "slot": item.slot, "price": item.price, "rarity": item.rarity, "stat": item.stat, "stat_value": item.stat_value, "level_requirement": item.level_requirement, "icon": item.icon, "owned": owned, "equipped": equipped, "locked": locked}


def realm_out(realm: Realm, level: int) -> dict:
    return {"id": realm.id, "name": realm.name, "title": realm.title, "description": realm.description, "lore": realm.lore, "attribute": realm.attribute, "level_requirement": realm.level_requirement, "coordinates_x": realm.coordinates_x, "coordinates_y": realm.coordinates_y, "image": realm.image, "order_index": realm.order_index, "unlocked": level >= realm.level_requirement}
