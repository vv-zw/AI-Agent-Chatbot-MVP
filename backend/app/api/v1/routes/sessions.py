from uuid import UUID

from fastapi import APIRouter, status
from sqlmodel import select

from app.agents.service import AgentService
from app.api.deps import DatabaseSession
from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Message, SessionRecord, ToolCall
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    MessageRead,
    SessionCreate,
    SessionDetail,
    SessionRead,
    ToolCallRead,
)
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


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


@router.get("", response_model=ApiResponse[list[SessionRead]])
def list_sessions(db: DatabaseSession) -> ApiResponse[list[SessionRecord]]:
    records = db.exec(
        select(SessionRecord).order_by(SessionRecord.updated_at.desc())
    ).all()
    return ApiResponse(data=list(records))


@router.post(
    "",
    response_model=ApiResponse[SessionRead],
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: SessionCreate,
    db: DatabaseSession,
) -> ApiResponse[SessionRecord]:
    title = payload.title.strip()
    if not title:
        raise AppError(
            code="VALIDATION_ERROR",
            message="会话标题不能为空。",
            status_code=422,
        )
    record = SessionRecord(title=title)
    db.add(record)
    db.commit()
    db.refresh(record)
    return ApiResponse(data=record)


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
            **SessionRead.model_validate(record).model_dump(),
            messages=[MessageRead.model_validate(item) for item in messages],
            tool_calls=[ToolCallRead.model_validate(item) for item in tool_calls],
        )
    )


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

    response = AgentService(settings).run(db, record, content)
    return ApiResponse(data=response)