from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.api.player import profile_for
from app.api.serializers import item_out, realm_out
from app.core.database import get_db
from app.models import Inventory, Item, PlayerProfile, Quest, QuestCompletion, Realm, User
from app.schemas import SettingsUpdate

router = APIRouter(tags=["Game content"])


@router.get("/cache/items")
async def cache_items(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    profile = await profile_for(db, user)
    inventory = {i.item_id: i for i in (await db.scalars(select(Inventory).where(Inventory.user_id == user.id))).all()}
    items = (await db.scalars(select(Item).order_by(Item.price))).all()
    return [
        item_out(
            item,
            item.id in inventory,
            inventory[item.id].equipped if item.id in inventory else False,
            item.level_requirement > profile.level and item.id not in inventory,
        )
        for item in items
    ]


@router.post("/cache/items/{item_id}/purchase")
async def purchase(item_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(Item).where(Item.id == item_id).with_for_update())
    profile = await db.scalar(select(PlayerProfile).where(PlayerProfile.user_id == user.id).with_for_update())

    if not item:
        raise HTTPException(404, detail={"error": "ITEM_NOT_FOUND", "message": "This relic is no longer in the Cache."})
    if not profile:
        raise HTTPException(404, detail={"error": "PROFILE_NOT_FOUND", "message": "Player profile could not be loaded."})
    if item.level_requirement > profile.level:
        raise HTTPException(403, detail={"error": "LEVEL_LOCKED", "message": "This relic requires a higher level before it can be acquired."})
    if profile.embers < item.price:
        raise HTTPException(400, detail={"error": "INSUFFICIENT_EMBERS", "message": "You do not have enough Embers to purchase this item."})
    if await db.scalar(select(Inventory).where(Inventory.user_id == user.id, Inventory.item_id == item.id)):
        raise HTTPException(409, detail={"error": "ITEM_OWNED", "message": "You already own this item."})

    profile.embers -= item.price
    db.add(Inventory(user_id=user.id, item_id=item.id))
    await db.commit()
    return {"item": item_out(item, True, False, False), "new_embers": profile.embers, "message": f"Acquired {item.name}"}


@router.get("/inventory")
async def inventory(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Inventory, Item)
        .join(Item, Item.id == Inventory.item_id)
        .where(Inventory.user_id == user.id)
        .order_by(Item.name)
    )).all()
    profile = await profile_for(db, user)
    return [
        {
            "inventory_id": inv.id,
            "item": item_out(item, True, inv.equipped, item.level_requirement > profile.level and not inv.equipped),
            "equipped": inv.equipped,
            "acquired_at": inv.acquired_at.isoformat(),
        }
        for inv, item in rows
    ]


@router.post("/inventory/{item_id}/equip")
async def equip(item_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(Item).where(Item.id == item_id))
    if not item:
        raise HTTPException(404, detail={"error": "ITEM_NOT_FOUND", "message": "This item does not exist."})

    profile = await profile_for(db, user)
    if item.level_requirement > profile.level:
        raise HTTPException(403, detail={"error": "LEVEL_LOCKED", "message": "This relic requires a higher level before it can be acquired."})

    inv = await db.scalar(select(Inventory).where(Inventory.user_id == user.id, Inventory.item_id == item.id).with_for_update())
    if not inv:
        raise HTTPException(404, detail={"error": "ITEM_NOT_OWNED", "message": "You can only equip relics you own."})

    same_slot_rows = (
        await db.scalars(
            select(Inventory)
            .join(Item, Item.id == Inventory.item_id)
            .where(Inventory.user_id == user.id, Item.slot == item.slot)
            .with_for_update()
        )
    ).all()
    for row in same_slot_rows:
        row.equipped = row.id == inv.id

    inv.equipped = True
    await db.commit()
    return {"item": item_out(item, True, True, False), "equipped": True, "message": f"Equipped {item.name}"}


@router.post("/inventory/{item_id}/unequip")
async def unequip(item_id: str, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(Item).where(Item.id == item_id))
    if not item:
        raise HTTPException(404, detail={"error": "ITEM_NOT_FOUND", "message": "This item does not exist."})

    inv = await db.scalar(select(Inventory).where(Inventory.user_id == user.id, Inventory.item_id == item_id).with_for_update())
    if not inv:
        raise HTTPException(404, detail={"error": "ITEM_NOT_OWNED", "message": "You can only change relics you own."})
    if not inv.equipped:
        raise HTTPException(409, detail={"error": "ITEM_NOT_EQUIPPED", "message": "This relic is not currently equipped."})

    inv.equipped = False
    await db.commit()
    return {"item_id": item_id, "item": item_out(item, True, False, False), "equipped": False, "message": f"Unequipped {item.name}"}


@router.get("/world")
async def world(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    p = await profile_for(db, user)
    realms = (await db.scalars(select(Realm).order_by(Realm.order_index))).all()
    return [realm_out(r, p.level) for r in realms]


@router.get("/quest-log")
async def quest_log(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(QuestCompletion, Quest).join(Quest).where(QuestCompletion.user_id == user.id).order_by(QuestCompletion.completed_at.desc()))).all()
    return [{"id": c.id, "title": q.title, "category": q.category, "completed_at": c.completed_at.isoformat(), "xp_awarded": c.xp_awarded, "embers_awarded": c.embers_awarded, "attribute_awarded": c.attribute_awarded, "attribute_gain": c.attribute_gain, "level_before": c.level_before, "level_after": c.level_after, "is_milestone": c.level_after > c.level_before, "date_label": "TODAY", "timestamp": c.completed_at.strftime("%I:%M %p")} for c, q in rows]


@router.patch("/settings")
async def settings(body: SettingsUpdate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    p = await profile_for(db, user)
    if body.sound_enabled is not None: p.sound_enabled = body.sound_enabled
    if body.reduced_motion is not None: p.reduced_motion = body.reduced_motion
    await db.commit()
    return {"sound_enabled": p.sound_enabled, "reduced_motion": p.reduced_motion}
