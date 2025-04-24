import uuid
from enum import StrEnum
from typing import Any, Literal

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel


class ActivityLevel(StrEnum):
    Beginner = "beginner"
    Intermediate = "intermediate"
    Advanced = "advanced"


class Activity(SQLModel, table=True):
    __tablename__ = "activities"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True,
        index=True,
        nullable=False,
        description="Unique identifier for the activity.",
    )
    user_id: str | None = Field(
        nullable=True,
        description="The ID of the user associated with the activity.",
    )
    title: str = Field(nullable=False, description="The name of the activity.")
    description: str = Field(
        nullable=False, description="A concise background summary for the activity."
    )
    overall_objective: str = Field(
        nullable=False,
        description="The main learning or practical objective of the activity.",
    )
    background: dict[str, Any] = Field(
        sa_column=Column(JSONB, nullable=False),
    )
    steps: list[Any] = Field(
        sa_column=Column(JSONB, nullable=False),
    )
    glossary: dict[str, str] | None = Field(
        sa_column=Column(JSONB, nullable=True),
        default=None,
        description="A dictionary of key terms and their definitions.",
    )
    alternative_methods: list[str] | None = Field(
        sa_column=Column(JSONB, nullable=True),
        default=None,
        description="Suggestions for non-technical or alternative ways to complete the activity.",
    )
    level: ActivityLevel = Field(
        default="Beginner", nullable=False, description="The level of the activity."
    )
