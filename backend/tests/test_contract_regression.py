import json

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from conftest import TEST_ENGINE


def send_message(
    client: TestClient,
    session_id: str,
    content: str,
    provider: str | None = None,
):
    payload = {"content": content}
    if provider is not None:
        payload["provider"] = provider
    return client.post(f"/api/v1/sessions/{session_id}/messages", json=payload)


def test_tests_use_isolated_in_memory_sqlite_database(client: TestClient) -> None:
    client.post("/api/v1/sessions", json={"title": "isolated test db"})

    assert TEST_ENGINE.url.drivername == "sqlite"
    assert TEST_ENGINE.url.database is None
    assert {"sessions", "messages", "tool_calls", "todos"} <= set(
        inspect(TEST_ENGINE).get_table_names()
    )


def test_tool_call_response_contains_frontend_display_data(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_message(client, session_id, "calculate (8 + 4) / 3")

    assert response.status_code == 201
    data = response.json()["data"]
    tool_call = data["tool_calls"][0]

    assert tool_call["id"]
    assert tool_call["session_id"] == session_id
    assert tool_call["assistant_message_id"] == data["assistant_message"]["id"]
    assert tool_call["tool_message_id"]
    assert tool_call["tool_name"] == "calculator"
    assert tool_call["arguments"] == {"expression": "(8 + 4) / 3"}
    assert tool_call["result"] == {"expression": "(8 + 4) / 3", "value": "4"}
    assert tool_call["status"] == "succeeded"
    assert tool_call["error_code"] is None
    assert tool_call["error_message"] is None

    detail = client.get(f"/api/v1/sessions/{session_id}").json()["data"]
    tool_messages = [
        message for message in detail["messages"] if message["role"] == "tool"
    ]
    assert len(tool_messages) == 1

    tool_message_payload = json.loads(tool_messages[0]["content"])
    assert tool_message_payload["tool_name"] == "calculator"
    assert tool_message_payload["arguments"] == tool_call["arguments"]
    assert tool_message_payload["result"] == tool_call["result"]
    assert tool_message_payload["status"] == "succeeded"


def test_failed_tool_call_response_and_tool_message_are_structured(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_message(client, session_id, "calculate 1 / 0")

    assert response.status_code == 201
    tool_call = response.json()["data"]["tool_calls"][0]
    assert tool_call["tool_name"] == "calculator"
    assert tool_call["status"] == "failed"
    assert tool_call["error_code"] == "TOOL_ARGUMENT_INVALID"
    assert tool_call["result"]["error"]["code"] == "TOOL_ARGUMENT_INVALID"
    assert "reason" in tool_call["result"]["error"]["details"]

    detail = client.get(f"/api/v1/sessions/{session_id}").json()["data"]
    tool_message = next(
        message for message in detail["messages"] if message["role"] == "tool"
    )
    payload = json.loads(tool_message["content"])
    assert payload["status"] == "failed"
    assert payload["tool_name"] == "calculator"
    assert payload["error_code"] == "TOOL_ARGUMENT_INVALID"
    assert payload["result"]["error"]["code"] == "TOOL_ARGUMENT_INVALID"


def test_message_request_rejects_invalid_provider_with_unified_error(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_message(client, session_id, "hello", provider="deepseek")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert "data" not in payload
    assert payload["error"]["details"][0]["loc"] == ["body", "provider"]
