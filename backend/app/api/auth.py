from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models import PlayerProfile, User
from app.schemas import LoginRequest, SignupRequest

router = APIRouter(prefix="/auth", tags=["Authentication"])


def token_response(user: User) -> dict:
    return {"access_token": create_access_token({"sub": user.id}), "token_type": "bearer", "user_id": user.id, "username": user.username}


@router.post("/signup", status_code=status.HTTP_201_CREATED, summary="Create an account and fresh player profile")
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    email, username = body.email.strip().lower(), body.username.strip()
    exists = await db.scalar(select(User).where(or_(User.email == email, User.username == username)))
    if exists:
        field = "email" if exists.email == email else "username"
        raise HTTPException(409, detail={"error": "DUPLICATE_ACCOUNT", "message": f"That {field} is already in use."})
    user = User(email=email, username=username, password_hash=hash_password(body.password))
    user.profile = PlayerProfile()
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return token_response(user)


@router.post("/login", summary="Authenticate an existing player")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, detail={"error": "INVALID_CREDENTIALS", "message": "Email or password is incorrect."})
    return token_response(user)


@router.get("/me", summary="Get the authenticated account")
async def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "username": user.username, "created_at": user.created_at.isoformat()}
