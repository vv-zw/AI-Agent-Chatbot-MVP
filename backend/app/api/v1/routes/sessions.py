import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse
from sqlmodel import select

from app.agents.service import AgentService
from app.api.deps import DatabaseSession
from app.core.config import get_settings
from app.core.errors import AppError, error_payload
from app.models import Message, MessageRole, SessionRecord, Todo, ToolCall
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    MessageRead,
    SessionCreate,
    SessionDetail,
    SessionRead,
    SessionRoleUpdate,
    ToolCallRead,
)
from app.schemas.common import ApiResponse
from app.schemas.roles import RoleRead
from app.services.roles import get_role, validate_role_id

router = APIRouter(prefix="/sessions", tags=["sessions"])
logger = logging.getLogger(__name__)


def sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def split_content(content: str, chunk_size: int = 12) -> list[str]:
    return [
        content[index : index + chunk_size]
        for index in range(0, len(content), chunk_size)
    ]


def get_session_or_404(db: DatabaseSession, session_id: UUID) -> SessionRecord:
    session_record = db.get(SessionRecord, session_id)
    if session_record is None:
        raise AppError(
            code="SESSION_NOT_FOUND",
            message="会话不存在。",
            status_code=404,
            details={"session_id": str(session_id)},
        )
    return session_record


def role_read(role_id: str) -> RoleRead:
    role = get_role(role_id)
    return RoleRead(**role.__dict__)


def session_read(record: SessionRecord) -> SessionRead:
    payload = SessionRead.model_validate(record).model_dump()
    payload["role"] = role_read(record.role_id)
    return SessionRead(**payload)


@router.get("", response_model=ApiResponse[list[SessionRead]])
def list_sessions(db: DatabaseSession) -> ApiResponse[list[SessionRead]]:
    records = db.exec(
        select(SessionRecord).order_by(SessionRecord.updated_at.desc())
    ).all()
    return ApiResponse(data=[session_read(record) for record in records])


@router.post(
    "",
    response_model=ApiResponse[SessionRead],
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: SessionCreate,
    db: DatabaseSession,
) -> ApiResponse[SessionRead]:
    title = payload.title.strip()
    if not title:
        raise AppError(
            code="VALIDATION_ERROR",
            message="会话标题不能为空。",
            status_code=422,
        )
    role_id = validate_role_id(payload.role_id)
    record = SessionRecord(title=title, role_id=role_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return ApiResponse(data=session_read(record))


@router.get("/{session_id}", response_model=ApiResponse[SessionDetail])
def get_session(
    session_id: UUID,
    db: DatabaseSession,
) -> ApiResponse[SessionDetail]:
    record = get_session_or_404(db, session_id)
    messages = db.exec(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    ).all()
    tool_calls = db.exec(
        select(ToolCall)
        .where(ToolCall.session_id == session_id)
        .order_by(ToolCall.created_at)
    ).all()
    return ApiResponse(
        data=SessionDetail(
            **session_read(record).model_dump(),
            messages=[MessageRead.model_validate(item) for item in messages],
            tool_calls=[ToolCallRead.model_validate(item) for item in tool_calls],
        )
    )


@router.patch("/{session_id}/role", response_model=ApiResponse[SessionRead])
def update_session_role(
    session_id: UUID,
    payload: SessionRoleUpdate,
    db: DatabaseSession,
) -> ApiResponse[SessionRead]:
    record = get_session_or_404(db, session_id)
    record.role_id = validate_role_id(payload.role_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return ApiResponse(data=session_read(record))


@router.delete("/{session_id}", response_model=ApiResponse[dict[str, str]])
def delete_session(
    session_id: UUID,
    db: DatabaseSession,
) -> ApiResponse[dict[str, str]]:
    record = get_session_or_404(db, session_id)

    for model in (ToolCall, Message, Todo):
        items = db.exec(select(model).where(model.session_id == session_id)).all()
        for item in items:
            db.delete(item)

    db.delete(record)
    db.commit()
    return ApiResponse(data={"id": str(session_id), "status": "deleted"})


@router.post(
    "/{session_id}/messages",
    response_model=ApiResponse[ChatResponse],
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    session_id: UUID,
    payload: ChatRequest,
    db: DatabaseSession,
) -> ApiResponse[ChatResponse]:
    record = get_session_or_404(db, session_id)
    settings = get_settings()
    content = payload.content.strip()
    if not content:
        raise AppError(
            code="EMPTY_MESSAGE",
            message="消息内容不能为空。",
            status_code=422,
        )
    if len(content) > settings.max_user_message_length:
        raise AppError(
            code="MESSAGE_TOO_LONG",
            message=f"消息长度不能超过 {settings.max_user_message_length} 个字符。",
            status_code=422,
            details={"max_length": settings.max_user_message_length},
        )

    response = AgentService(settings).run(db, record, content, provider_name=payload.provider)
    return ApiResponse(data=response)


@router.post("/{session_id}/messages/stream")
def stream_message(
    session_id: UUID,
    payload: ChatRequest,
    db: DatabaseSession,
) -> StreamingResponse:
    record = get_session_or_404(db, session_id)
    settings = get_settings()
    content = payload.content.strip()
    if not content:
        raise AppError(
            code="EMPTY_MESSAGE",
            message="消息内容不能为空。",
            status_code=422,
        )
    if len(content) > settings.max_user_message_length:
        raise AppError(
            code="MESSAGE_TOO_LONG",
            message=f"消息长度不能超过 {settings.max_user_message_length} 个字符。",
            status_code=422,
            details={"max_length": settings.max_user_message_length},
        )

    user_message = Message(
        session_id=record.id,
        role=MessageRole.USER,
        content=content,
    )
    record.updated_at = datetime.now(timezone.utc)
    if record.title == "New conversation":
        record.title = content[:40]
    db.add(user_message)
    db.add(record)
    db.commit()
    db.refresh(user_message)
    saved_user = MessageRead.model_validate(user_message).model_dump(mode="json")

    async def event_stream() -> AsyncIterator[str]:
        try:
            yield sse_event("user_message_saved", {"user_message": saved_user})
            await asyncio.sleep(0)
            response = AgentService(settings).run(
                db,
                record,
                content,
                provider_name=payload.provider,
                user_message=user_message,
            )
            payload_data = response.model_dump(mode="json")
            for sequence, tool_call in enumerate(payload_data["tool_calls"], 1):
                pending_call = {
                    **tool_call,
                    "assistant_message_id": None,
                    "tool_message_id": None,
                    "result": None,
                    "status": "pending",
                    "error_code": None,
                    "error_message": None,
                    "completed_at": None,
                }
                yield sse_event(
                    "tool_call_start",
                    {"sequence": sequence, "tool_call": pending_call},
                )
                await asyncio.sleep(0.05)
                yield sse_event(
                    "tool_call_result",
                    {"sequence": sequence, "tool_call": tool_call},
                )
            for delta in split_content(payload_data["assistant_message"]["content"]):
                yield sse_event("assistant_delta", {"delta": delta})
                await asyncio.sleep(0.04 if payload.provider in (None, "mock") else 0)
            yield sse_event("assistant_done", payload_data)
        except AppError as exc:
            db.rollback()
            yield sse_event("error", error_payload(exc.code, exc.message, exc.details))
        except Exception as exc:
            db.rollback()
            logger.exception("Streaming message failed", exc_info=exc)
            yield sse_event("error", error_payload("STREAM_FAILED", "流式回复失败，请稍后重试。"))

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
