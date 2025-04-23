from typing import Annotated, cast

from fastapi import Depends, Request
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


async def get_checkpointer(request: Request):
    return cast(AsyncPostgresSaver, request.state.checkpointer)


CheckpointerDep = Annotated[AsyncPostgresSaver, Depends(get_checkpointer)]
