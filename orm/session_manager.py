import contextlib
import os
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from .base_model import OrmBase


#Base = declarative_base()


class DatabaseSessionManager:
    def __init__(self) -> None:
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None

    def init(self, db_url: str) -> None:
        # Just additional example of customization.
        # you can add parameters to init and so on
        if "postgresql" in db_url:
            # These settings are needed to work with pgbouncer in transaction mode
            # because you can't use prepared statements in such case
            connect_args = {
                "statement_cache_size": 0,
                "prepared_statement_cache_size": 0,
            }
        else:
            connect_args = {}
        self._engine = create_async_engine(
            url=db_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )

    async def init_db(self) -> None:
        async with db_manager.connect() as connection:
            #await connection.run_sync(OrmBase.metadata.drop_all)
            await connection.run_sync(OrmBase.metadata.create_all)

    async def close(self) -> None:
        if self._engine is None:
            return
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise IOError("DatabaseSessionManager is not initialized")
        async with self._sessionmaker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise IOError("DatabaseSessionManager is not initialized")
        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise


async def get_session() -> AsyncSession:
    async with db_manager.session() as session:
        yield session


db_manager = DatabaseSessionManager()
