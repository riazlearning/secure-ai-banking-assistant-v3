"""PostgreSQL checkpoint storage and connection lifecycle."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from banking_assistant.core.config import Settings


@asynccontextmanager
async def create_checkpointer(settings: Settings) -> AsyncIterator[AsyncPostgresSaver]:
    conninfo = make_conninfo(
        host=settings.postgres_host,
        port=settings.postgres_port,
        dbname=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password,
        connect_timeout=10,
    )
    connection_pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]] = AsyncConnectionPool(
        conninfo=conninfo,
        min_size=1,
        max_size=10,
        open=False,
        timeout=10,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
    )
    async with connection_pool as pool:
        await pool.wait(timeout=10)
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()
        yield checkpointer
