from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, status
from sqlmodel import select

from app.api.deps import DatabaseSession
from app.core.errors import AppError
from app.models import Message, SessionRecord, ToolCall
from app.models.entities import MessageRole
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
            message="Session does not exist.",
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
    record = SessionRecord(title=payload.title.strip())
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
    content = payload.content.strip()
    if not content:
        raise AppError(
            code="EMPTY_MESSAGE",
            message="Message content cannot be empty.",
            status_code=422,
        )

    user_message = Message(
        session_id=session_id,
        role=MessageRole.USER,
        content=content,
    )
    assistant_message = Message(
        session_id=session_id,
        role=MessageRole.ASSISTANT,
        content=f"[Mock] I received: {content}",
    )
    record.updated_at = datetime.now(timezone.utc)
    if record.title == "New conversation":
        record.title = content[:40]

    db.add(user_message)
    db.add(assistant_message)
    db.add(record)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    return ApiResponse(
        data=ChatResponse(
            user_message=MessageRead.model_validate(user_message),
            assistant_message=MessageRead.model_validate(assistant_message),
            tool_calls=[],
        )
    )

