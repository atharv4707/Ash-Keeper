from datetime import datetime, timezone

from app.models import PlayerProfile


def xp_for_level(level: int) -> int:
    """XP needed to advance from `level` to the next level."""
    return 100 + (level - 1) * 50


def apply_xp(profile: PlayerProfile, xp: int) -> tuple[bool, int]:
    old_level = profile.level
    profile.current_xp += xp
    profile.total_xp += xp
    while profile.current_xp >= xp_for_level(profile.level):
        profile.current_xp -= xp_for_level(profile.level)
        profile.level += 1
    return profile.level > old_level, profile.level - old_level


def calculate_archetype(profile: PlayerProfile) -> str:
    stats = {"CRAFT": profile.craft, "FOCUS": profile.focus, "VIGOR": profile.vigor, "WILL": profile.will}
    if max(stats.values()) - min(stats.values()) <= 3:
        return "THE BALANCED"
    if profile.craft >= profile.focus + 3 and profile.craft == max(stats.values()):
        return "THE BUILDER"
    return {"FOCUS": "THE SCHOLAR", "VIGOR": "THE WARRIOR", "WILL": "THE KEEPER", "CRAFT": "THE BUILDER"}[max(stats, key=stats.get)]


def update_streak(profile: PlayerProfile, occurred_at: datetime | None = None) -> None:
    occurred_at = occurred_at or datetime.now(timezone.utc)
    today = occurred_at.date()
    if not profile.last_completed_on:
        profile.current_streak = 1
    else:
        gap = (today - profile.last_completed_on.date()).days
        if gap == 1:
            profile.current_streak += 1
        elif gap > 1:
            profile.current_streak = 1
    profile.longest_streak = max(profile.longest_streak, profile.current_streak)
    profile.combo += 1
    profile.last_completed_on = occurred_at
