from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status
from scalar_fastapi import get_scalar_api_reference  # type: ignore

from app.activity.router import activity_router as activity_router
from app.activity.router import chat_activity_router
from app.config import settings
from app.database.models import initialize_database
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
    lifespan=lifespan,
    dependencies=[Depends(validate_inverso_api_key)],
    redoc_url=None,
    docs_url=None,
)


@app.post("/health")
async def health():
    return {"status": "ok"}


@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    if app.openapi_url is None:
        return

    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title="InversoAI API",
    )


app.include_router(prefix="/api/v1", router=onboarding_router)
app.include_router(prefix="/api/v1", router=chat_activity_router)
app.include_router(prefix="/api/v1", router=activity_router)
