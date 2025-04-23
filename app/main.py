from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.config import settings
from app.onboarding.router import router as onboarding_router


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    from app.activity.agent import get_graph as get_activity_graph
    from app.onboarding.agent import get_graph as get_onboarding_graph

    async with AsyncPostgresSaver.from_conn_string(
        settings.DATABASE_URI_PSYCOPG.encoded_string()
    ) as checkpointer:
        await checkpointer.setup()
        yield {
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
)


@app.post("/health")
async def health():
    return {"status": "ok"}


app.include_router(prefix="/api/v1", router=onboarding_router)
