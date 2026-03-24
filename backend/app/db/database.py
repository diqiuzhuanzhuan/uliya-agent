from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


class MemoryRecord(Base):
    __tablename__ = "memory_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[str]
    role: Mapped[str]
    content: Mapped[str]
    created_at: Mapped[str]


class ThreadRecord(Base):
    __tablename__ = "thread_records"

    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    created_at: Mapped[str]
    updated_at: Mapped[str]


class TraceRecord(Base):
    __tablename__ = "trace_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[str]
    run_id: Mapped[str]
    event_type: Mapped[str]
    payload: Mapped[str]
    created_at: Mapped[str]


class UploadRecord(Base):
    __tablename__ = "upload_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[str | None]
    filename: Mapped[str]
    stored_path: Mapped[str]
    preview: Mapped[str]
    created_at: Mapped[str]


settings = get_settings()
sqlite_path = settings.sqlite_path
sqlite_path.parent.mkdir(parents=True, exist_ok=True)
engine: AsyncEngine = create_async_engine(
    f"sqlite+aiosqlite:///{sqlite_path}",
    future=True,
    echo=False,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
