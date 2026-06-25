import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.agents import service as agent_service
from app.llm.base import LLMResult, ToolCallRequest
from app.models import Message, MessageRole, Todo, ToolCall
from app.tools.registry import ToolArgumentError, ToolContext, tool_registry
from conftest import TEST_ENGINE


class FixedToolProvider:
    def __init__(self, name: Any, arguments: Any) -> None:
        self.name = name
        self.arguments = arguments

    def complete(self, messages: list[dict[str, str]]) -> LLMResult:
        return LLMResult(
            tool_call=ToolCallRequest(
                name=self.name,
                arguments=self.arguments,
            )
        )

    def complete_with_tool_result(
        self,
        messages: list[dict[str, str]],
        tool_name: str,
        result: dict[str, Any],
    ) -> str:
        if result["status"] == "failed":
            return f"工具调用失败：{result['error_message']}"
        return "工具调用成功。"


def use_provider(
    monkeypatch: pytest.MonkeyPatch,
    provider: FixedToolProvider,
) -> None:
    monkeypatch.setattr(agent_service, "get_llm_provider", lambda settings: provider)


def send_message(client: TestClient, session_id: str, content: str = "测试工具"):
    return client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": content},
    )


def test_registry_exposes_whitelisted_tool_schemas() -> None:
    definitions = {item.name: item for item in tool_registry.definitions()}

    assert set(definitions) == {"get_current_time", "calculator", "todo_tool"}
    for definition in definitions.values():
        assert definition.description
        assert definition.parameters_schema["type"] == "object"
        assert callable(definition.executor)
        assert definition.result_description
        assert definition.failure_description

    assert definitions["calculator"].parameters_schema["required"] == ["expression"]
    assert definitions["todo_tool"].parameters_schema["required"] == ["action"]


def test_calculator_rejects_invalid_expression_and_zero_division(
    session_id: str,
) -> None:
    with Session(TEST_ENGINE) as db:
        context = ToolContext(db=db, session_id=session_id)
        with pytest.raises(ToolArgumentError, match="工具参数不合法"):
            tool_registry.execute("calculator", {"expression": "2 + abc"}, context)
        with pytest.raises(ToolArgumentError, match="除数不能为零"):
            tool_registry.execute("calculator", {"expression": "1 / 0"}, context)
        with pytest.raises(ToolArgumentError):
            tool_registry.execute("calculator", {"expression": 123}, context)
        with pytest.raises(ToolArgumentError):
            tool_registry.execute("calculator", {}, context)
        with pytest.raises(ToolArgumentError):
            tool_registry.execute("todo_tool", {"action": "create"}, context)


def test_calculator_zero_division_is_structured_and_persisted(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_message(client, session_id, "计算 1 / 0")

    assert response.status_code == 201
    tool_call = response.json()["data"]["tool_calls"][0]
    assert tool_call["status"] == "failed"
    assert tool_call["error_code"] == "TOOL_ARGUMENT_INVALID"
    assert tool_call["error_message"] == "除数不能为零。"
    assert tool_call["arguments"] == {"expression": "1 / 0"}
    assert tool_call["result"]["error"]["details"] == {"reason": "除数不能为零。"}


def test_unregistered_tool_call_does_not_crash_api(
    client: TestClient,
    session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_provider(monkeypatch, FixedToolProvider("dangerous_tool", {}))

    response = send_message(client, session_id)

    assert response.status_code == 201
    tool_call = response.json()["data"]["tool_calls"][0]
    assert tool_call["tool_name"] == "dangerous_tool"
    assert tool_call["status"] == "failed"
    assert tool_call["error_code"] == "TOOL_NOT_FOUND"
    assert "未注册或未启用" in tool_call["error_message"]


def test_malformed_tool_arguments_do_not_crash_api(
    client: TestClient,
    session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_provider(monkeypatch, FixedToolProvider("calculator", ["1 + 1"]))

    response = send_message(client, session_id)

    assert response.status_code == 201
    tool_call = response.json()["data"]["tool_calls"][0]
    assert tool_call["arguments"] == {"_raw": ["1 + 1"]}
    assert tool_call["status"] == "failed"
    assert tool_call["error_code"] == "TOOL_ARGUMENT_INVALID"


def test_tool_call_and_tool_message_are_persisted(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_message(client, session_id, "计算 (8 + 4) / 3")
    assert response.status_code == 201
    returned = response.json()["data"]["tool_calls"][0]

    with Session(TEST_ENGINE) as db:
        stored_call = db.exec(select(ToolCall)).one()
        stored_message = db.exec(
            select(Message).where(Message.role == MessageRole.TOOL)
        ).one()

        assert str(stored_call.session_id) == session_id
        assert stored_call.tool_name == "calculator"
        assert stored_call.arguments == {"expression": "(8 + 4) / 3"}
        assert stored_call.result == {"expression": "(8 + 4) / 3", "value": "4"}
        assert stored_call.status.value == "succeeded"
        assert stored_call.assistant_message_id is not None
        assert stored_call.tool_message_id == stored_message.id
        assert stored_call.created_at is not None
        assert stored_call.completed_at is not None

        payload = json.loads(stored_message.content)
        assert payload["tool_name"] == "calculator"
        assert payload["arguments"] == stored_call.arguments
        assert payload["status"] == "succeeded"
        assert payload["result"] == stored_call.result

    assert returned["tool_message_id"] == str(stored_message.id)


def test_todos_are_isolated_by_session(client: TestClient) -> None:
    first = client.post("/api/v1/sessions", json={}).json()["data"]["id"]
    second = client.post("/api/v1/sessions", json={}).json()["data"]["id"]

    created = send_message(client, first, "帮我记一个待办：只属于第一个会话")
    assert created.status_code == 201
    listed_second = send_message(client, second, "我有哪些待办")
    assert listed_second.status_code == 201
    assert listed_second.json()["data"]["tool_calls"][0]["result"]["todos"] == []

    with Session(TEST_ENGINE) as db:
        todos = db.exec(select(Todo)).all()
        assert len(todos) == 1
        assert str(todos[0].session_id) == first
