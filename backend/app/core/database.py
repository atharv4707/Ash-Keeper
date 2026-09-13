import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


_engines_by_loop: dict[int, object] = {}


class _SessionFactoryProxy:
    def __call__(self):
        return async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )


def get_engine():
    loop = asyncio.get_running_loop()
    loop_id = id(loop)
    engine = _engines_by_loop.get(loop_id)
    if engine is None:
        engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
        )
        _engines_by_loop[loop_id] = engine
    return engine


def get_session_local():
    return _SessionFactoryProxy()()


AsyncSessionLocal = _SessionFactoryProxy()


async def get_db():
    async_session = get_session_local()
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
