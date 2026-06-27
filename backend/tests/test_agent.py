import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.agents.service import build_context
from app.core.config import Settings
from app.core.llm_provider_state import runtime_llm_provider_state
from app.models import Message, MessageRole, SessionRecord
from app.tools.registry import ToolContext, ToolNotFoundError, tool_registry
from conftest import TEST_ENGINE


def test_context_builder_keeps_recent_roles() -> None:
    with Session(TEST_ENGINE) as db:
        record = SessionRecord(title="上下文测试")
        db.add(record)
        db.flush()
        for role, content in (
            (MessageRole.USER, "第一条"),
            (MessageRole.ASSISTANT, "第二条"),
            (MessageRole.TOOL, '{"value":"3"}'),
            (MessageRole.ASSISTANT, "第四条"),
        ):
            db.add(Message(session_id=record.id, role=role, content=content))
            db.flush()

        context = build_context(db, record.id, limit=3)

    assert context == [
        {
            "role": "system",
            "content": "你是通用助手，适合日常问答和任务处理。回答要清晰、友好、直接，在需要时主动拆解步骤并给出可执行建议。",
        },
        {"role": "assistant", "content": "第二条"},
        {"role": "tool", "content": '{"value":"3"}'},
        {"role": "assistant", "content": "第四条"},
    ]


def test_missing_api_key_returns_unified_error(
    client: TestClient,
    session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api.v1.routes import sessions

    runtime_llm_provider_state.reset("openai")
    monkeypatch.setattr(
        sessions,
        "get_settings",
        lambda: Settings(llm_provider="mock", openai_api_key=None),
    )
    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "你好"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LLM_CONFIGURATION_ERROR"
    assert "OPENAI_API_KEY" in response.json()["error"]["details"]["missing"]


def test_unregistered_tool_is_rejected() -> None:
    with Session(TEST_ENGINE) as db:
        record = SessionRecord(title="工具测试")
        db.add(record)
        db.flush()
        with pytest.raises(ToolNotFoundError):
            tool_registry.execute(
                "dangerous_tool",
                {},
                ToolContext(db=db, session_id=record.id),
            )
