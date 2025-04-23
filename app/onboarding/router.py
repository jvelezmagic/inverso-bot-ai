import orjson
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage
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
        async for message_chunk, metadata in agent.astream(
            stream_mode="messages",
            config={
                "configurable": {"thread_id": request.thread_id},
                "run_name": "chat_onboarding",
            },
            input={
                "messages": [human_message],
            },
        ):
            if not metadata["langgraph_node"] == "chat_onboarding":  # type: ignore
                continue

            if not isinstance(message_chunk, AIMessageChunk):
                continue

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
