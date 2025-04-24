from sqlmodel import SQLModel

from app.activity.models import Activity


def get_models():
    return [Activity]


async def initialize_database():
    from app.database.session import engine

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


__all__ = ["initialize_database"]
