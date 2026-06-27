import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.models import KnowledgeChunk, KnowledgeFile


SUPPORTED_KNOWLEDGE_EXTENSIONS = {".txt", ".md", ".csv", ".json"}
KNOWLEDGE_CONTENT_TYPES = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
}
SUMMARY_TERMS = ("总结", "概括", "主要内容", "核心内容", "摘要")
QUERY_NOISE = (
    "根据我上传的文件", "根据上传的文件", "我上传的文件", "这个文档里",
    "这份文档里", "文档中", "文件中", "请问", "一下",
)


def normalize_filename(filename: str | None) -> tuple[str, str]:
    safe_name = Path(filename or "").name.strip()
    return safe_name, Path(safe_name).suffix.lower()


def decode_text(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("文件必须使用 UTF-8 编码。") from exc


def split_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", normalized) if item.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        pieces = [paragraph[index:index + chunk_size] for index in range(0, len(paragraph), chunk_size)]
        for piece in pieces:
            candidate = f"{current}\n\n{piece}".strip() if current else piece
            if len(candidate) <= chunk_size:
                current = candidate
            elif current:
                chunks.append(current)
                current = f"{current[-overlap:]}\n\n{piece}".strip()
            else:
                chunks.append(piece)
    if current:
        chunks.append(current)
    return chunks


def _terms(value: str) -> set[str]:
    lowered = value.lower()
    words = set(re.findall(r"[a-z0-9_+#.-]{2,}", lowered))
    for run in re.findall(r"[\u4e00-\u9fff]+", lowered):
        for width in (2, 3):
            words.update(run[index:index + width] for index in range(len(run) - width + 1))
    return words


def _clean_query(query: str) -> str:
    cleaned = query.strip()
    for noise in QUERY_NOISE:
        cleaned = cleaned.replace(noise, "")
    for term in SUMMARY_TERMS:
        cleaned = cleaned.replace(term, "")
    return cleaned.strip("，。！？!?：: ")


def search_knowledge(db: Session, session_id: UUID, query: str, top_k: int = 3) -> dict[str, Any]:
    files = db.exec(select(KnowledgeFile).where(KnowledgeFile.session_id == session_id)).all()
    if not files:
        return {
            "matched_chunks": [], "status": "no_files",
            "message": "当前会话还没有知识库文件，请先上传 .txt、.md、.csv 或 .json 文件。",
        }

    filenames = {item.id: item.filename for item in files}
    chunks = db.exec(
        select(KnowledgeChunk).where(KnowledgeChunk.session_id == session_id)
        .order_by(KnowledgeChunk.created_at, KnowledgeChunk.chunk_index)
    ).all()
    cleaned_query = _clean_query(query)
    query_terms = _terms(cleaned_query)
    is_summary = any(term in query for term in SUMMARY_TERMS) or not query_terms
    scored: list[tuple[float, KnowledgeChunk, str]] = []
    for chunk in chunks:
        chunk_lower = chunk.content.lower()
        matches = sorted(query_terms & _terms(chunk_lower), key=len, reverse=True)
        score = len(matches) / max(len(query_terms), 1) * 0.7
        if cleaned_query and cleaned_query.lower() in chunk_lower:
            score += 0.5
        if cleaned_query:
            score += SequenceMatcher(None, cleaned_query.lower(), chunk_lower[:1200]).ratio() * 0.3
        if is_summary:
            score = max(score, 0.1 / (chunk.chunk_index + 1))
            reason = "概要问题，优先返回文档开头片段"
        elif matches:
            reason = f"匹配关键词：{', '.join(matches[:5])}"
        elif score >= 0.16:
            reason = "文本内容与问题近似"
        else:
            continue
        scored.append((min(score, 1.0), chunk, reason))

    scored.sort(key=lambda item: (-item[0], item[1].chunk_index))
    matched = [{
        "filename": filenames[chunk.file_id], "chunk_index": chunk.chunk_index,
        "chunk_text": chunk.content, "score": round(score, 4), "match_reason": reason,
    } for score, chunk, reason in scored[:top_k]]
    return {
        "matched_chunks": matched,
        "status": "matched" if matched else "no_matches",
        "message": f"找到 {len(matched)} 个相关片段。" if matched else "知识库中没有找到与当前问题相关的片段。",
    }
