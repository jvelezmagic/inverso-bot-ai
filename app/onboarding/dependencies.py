from typing import Annotated, cast

from fastapi import Depends, Request
from langgraph.graph.state import CompiledStateGraph


async def get_onboarding_agent(
    request: Request,
) -> CompiledStateGraph:
    return cast(CompiledStateGraph, request.state.onboarding_agent)


OnboaringAgentDep = Annotated[CompiledStateGraph, Depends(get_onboarding_agent)]
