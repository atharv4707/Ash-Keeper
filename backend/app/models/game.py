import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def uid() -> str:
    return str(uuid.uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    profile: Mapped["PlayerProfile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class PlayerProfile(Base):
    __tablename__ = "player_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    level: Mapped[int] = mapped_column(Integer, default=1)
    current_xp: Mapped[int] = mapped_column(Integer, default=0)
    total_xp: Mapped[int] = mapped_column(Integer, default=0)
    embers: Mapped[int] = mapped_column(Integer, default=0)
    combo: Mapped[int] = mapped_column(Integer, default=0)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    craft: Mapped[int] = mapped_column(Integer, default=10)
    focus: Mapped[int] = mapped_column(Integer, default=10)
    vigor: Mapped[int] = mapped_column(Integer, default=10)
    will: Mapped[int] = mapped_column(Integer, default=10)
    archetype: Mapped[str] = mapped_column(String(40), default="THE BALANCED")
    avatar: Mapped[str] = mapped_column(String(500), default="")
    sound_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reduced_motion: Mapped[bool] = mapped_column(Boolean, default=False)
    last_completed_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    user: Mapped[User] = relationship(back_populates="profile")


class Quest(Base):
    __tablename__ = "quests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(30))
    quest_type: Mapped[str] = mapped_column(String(20), default="CUSTOM")
    difficulty: Mapped[str] = mapped_column(String(20))
    xp_reward: Mapped[int] = mapped_column(Integer)
    ember_reward: Mapped[int] = mapped_column(Integer)
    attribute: Mapped[str] = mapped_column(String(12))
    attribute_gain: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class QuestCompletion(Base):
    __tablename__ = "quest_completions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    quest_id: Mapped[str] = mapped_column(ForeignKey("quests.id", ondelete="CASCADE"), unique=True, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    xp_awarded: Mapped[int] = mapped_column(Integer)
    embers_awarded: Mapped[int] = mapped_column(Integer)
    attribute_awarded: Mapped[str] = mapped_column(String(12))
    attribute_gain: Mapped[int] = mapped_column(Integer)
    level_before: Mapped[int] = mapped_column(Integer)
    level_after: Mapped[int] = mapped_column(Integer)


class Item(Base):
    __tablename__ = "items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text)
    lore: Mapped[str] = mapped_column(Text)
    effect: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(30), default="RELIC")
    slot: Mapped[str] = mapped_column(String(30))
    price: Mapped[int] = mapped_column(Integer)
    rarity: Mapped[str] = mapped_column(String(20))
    stat: Mapped[str] = mapped_column(String(20))
    stat_value: Mapped[int] = mapped_column(Integer, default=0)
    level_requirement: Mapped[int] = mapped_column(Integer, default=1)
    icon: Mapped[str | None] = mapped_column(String(80), nullable=True)


class Inventory(Base):
    __tablename__ = "inventory"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_inventory_user_item"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    equipped: Mapped[bool] = mapped_column(Boolean, default=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Realm(Base):
    __tablename__ = "realms"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    lore: Mapped[str] = mapped_column(Text)
    attribute: Mapped[str] = mapped_column(String(12))
    level_requirement: Mapped[int] = mapped_column(Integer)
    coordinates_x: Mapped[int] = mapped_column(Integer)
    coordinates_y: Mapped[int] = mapped_column(Integer)
    image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer)


class Achievement(Base):
    __tablename__ = "achievements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30))
    requirement_type: Mapped[str] = mapped_column(String(30))
    requirement_value: Mapped[int] = mapped_column(Integer)
    ember_reward: Mapped[int] = mapped_column(Integer)
    icon: Mapped[str] = mapped_column(String(80))


class UserAchievement(Base):
    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    achievement_id: Mapped[str] = mapped_column(ForeignKey("achievements.id", ondelete="CASCADE"), index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    unlocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NetworkProfile(Base):
    """Static discoverable player content, deliberately separate from private users."""
    __tablename__ = "network_profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    level: Mapped[int] = mapped_column(Integer)
    archetype: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(200))
    avatar: Mapped[str] = mapped_column(String(500), default="")
    craft: Mapped[int] = mapped_column(Integer)
    focus: Mapped[int] = mapped_column(Integer)
    vigor: Mapped[int] = mapped_column(Integer)
    will: Mapped[int] = mapped_column(Integer)


class SharedQuest(Base):
    __tablename__ = "shared_quests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text)
    objective: Mapped[str] = mapped_column(String(300))
    target_days: Mapped[int] = mapped_column(Integer)
    current_day: Mapped[int] = mapped_column(Integer, default=0)
    reward_xp: Mapped[int] = mapped_column(Integer)
    reward_embers: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SharedQuestParticipant(Base):
    __tablename__ = "shared_quest_participants"
    __table_args__ = (UniqueConstraint("shared_quest_id", "user_id", name="uq_shared_quest_participant"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    shared_quest_id: Mapped[str] = mapped_column(ForeignKey("shared_quests.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    contribution: Mapped[int] = mapped_column(Integer, default=0)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
