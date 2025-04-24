from typing import Annotated, Any, Literal
from uuid import UUID

import orjson
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_core.runnables.schema import EventData
from pydantic import BaseModel, Field

from app.activity.agent import (
    Activity,
    ActivityBackground,
    ActivityProgress,
    # ActivityStep,
    OnboardingDataComplete,
)
from app.activity.create_from_concepts import create_activity_from_concepts
from app.activity.create_from_onboarding import (
    ActivityStep,
    PersonalContext,
    create_activities_from_onboarding_data,
)
from app.activity.dependencies import ActivityAgentDep, ActivityRepositoryDep
from app.activity.models import Activity as ActivityModel
from app.activity.models import ActivityLevel

chat_activity_router = APIRouter(prefix="/chat/activity")
onboarding_data_example = OnboardingDataComplete(
    profession="Software Engineer",
    age_range="30-39",
    life_stage="Professional",
    financial_goals=["Save for a house", "Build an emergency fund"],
    financial_interests=["Investing", "Budgeting"],
    financial_concerns=["Managing debt", "Saving enough"],
    financial_knowledge_level="Intermediate",
    personal_context=PersonalContext(
        hobbies=["reading", "cycling"],
        family_status="Single",
    ),
    previous_experience=[
        "Has invested in stocks",
        "Attended a finance workshop",
    ],
)

activity_example = Activity(
    title="Rapid Emergency Fund Blueprint for the Solo Engineer",
    description=(
        "Build a resilient emergency fund tailored to your single‑income, "
        "tech‑professional lifestyle so unexpected costs never derail your "
        "house‑saving plans."
    ),
    overall_objective=(
        "Have a fully funded, 6‑month emergency fund housed in the right account "
        "and an automated system to keep it on track."
    ),
    background=ActivityBackground(
        concepts=[
            "emergency fund",
            "living expenses",
            "liquidity",
            "opportunity cost",
        ],
        content=(
            "An emergency fund is a cash buffer (usually 3–6 months of essential "
            "living expenses) you can tap when life throws surprises—job loss, "
            "medical bills, bike repairs. Liquidity means how quickly you can "
            "access money without losing value; emergency funds need high liquidity "
            "(think high‑yield savings accounts). While cash earns less than "
            "investments (opportunity cost), it shields you from selling stocks at "
            "a loss. As a single software engineer, you rely solely on your income, "
            "so a 6‑month cushion minimizes risk and protects your bigger goal: "
            "buying a house."
        ),
    ),
    steps=[
        ActivityStep(
            index=1,
            title="Tally Your Core Living Expenses",
            content=(
                "Export the last 3 months of transactions from your bank or budgeting "
                "app. Write or code a quick script to categorize rent, food, utilities, "
                "insurance, transport, and minimum debt payments. Average each category "
                "to get one month of core costs."
            ),
            step_objective="Establish an accurate monthly baseline for essential expenses.",
        ),
        ActivityStep(
            index=2,
            title="Set Your Fund Size Target",
            content=(
                "Multiply the monthly core cost by 6 (or 4 if you feel your job is "
                "ultra‑stable, 9 if you want extra security). Note the final dollar "
                "amount; this is your emergency‑fund ‘definition of done’."
            ),
            step_objective="Define a specific, measurable emergency‑fund goal.",
        ),
        ActivityStep(
            index=3,
            title="Pick a Parking Spot",
            content=(
                "Compare at least two high‑yield savings accounts (HYSA) or "
                "money‑market funds. Prioritize FDIC/NCUA insurance, same‑day "
                "withdrawal, and APY. Open the chosen account and nickname it "
                "“Safety Net”."
            ),
            step_objective="Select a liquid, low‑risk account for the fund.",
        ),
        ActivityStep(
            index=4,
            title="Automate the Cashflow",
            content=(
                "Set up an automatic transfer from checking each payday for 10–15% "
                "of net income (adjust if you’re also allocating to house savings). "
                "Treat it like a non‑negotiable bill."
            ),
            step_objective=(
                "Create a default system that funds the emergency account without manual effort."
            ),
        ),
        ActivityStep(
            index=5,
            title="Stress‑Test & Reflect",
            content=(
                "Imagine a sudden layoff or $3k bike accident bill. Would 6 months "
                "feel sufficient? Journal one paragraph on your emotional reaction "
                "to these scenarios and any tweaks you’d make."
            ),
            step_objective=(
                "Evaluate psychological comfort and refine the target or timeline."
            ),
        ),
        ActivityStep(
            index=6,
            title="Schedule Quarterly Health Checks",
            content=(
                "Add a recurring calendar event to verify balance, APY, and "
                "contribution rate. Adjust if expenses or income change."
            ),
            step_objective=(
                "Ensure the fund stays right‑sized and optimized over time."
            ),
        ),
    ],
    glossary={
        "Emergency fund": "Cash reserve for unexpected expenses or income gaps.",
        "Liquidity": "Ease and speed of converting assets to cash without loss.",
        "Opportunity cost": "Potential gains you miss by choosing one option over another.",
        "HYSA": "High‑yield savings account offering higher interest than regular savings.",
    },
    alternative_methods=[
        "Use a paper ledger instead of a spreadsheet for expense tallying.",
        "If automation feels scary, set a monthly phone reminder to transfer funds manually.",
    ],
)


class ChatActivityRequest(BaseModel):
    """Request to chat activity."""

    thread_id: str = Field(
        description="ID of the thread to chat activity.",
    )
    message: str = Field(
        description="Message to chat activity.",
    )
    user_full_name: str | None = Field(
        description="Full name of the user.",
    )
    onboarding_data: OnboardingDataComplete = Field(
        description="Onboarding data to chat activity.",
        default=onboarding_data_example,
    )
    activity: Activity = Field(
        description="Activity to chat.",
        default=activity_example,
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


@chat_activity_router.post("/")
async def chat_activity(
    request: ChatActivityRequest,
    activity_agent: ActivityAgentDep,
):
    human_message = HumanMessage(content=request.message)

    async def stream_response():
        async for event in activity_agent.astream_events(
            stream_mode=["custom", "messages"],
            version="v2",
            config={
                "configurable": {
                    "thread_id": request.thread_id,
                    "user_full_name": request.user_full_name,
                },
                "run_name": "chat_activity",
            },
            input={
                "messages": [human_message],
                "onboarding_data": request.onboarding_data.model_dump(),
                "activity": request.activity.model_dump(),
                "progress": None,
            },
        ):
            if (
                event["event"] == "on_custom_event"
                and event["name"] == "progress_updated"
            ):
                data = event["data"]
                yield format_sse(
                    orjson.dumps(
                        data,
                    ).decode("utf-8"),
                    event="progress_updated",
                )

            if event["event"] == "on_chain_stream" and event["name"] == "chat_activity":
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

                if message_chunk.additional_kwargs.get("tool_calls", []):
                    continue

                if (
                    message_chunk.response_metadata.get("finish_reason", None)
                    == "tool_calls"
                ):
                    continue

                langgraph_node = metadata.get("langgraph_node", None)

                if langgraph_node == "chat_activity":
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


class ChatActivityStateRequest(BaseModel):
    """Request to chat activity state."""

    thread_id: str = Field(
        description="ID of the thread to chat activity state.",
    )


class GetStateResponse(BaseModel):
    messages: list[Message]
    onboarding_data: OnboardingDataComplete
    activity: Activity
    progress: ActivityProgress | None


@chat_activity_router.get("/")
async def get_state(
    activity_agent: ActivityAgentDep,
    request: ChatActivityStateRequest = Query(),
):
    config = {"configurable": {"thread_id": request.thread_id}}
    state = await activity_agent.aget_state(config=config)
    # return state
    messages = state.values["messages"]
    onboarding_data = OnboardingDataComplete.model_validate(
        state.values["onboarding_data"]
    )
    activity = Activity.model_validate(state.values["activity"])
    progress_data = state.values["progress"]
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
        "activity": activity.model_dump(),
        "progress": ActivityProgress.model_validate(progress_data)
        if progress_data
        else None,
    }


activity_router = APIRouter(prefix="/activity")


class CreateActivityFromOnboardingRequest(BaseModel):
    """Request to create activity from onboarding."""

    onboarding_data: OnboardingDataComplete = Field(
        description="Onboarding data to create activity from.",
        default=onboarding_data_example,
    )


class CreateActivityFromOnboardingResponse(BaseModel):
    type: Literal["onboarding"] = "onboarding"
    data: list[Activity]


@activity_router.post("/onboarding")
async def create_activity_from_onboarding(
    request: CreateActivityFromOnboardingRequest,
):
    activities = await create_activities_from_onboarding_data(request.onboarding_data)
    return CreateActivityFromOnboardingResponse(
        type="onboarding",
        data=activities.activities,
    )


class CreateActivityFromConceptsRequest(BaseModel):
    """Request to create activity from concepts."""

    level: Literal["Beginner", "Intermediate", "Advanced"] = Field(
        description="The level of the activity.",
    )
    concepts: list[str] = Field(
        description="A list of financial concepts to include in the activity.",
    )
    guided_description: str | None = Field(
        default=None,
        description="A guided description of the activity's context, background, or scenario.",
    )
    user_context: dict[str, Any] | None = Field(
        default=None,
        description="A dictionary of user information to personalize the activity.",
    )


class CreateActivityFromConceptsResponse(BaseModel):
    type: Literal["concepts"] = "concepts"
    data: Activity


@activity_router.post("/concepts")
async def create_activity_from_concepts_api(
    request: CreateActivityFromConceptsRequest,
):
    activity = await create_activity_from_concepts(
        level=request.level,
        concepts=request.concepts,
        guided_description=request.guided_description,
        user_context=request.user_context,
    )
    return CreateActivityFromConceptsResponse(
        type="concepts",
        data=activity,
    )


class CreatePublicActivityRequest(BaseModel):
    """Request to create a public activity."""

    title: str = Field(description="The name of the activity.")
    description: str = Field(
        description="A concise background summary for the activity."
    )
    overall_objective: str = Field(
        description="The main learning or practical objective of the activity."
    )
    background: ActivityBackground = Field(
        description="Contains concepts and content about the activity."
    )
    steps: list[ActivityStep] = Field(
        description="Detailed steps to complete the activity."
    )
    glossary: dict[str, str] | None = Field(
        default=None,
        description="A dictionary of key terms and their definitions.",
    )
    alternative_methods: list[str] | None = Field(
        default=None,
        description="Suggestions for non-technical or alternative ways to complete the activity.",
    )
    level: ActivityLevel = Field(
        description="The level of the activity (Beginner, Intermediate, Advanced)."
    )


class CreateUserActivityRequest(CreatePublicActivityRequest):
    """Request to create a user-specific activity."""

    user_id: str = Field(description="The ID of the user associated with the activity.")


class ActivityResponse(BaseModel):
    """Response for activity creation."""

    id: UUID
    title: str
    description: str
    level: str
    user_id: str | None


@activity_router.post("/public", response_model=ActivityResponse)
async def create_public_activity(
    request: CreatePublicActivityRequest,
    activity_repository: ActivityRepositoryDep,
):
    """Create a new public activity."""

    activity = ActivityModel(
        user_id=None,
        title=request.title,
        description=request.description,
        overall_objective=request.overall_objective,
        background=request.background.model_dump(),
        steps=request.steps,
        glossary=request.glossary,
        alternative_methods=request.alternative_methods,
        level=request.level,
    )

    try:
        created_activity = await activity_repository.create_public_activity(activity)
        return ActivityResponse(
            id=created_activity.id,
            title=created_activity.title,
            description=created_activity.description,
            level=created_activity.level,
            user_id=created_activity.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@activity_router.post("/user", response_model=ActivityResponse)
async def create_user_activity(
    request: CreateUserActivityRequest,
    activity_repository: ActivityRepositoryDep,
):
    """Create a new user-specific activity."""

    activity = ActivityModel(
        user_id=request.user_id,
        title=request.title,
        description=request.description,
        overall_objective=request.overall_objective,
        background=request.background.model_dump(),
        steps=request.steps,
        glossary=request.glossary,
        alternative_methods=request.alternative_methods,
        level=request.level,
    )

    try:
        created_activity = await activity_repository.create_user_activity(activity)
        return ActivityResponse(
            id=created_activity.id,
            title=created_activity.title,
            description=created_activity.description,
            level=created_activity.level,
            user_id=created_activity.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ActivityListResponse(BaseModel):
    """Response for activity listing."""

    data: list[ActivityResponse]


@activity_router.get("/public", response_model=ActivityListResponse)
async def get_public_activities(
    activity_repository: ActivityRepositoryDep,
):
    """Get all public activities."""

    activities = await activity_repository.get_public_activities()
    return ActivityListResponse(
        data=[
            ActivityResponse(
                id=activity.id,
                title=activity.title,
                description=activity.description,
                level=activity.level,
                user_id=activity.user_id,
            )
            for activity in activities
        ]
    )


@activity_router.get("/user/{user_id}", response_model=ActivityListResponse)
async def get_user_activities(
    user_id: str,
    activity_repository: ActivityRepositoryDep,
):
    """Get all activities for a specific user."""

    activities = await activity_repository.get_user_activities(user_id)
    return ActivityListResponse(
        data=[
            ActivityResponse(
                id=activity.id,
                title=activity.title,
                description=activity.description,
                level=activity.level,
                user_id=activity.user_id,
            )
            for activity in activities
        ]
    )


@activity_router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: UUID,
    activity_repository: ActivityRepositoryDep,
):
    """Get an activity by ID."""

    activity = await activity_repository.get_activity(str(activity_id))
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    return ActivityResponse(
        id=activity.id,
        title=activity.title,
        description=activity.description,
        level=activity.level,
        user_id=activity.user_id,
    )
