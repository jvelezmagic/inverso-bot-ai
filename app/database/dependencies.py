from collections.abc import AsyncGenerator
from typing import Annotated, cast

from fastapi import Depends, Request
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import SessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def get_checkpointer(request: Request) -> AsyncGenerator[AsyncPostgresSaver]:
    yield cast(AsyncPostgresSaver, request.state.checkpointer)


CheckpointerDep = Annotated[AsyncPostgresSaver, Depends(get_checkpointer)]
