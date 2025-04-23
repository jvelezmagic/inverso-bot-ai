import datetime
from enum import StrEnum

from sqlmodel import Field, Relationship, SQLModel


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Thread(SQLModel, table=True):
    __tablename__ = "threads"  # type: ignore

    id: int = Field(default=None, primary_key=True)
    title: str | None = Field(default=None)
    created_at: datetime.datetime = Field(default=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default=datetime.datetime.now)

    messages: list["Message"] = Relationship(
        back_populates="thread",
        cascade_delete=True,
    )


class Message(SQLModel, table=True):
    __tablename__ = "messages"  # type: ignore
    id: int = Field(default=None, primary_key=True)
    thread_id: int = Field(default=None)
    message: str = Field(default=None)
    message_role: MessageRole = Field()
    created_at: datetime.datetime = Field(default=datetime.datetime.now)
    updated_at: datetime.datetime = Field(default=datetime.datetime.now)

    thread: Thread = Relationship(back_populates="messages")
