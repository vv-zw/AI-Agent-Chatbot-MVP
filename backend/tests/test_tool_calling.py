import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.agents import service as agent_service
from app.llm.base import LLMResult, ToolCallRequest
from app.models import Message, MessageRole, Todo, ToolCall
from app.tools.registry import (
    ToolArgumentError,
    ToolContext,
    ToolExecutionError,
    tool_registry,
)
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
    monkeypatch.setattr(agent_service, "get_llm_provider", lambda settings, provider_name=None: provider)


def send_message(client: TestClient, session_id: str, content: str = "测试工具"):
    return client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": content},
    )


def test_registry_exposes_whitelisted_tool_schemas() -> None:
    definitions = {item.name: item for item in tool_registry.definitions()}

    assert set(definitions) == {"get_current_time", "calculator", "todo_tool", "knowledge_search"}
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

class MultiToolProvider:
    def __init__(self, calls: tuple[ToolCallRequest, ...]) -> None:
        self.calls = calls
        self.final_messages: list[dict[str, str]] = []
        self.final_results: list[dict[str, Any]] = []

    def complete(self, messages: list[dict[str, str]]) -> LLMResult:
        return LLMResult(tool_calls=self.calls)

    def complete_with_tool_results(
        self,
        messages: list[dict[str, str]],
        results: list[dict[str, Any]],
    ) -> str:
        self.final_messages = messages
        self.final_results = results
        failed = [item for item in results if item["status"] == "failed"]
        return f"已完成 {len(results)} 项工具调用，其中 {len(failed)} 项失败。"


def test_single_tool_call_remains_available(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_message(client, session_id, "现在几点？")

    assert response.status_code == 201
    calls = response.json()["data"]["tool_calls"]
    assert len(calls) == 1
    assert calls[0]["tool_name"] == "get_current_time"
    assert calls[0]["status"] == "succeeded"


def test_mock_time_and_calculation_are_executed_in_request_order(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_message(
        client,
        session_id,
        "现在几点？顺便帮我算一下 128 * 36 + 520",
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert [item["tool_name"] for item in data["tool_calls"]] == [
        "get_current_time",
        "calculator",
    ]
    assert all(item["status"] == "succeeded" for item in data["tool_calls"])
    assert data["tool_calls"][1]["result"]["value"] == "5128"
    assert "已按顺序完成 2 项工具调用" in data["assistant_message"]["content"]


def test_mock_todo_create_then_list_sees_new_todo(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_message(
        client,
        session_id,
        "帮我记一个待办：提交 README，然后看看我有哪些待办",
    )

    assert response.status_code == 201
    calls = response.json()["data"]["tool_calls"]
    assert [(item["tool_name"], item["arguments"]["action"]) for item in calls] == [
        ("todo_tool", "create"),
        ("todo_tool", "list"),
    ]
    assert calls[0]["arguments"]["title"] == "提交 README"
    assert [item["title"] for item in calls[1]["result"]["todos"]] == ["提交 README"]


def test_multi_tool_partial_failure_persists_all_calls_and_tool_context(
    client: TestClient,
    session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = MultiToolProvider(
        (
            ToolCallRequest(name="get_current_time", arguments={}),
            ToolCallRequest(name="calculator", arguments={"expression": "1 / 0"}),
            ToolCallRequest(name="missing_tool", arguments={}),
        )
    )
    use_provider(monkeypatch, provider)

    response = send_message(client, session_id)

    assert response.status_code == 201
    data = response.json()["data"]
    assert [item["status"] for item in data["tool_calls"]] == [
        "succeeded",
        "failed",
        "failed",
    ]
    assert [item["error_code"] for item in data["tool_calls"]] == [
        None,
        "TOOL_ARGUMENT_INVALID",
        "TOOL_NOT_FOUND",
    ]
    assert "2 项失败" in data["assistant_message"]["content"]
    assert len(provider.final_results) == 3
    assert [message["role"] for message in provider.final_messages].count("tool") == 3

    with Session(TEST_ENGINE) as db:
        stored_calls = db.exec(select(ToolCall).order_by(ToolCall.created_at)).all()
        tool_messages = db.exec(
            select(Message)
            .where(Message.role == MessageRole.TOOL)
            .order_by(Message.created_at)
        ).all()
        assert len(stored_calls) == 3
        assert len(tool_messages) == 3
        assert all(item.tool_message_id is not None for item in stored_calls)
        assert all(item.assistant_message_id is not None for item in stored_calls)


def test_mock_todo_create_then_time_uses_independent_arguments(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_message(
        client,
        session_id,
        "帮我记一个待办：明天提交笔试项目，然后告诉我现在几点",
    )

    assert response.status_code == 201
    calls = response.json()["data"]["tool_calls"]
    assert [item["tool_name"] for item in calls] == ["todo_tool", "get_current_time"]
    assert calls[0]["arguments"] == {
        "action": "create",
        "title": "明天提交笔试项目",
    }
    assert calls[1]["arguments"] == {}


def test_multi_tool_execution_failure_does_not_stop_later_tools(
    client: TestClient,
    session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_execute = tool_registry.execute

    def execute_with_failure(
        name: str,
        arguments: Any,
        context: ToolContext,
    ) -> dict[str, Any]:
        if name == "calculator":
            raise ToolExecutionError("模拟执行器故障。")
        return original_execute(name, arguments, context)

    monkeypatch.setattr(tool_registry, "execute", execute_with_failure)
    provider = MultiToolProvider(
        (
            ToolCallRequest(name="calculator", arguments={"expression": "2 + 2"}),
            ToolCallRequest(name="get_current_time", arguments={}),
        )
    )
    use_provider(monkeypatch, provider)

    response = send_message(client, session_id)

    assert response.status_code == 201
    calls = response.json()["data"]["tool_calls"]
    assert [item["status"] for item in calls] == ["failed", "succeeded"]
    assert calls[0]["error_code"] == "TOOL_EXECUTION_FAILED"
    assert calls[0]["error_message"] == "模拟执行器故障。"
    assert calls[1]["result"]["timezone"] == "Asia/Shanghai"
