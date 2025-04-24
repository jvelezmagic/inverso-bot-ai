from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, insert, select

from app.activity.models import Activity


class ActivityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_activity(self, id: str) -> Activity | None:
        query = select(Activity).where(Activity.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_public_activities(self) -> list[Activity]:
        query = select(Activity).where(col(Activity.user_id).is_(None))
        results = await self.session.execute(query)
        return list(results.scalars().all())

    async def get_user_activities(self, user_id: str) -> list[Activity]:
        query = select(Activity).where(Activity.user_id == user_id)
        results = await self.session.execute(query)
        return list(results.scalars().all())

    async def create_public_activity(self, activity: Activity) -> Activity:
        query = select(Activity).where(Activity.id == str(activity.id))
        result = await self.session.execute(query)

        if result.scalar_one_or_none():
            raise ValueError("Activity already exists")

        self.session.add(activity)
        await self.session.commit()
        return activity

    async def create_user_activity(self, activity: Activity) -> Activity:
        query = select(Activity).where(Activity.id == str(activity.id))
        result = await self.session.execute(query)

        if result.scalar_one_or_none():
            raise ValueError("Activity already exists")

        if activity.user_id is None:
            raise ValueError("Activity must have a user_id")

        self.session.add(activity)
        await self.session.commit()
        return activity

    async def create_public_activities(
        self, activities: list[Activity]
    ) -> list[Activity]:
        if any(activity.user_id is not None for activity in activities):
            raise ValueError("All activities must be public")

        data: list[dict[str, Any]] = []

        for activity in activities:
            data.append(activity.model_dump())

        query = insert(Activity).values(data)
        await self.session.execute(query)
        await self.session.commit()
        return activities

    async def create_user_activities(
        self, activities: list[Activity]
    ) -> list[Activity]:
        if any(activity.user_id is None for activity in activities):
            raise ValueError("All activities must have a user_id")

        data: list[dict[str, Any]] = []

        for activity in activities:
            data.append(activity.model_dump())

        query = insert(Activity).values(data)
        await self.session.execute(query)
        await self.session.commit()
        return activities
