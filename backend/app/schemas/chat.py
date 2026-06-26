from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.entities import MessageRole, ToolCallStatus


class SessionCreate(BaseModel):
    title: str = Field(default="New conversation", max_length=120)


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    role: MessageRole
    content: str
    created_at: datetime


class ToolCallRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    assistant_message_id: UUID | None
    tool_message_id: UUID | None
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | None
    status: ToolCallStatus
    error_code: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class SessionDetail(SessionRead):
    messages: list[MessageRead] = Field(default_factory=list)
    tool_calls: list[ToolCallRead] = Field(default_factory=list)


class ChatRequest(BaseModel):
    content: str
    provider: Literal["mock", "openai"] | None = None


class ChatResponse(BaseModel):
    user_message: MessageRead
    assistant_message: MessageRead
    tool_calls: list[ToolCallRead] = Field(default_factory=list)