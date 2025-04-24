from typing import Annotated, Any, Literal

import orjson
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_core.runnables.schema import EventData
from pydantic import BaseModel, Field

from app.onboarding.agent import OnboardingData
from app.onboarding.dependencies import OnboaringAgentDep


class ChatOnboardingRequest(BaseModel):
    """Request to chat onboarding."""

    thread_id: str = Field(
        description="ID of the thread to chat onboarding.",
    )
    message: str = Field(
        description="Message to chat onboarding.",
    )
    user_full_name: str | None = Field(
        default=None,
        description="Full name of the user.",
    )


class ChatOnboardingStateRequest(BaseModel):
    """Request to chat onboarding state."""

    thread_id: str = Field(
        description="ID of the thread to chat onboarding state.",
    )


def format_sse(data: str, event: str | None = None) -> bytes:
    """Format a message as an SSE event."""
    msg = ""
    if event:
        msg += f"event: {event}\n"
    for line in data.rstrip().splitlines():
        msg += f"data: {line}\n"
    msg += "\n"
    return msg.encode("utf-8")


router = APIRouter(prefix="/chat/onboarding")


@router.post("/")
async def chat_onboarding(
    request: ChatOnboardingRequest,
    agent: OnboaringAgentDep,
):
    """
    Interact with the onboarding agent in a streaming conversation.
    
    Sends a user message to the onboarding agent and returns the agent's response as a server-sent
    event stream. The stream includes AI message chunks and an onboarding completion event when
    the onboarding process is complete.
    
    The onboarding agent helps gather financial information about the user through conversation,
    which is later used to personalize financial activities.
    
    Returns:
        StreamingResponse: A streaming response with AI message chunks and onboarding completion events.
    """
    human_message = HumanMessage(content=request.message)

    async def stream_response():
        async for event in agent.astream_events(
            stream_mode=["custom", "messages"],
            version="v2",
            config={
                "configurable": {
                    "thread_id": request.thread_id,
                    "user_full_name": request.user_full_name,
                },
                "run_name": "chat_onboarding",
            },
            input={
                "messages": [human_message],
            },
        ):
            if (
                event["event"] == "on_custom_event"
                and event["name"] == "onboarding_completed"
            ):
                data = event["data"]
                yield format_sse(
                    orjson.dumps(
                        data,
                    ).decode("utf-8"),
                    event="onboarding_completed",
                )

            if (
                event["event"] == "on_chain_stream"
                and event["name"] == "chat_onboarding"
            ):
                data: EventData | Any = event["data"]
                chunk = data["chunk"]

                if not isinstance(chunk, tuple):
                    continue

                _, message_chunk = chunk

                if not isinstance(message_chunk, tuple):
                    continue

                message_chunk, metadata = message_chunk

                if not isinstance(message_chunk, AIMessageChunk):
                    continue

                langgraph_node = metadata.get("langgraph_node", None)

                if langgraph_node == "chat_onboarding":
                    yield format_sse(
                        orjson.dumps(
                            {
                                "id": message_chunk.id,
                                "content": message_chunk.content,
                                "response_metadata": message_chunk.response_metadata,
                            },
                        ).decode("utf-8"),
                        event="ai_message_chunk",
                    )

    return StreamingResponse(stream_response(), media_type="text/event-stream")


class HumanMessageData(BaseModel):
    type: Literal["human"] = "human"
    id: str
    content: str


class AIMessageData(BaseModel):
    type: Literal["ai"] = "ai"
    id: str
    content: str


Message = Annotated[HumanMessageData | AIMessageData, Field(discriminator="type")]


class GetStateResponse(BaseModel):
    messages: list[Message]
    onboarding_data: OnboardingData


@router.get("/", response_model=GetStateResponse)
async def get_state(
    agent: OnboaringAgentDep,
    request: ChatOnboardingStateRequest = Query(),
):
    """
    Retrieve the current state of an onboarding chat thread.
    
    Fetches the conversation history and collected onboarding data for a specific chat thread.
    This endpoint is useful for resuming onboarding conversations or accessing the financial
    information collected during the onboarding process.
    
    Returns:
        GetStateResponse: The current state of the onboarding chat thread including messages
                          and collected onboarding data.
    """
    config = {"configurable": {"thread_id": request.thread_id}}
    state = await agent.aget_state(config=config)
    messages = state.values["messages"]
    onboarding_data = state.values["onboarding_data"]
    return {
        "messages": [
            {
                "id": message.id,
                "type": message.type,
                "content": message.content,
            }
            for message in messages
            if message.type in ["human", "ai"]
        ],
        "onboarding_data": onboarding_data.model_dump(),
    }
