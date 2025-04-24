from collections.abc import AsyncGenerator
from typing import Annotated, cast

from fastapi import Depends, Request
from langgraph.graph.state import CompiledStateGraph

from app.activity.repository import ActivityRepository
from app.database.dependencies import SessionDep


async def get_activity_agent(
    request: Request,
) -> CompiledStateGraph:
    return cast(CompiledStateGraph, request.state.activity_agent)


async def get_activity_repository(
    session: SessionDep,
) -> AsyncGenerator[ActivityRepository]:
    yield ActivityRepository(session)


ActivityAgentDep = Annotated[CompiledStateGraph, Depends(get_activity_agent)]
ActivityRepositoryDep = Annotated[ActivityRepository, Depends(get_activity_repository)]
