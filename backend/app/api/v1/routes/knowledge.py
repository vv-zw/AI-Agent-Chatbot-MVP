from uuid import UUID

from fastapi import APIRouter, File, UploadFile, status
from sqlmodel import func, select

from app.api.deps import DatabaseSession
from app.core.config import get_settings
from app.core.errors import AppError
from app.models import KnowledgeChunk, KnowledgeFile, SessionRecord
from app.schemas.common import ApiResponse
from app.schemas.knowledge import KnowledgeFileRead
from app.services.knowledge import (
    KNOWLEDGE_CONTENT_TYPES,
    SUPPORTED_KNOWLEDGE_EXTENSIONS,
    decode_text,
    normalize_filename,
    split_text,
)

router = APIRouter(prefix="/sessions/{session_id}/knowledge", tags=["knowledge"])


def _get_session(db: DatabaseSession, session_id: UUID) -> SessionRecord:
    record = db.get(SessionRecord, session_id)
    if record is None:
        raise AppError(
            code="SESSION_NOT_FOUND", message="会话不存在。", status_code=404,
            details={"session_id": str(session_id)},
        )
    return record


def _file_read(db: DatabaseSession, record: KnowledgeFile) -> KnowledgeFileRead:
    count = db.exec(
        select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.file_id == record.id)
    ).one()
    return KnowledgeFileRead(**record.model_dump(), chunk_count=count)


@router.get("/files", response_model=ApiResponse[list[KnowledgeFileRead]])
def list_knowledge_files(session_id: UUID, db: DatabaseSession) -> ApiResponse[list[KnowledgeFileRead]]:
    _get_session(db, session_id)
    records = db.exec(
        select(KnowledgeFile).where(KnowledgeFile.session_id == session_id)
        .order_by(KnowledgeFile.created_at.desc())
    ).all()
    return ApiResponse(data=[_file_read(db, item) for item in records])


@router.post(
    "/files", response_model=ApiResponse[KnowledgeFileRead],
    status_code=status.HTTP_201_CREATED,
)
async def upload_knowledge_file(
    session_id: UUID,
    db: DatabaseSession,
    file: UploadFile = File(...),
) -> ApiResponse[KnowledgeFileRead]:
    _get_session(db, session_id)
    settings = get_settings()
    filename, extension = normalize_filename(file.filename)
    if not filename or extension not in SUPPORTED_KNOWLEDGE_EXTENSIONS:
        raise AppError(
            code="UNSUPPORTED_FILE_TYPE",
            message="仅支持 .txt、.md、.csv 和 .json 文本文件。",
            status_code=415,
            details={"filename": filename or None},
        )

    raw = await file.read(settings.max_knowledge_file_size + 1)
    await file.close()
    if len(raw) > settings.max_knowledge_file_size:
        raise AppError(
            code="FILE_TOO_LARGE",
            message=f"文件不能超过 {settings.max_knowledge_file_size // 1024} KB。",
            status_code=413,
            details={"max_size": settings.max_knowledge_file_size},
        )
    if not raw:
        raise AppError(code="EMPTY_FILE", message="上传的文件为空。", status_code=422)
    try:
        text = decode_text(raw)
    except ValueError as exc:
        raise AppError(
            code="INVALID_TEXT_ENCODING", message=str(exc), status_code=422,
        ) from exc
    chunks = split_text(text)
    if not chunks:
        raise AppError(code="EMPTY_FILE", message="文件没有可检索的文本内容。", status_code=422)

    record = KnowledgeFile(
        session_id=session_id, filename=filename,
        content_type=KNOWLEDGE_CONTENT_TYPES[extension], size=len(raw),
    )
    db.add(record)
    db.flush()
    for index, content in enumerate(chunks):
        db.add(KnowledgeChunk(
            file_id=record.id, session_id=session_id,
            chunk_index=index, content=content,
        ))
    db.commit()
    db.refresh(record)
    return ApiResponse(data=_file_read(db, record))
