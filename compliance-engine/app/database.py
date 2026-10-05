"""
SQLAlchemy async database engine + session factory.

Dùng asyncpg driver cho async I/O với FastAPI.
Base declarative class dùng chung bởi tất cả ORM models.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base cho tất cả ORM models."""

    pass


def create_engine_and_session(database_url: str):
    """
    Factory function để tạo engine + session maker.
    Tách ra để test có thể override URL với test database.
    """
    engine = create_async_engine(
        database_url,
        echo=False,  # Set True để log SQL queries (DEBUG mode)
        pool_pre_ping=True,  # Kiểm tra connection health trước khi dùng
        pool_size=10,
        max_overflow=20,
    )
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Tránh lazy load issues với async
    )
    return engine, session_factory


# Module-level instances — sẽ được override trong lifespan startup
_engine = None
_session_factory = None


def init_db(database_url: str) -> None:
    """Khởi tạo engine và session factory với URL từ settings."""
    global _engine, _session_factory
    _engine, _session_factory = create_engine_and_session(database_url)


def get_engine():
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory


async def get_session() -> AsyncSession:
    """
    FastAPI dependency — inject async DB session vào routes.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_session)):
            ...
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
