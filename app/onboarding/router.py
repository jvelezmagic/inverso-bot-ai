from typing import Any

import orjson
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_core.runnables.schema import EventData
from pydantic import BaseModel, Field

from app.onboarding.dependencies import OnboaringAgentDep


class ChatOnboardingRequest(BaseModel):
    """Request to chat onboarding."""

    thread_id: str = Field(
        description="ID of the thread to chat onboarding.",
    )
    message: str = Field(
        description="Message to chat onboarding.",
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
    human_message = HumanMessage(content=request.message)

    async def stream_response():
        async for event in agent.astream_events(
            stream_mode=["custom", "messages"],
            version="v2",
            config={
                "configurable": {"thread_id": request.thread_id},
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
