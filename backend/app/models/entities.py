from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, JSON, Text, Uuid
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCallStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TodoStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


class SessionRecord(SQLModel, table=True):
    __tablename__ = "sessions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(default="New conversation", max_length=120)
    role_id: str = Field(default="general", max_length=40, index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="sessions.id", index=True)
    role: MessageRole = Field(index=True)
    content: str = Field(sa_column=Column(Text, nullable=False))
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON, nullable=False),
    )
    created_at: datetime = Field(default_factory=utc_now, index=True)


class ToolCall(SQLModel, table=True):
    __tablename__ = "tool_calls"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="sessions.id", index=True)
    assistant_message_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            "message_id",
            Uuid,
            ForeignKey("messages.id"),
            nullable=True,
            index=True,
        ),
    )
    tool_message_id: UUID | None = Field(
        default=None,
        foreign_key="messages.id",
        index=True,
    )
    tool_name: str = Field(max_length=80, index=True)
    arguments: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    status: ToolCallStatus = Field(default=ToolCallStatus.PENDING, index=True)
    error_code: str | None = Field(default=None, max_length=80)
    error_message: str | None = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utc_now, index=True)
    completed_at: datetime | None = None


class Todo(SQLModel, table=True):
    __tablename__ = "todos"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="sessions.id", index=True)
    title: str = Field(max_length=500)
    status: TodoStatus = Field(default=TodoStatus.PENDING, index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now, index=True)
