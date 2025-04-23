from typing import Annotated, cast

from fastapi import Depends, Request
from langgraph.graph.state import CompiledStateGraph


async def get_activity_agent(
    request: Request,
) -> CompiledStateGraph:
    return cast(CompiledStateGraph, request.state.activity_agent)


ActivityAgentDep = Annotated[CompiledStateGraph, Depends(get_activity_agent)]
