from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter
from sqlmodel import select

from app.api.deps import DatabaseSession
from app.core.errors import AppError
from app.models import Feedback, FeedbackRating, Message, MessageRole, SessionRecord
from app.schemas.chat import FeedbackCreate, FeedbackRead
from app.schemas.common import ApiResponse

router = APIRouter(
    prefix="/sessions/{session_id}/messages",
    tags=["feedback"],
)


@router.post(
    "/{message_id}/feedback",
    response_model=ApiResponse[FeedbackRead],
)
def submit_feedback(
    session_id: UUID,
    message_id: UUID,
    payload: FeedbackCreate,
    db: DatabaseSession,
) -> ApiResponse[FeedbackRead]:
    if db.get(SessionRecord, session_id) is None:
        raise AppError(
            code="SESSION_NOT_FOUND",
            message="会话不存在。",
            status_code=404,
            details={"session_id": str(session_id)},
        )

    message = db.get(Message, message_id)
    if message is None:
        raise AppError(
            code="MESSAGE_NOT_FOUND",
            message="消息不存在。",
            status_code=404,
            details={"message_id": str(message_id)},
        )
    if message.session_id != session_id:
        raise AppError(
            code="MESSAGE_SESSION_MISMATCH",
            message="消息不属于当前会话。",
            status_code=409,
            details={
                "session_id": str(session_id),
                "message_id": str(message_id),
            },
        )
    if message.role != MessageRole.ASSISTANT:
        raise AppError(
            code="FEEDBACK_NOT_ALLOWED",
            message="只能对 AI 回复提交反馈。",
            status_code=422,
            details={
                "message_id": str(message_id),
                "role": message.role.value,
            },
        )

    feedback = db.exec(
        select(Feedback).where(Feedback.message_id == message_id)
    ).first()
    if feedback is None:
        feedback = Feedback(
            session_id=session_id,
            message_id=message_id,
            rating=FeedbackRating(payload.rating),
            reason=payload.reason.strip(),
        )
    else:
        feedback.rating = FeedbackRating(payload.rating)
        feedback.reason = payload.reason.strip()
        feedback.updated_at = datetime.now(timezone.utc)

    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return ApiResponse(data=FeedbackRead.model_validate(feedback))
