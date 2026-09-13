from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api import achievements, auth, game_content, network, player, quests
from app.core.config import settings
from app.core.database import Base, get_engine
import app.models  # Register all SQLAlchemy models before metadata creation.


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Keeps local setup friction-free; production deployments should run Alembic first.
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="AshKeeper Game Engine", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(player.router)
app.include_router(quests.router)
app.include_router(game_content.router)
app.include_router(achievements.router)
app.include_router(network.router)


@app.exception_handler(HTTPException)
async def game_error(_: Request, exc: HTTPException) -> JSONResponse:
    """Keep client errors consistently shaped for the game's UI feedback."""
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        body = detail
    else:
        body = {"error": "REQUEST_FAILED", "message": str(detail)}
    return JSONResponse(status_code=exc.status_code, content=body)


@app.get("/health", tags=["System"])
async def health():
    return {"status": "online", "service": "ashkeeper-game-engine"}
