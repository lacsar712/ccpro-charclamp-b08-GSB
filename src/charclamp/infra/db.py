from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from charclamp.domain.models import Base

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://charclamp:charclamp@127.0.0.1:6150/charclamp",
)
DATABASE_URL_SYNC = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://charclamp:charclamp@127.0.0.1:6150/charclamp",
)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

sync_engine = create_engine(DATABASE_URL_SYNC, echo=False)
SyncSessionLocal = sessionmaker(sync_engine, expire_on_commit=False, class_=Session)


def sync_create_all() -> None:
    Base.metadata.create_all(sync_engine)


def sync_ensure_open_shift_index() -> None:
    """对已存在的数据卷幂等补建「每窑至多一条空峰值班次」的部分唯一索引。"""
    ddl = (
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_burn_shift_open_per_clamp "
        "ON burn_shifts (clamp_id) WHERE peak_temp_c IS NULL"
    )
    with sync_engine.begin() as conn:
        conn.execute(text(ddl))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
