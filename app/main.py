from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from scalar_fastapi import get_scalar_api_reference  # type: ignore
from sqlalchemy import text

from app.activity.router import activity_router as activity_router
from app.activity.router import chat_activity_router
from app.config import settings
from app.database.models import initialize_database
from app.database.session import SessionLocal
from app.onboarding.router import router as onboarding_router


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    from app.activity.agent import get_graph as get_activity_graph
    from app.onboarding.agent import get_graph as get_onboarding_graph

    await initialize_database()
    async with AsyncPostgresSaver.from_conn_string(
        settings.DATABASE_URI_PSYCOPG.encoded_string()
    ) as checkpointer:
        await checkpointer.setup()
        yield {
            "checkpointer": checkpointer,
            "onboarding_agent": get_onboarding_graph(checkpointer=checkpointer),
            "activity_agent": get_activity_graph(checkpointer=checkpointer),
        }


async def validate_inverso_api_key(
    x_inverso_api_key: Annotated[str | None, Header()] = None,
):
    if x_inverso_api_key != settings.INVERSO_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid x-inverso-api-key header",
        )


app = FastAPI(
    title="InversoAI API",
    summary="Personalized financial education platform with interactive AI-powered learning experiences",
    description="""\
# InversoAI: Personalized Financial Education Platform

InversoAI aims to democratize financial education by creating a highly personalized learning
experience that adapts to each user's unique background, goals, and knowledge level. We make
financial concepts accessible through interactive conversations and tailored activities that
connect directly to users' real-life situations.

## Key Features

- **Personalized onboarding**: Collects user information through a conversational interface,
    gathering details about life stage, profession, age, financial goals, interests, concerns,
    and knowledge level.

- **Activity generation**: Creates tailored financial learning activities based on the user's
    profile, ensuring that content is relevant to their specific situation.

- **Interactive guidance**: Provides step-by-step coaching through financial activities, using
    conversation to explain concepts, answer questions, and adapt to the user's pace and understanding.

- **Progress tracking**: Monitors user progress through activities, marking steps as "Not started,"
    "In progress," or "Completed" to maintain momentum.

- **Knowledge building**: Builds financial literacy progressively, with activities that range from
    beginner to advanced levels, ensuring continuous learning and development.


## API Authentication

All API endpoints require authentication using the `x-inverso-api-key` header.
    """,
    lifespan=lifespan,
    dependencies=[Depends(validate_inverso_api_key)],
    redoc_url=None,
    docs_url=None,
    version="1.0.0",
)


@app.post("/health")
async def health():
    """
    Check the health status of the API and database connection.

    Performs a simple database connectivity test by executing a lightweight query.
    This endpoint is used for monitoring the system's operational status and
    can be integrated with health check systems or load balancers.

    Returns:
        dict: A status object with "ok" value indicating the system is functioning properly.

    Raises:
        HTTPException: If the database connection fails, an exception will be raised,
                      resulting in a non-200 status code response.
    """
    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    """
    Serve the Scalar API reference documentation.

    Generates and serves an interactive API documentation interface using Scalar.
    This endpoint is hidden from the schema but provides a user-friendly way to
    explore and test the API endpoints.

    Returns:
        HTML content: The Scalar API reference UI with the OpenAPI specification loaded.
    """
    if app.openapi_url is None:
        return

    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="InversoAI API - Personalized Financial Education Platform",
    )


app.include_router(prefix="/api/v1", router=onboarding_router)
app.include_router(prefix="/api/v1", router=chat_activity_router)
app.include_router(prefix="/api/v1", router=activity_router)
