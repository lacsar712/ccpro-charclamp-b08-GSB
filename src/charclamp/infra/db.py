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


# 已存在的卷上 create_all 不会为既有表补建新增索引（含部分唯一索引），
# 因此显式幂等补建，保证老部署也获得并发硬约束。
_PARTIAL_INDEX_DDL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_burn_shift_one_open_per_clamp "
    "ON burn_shifts (clamp_id) WHERE peak_temp_c IS NULL"
)


def sync_create_all() -> None:
    Base.metadata.create_all(sync_engine)
    with sync_engine.begin() as conn:
        conn.execute(text(_PARTIAL_INDEX_DDL))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
