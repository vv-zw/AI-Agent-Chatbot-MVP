from uuid import uuid4

from fastapi.testclient import TestClient


def send_message(client: TestClient, session_id: str, content: str):
    return client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": content},
    )


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok", "provider": "mock"}}


def test_create_list_and_get_session(client: TestClient) -> None:
    created = client.post("/api/v1/sessions", json={"title": "测试会话"})
    assert created.status_code == 201
    session = created.json()["data"]
    assert session["title"] == "测试会话"

    listed = client.get("/api/v1/sessions")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["data"]] == [session["id"]]

    detail = client.get(f"/api/v1/sessions/{session['id']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["messages"] == []
    assert detail.json()["data"]["tool_calls"] == []


def test_send_normal_mock_message(client: TestClient, session_id: str) -> None:
    response = send_message(client, session_id, "你好，介绍一下自己")

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["user_message"]["content"] == "你好，介绍一下自己"
    assert data["assistant_message"]["role"] == "assistant"
    assert data["assistant_message"]["content"].startswith("[Mock]")
    assert data["tool_calls"] == []


def test_time_tool_call(client: TestClient, session_id: str) -> None:
    response = send_message(client, session_id, "现在几点")

    assert response.status_code == 201
    tool_call = response.json()["data"]["tool_calls"][0]
    assert tool_call["tool_name"] == "get_current_time"
    assert tool_call["status"] == "succeeded"
    assert set(tool_call["result"]) == {"date", "time", "timezone", "weekday"}


def test_calculator_tool_call(client: TestClient, session_id: str) -> None:
    response = send_message(client, session_id, "帮我算 (12.5 + 7.5) / 4")

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["tool_calls"][0]["tool_name"] == "calculator"
    assert data["tool_calls"][0]["result"]["value"] == "5"
    assert "= 5" in data["assistant_message"]["content"]


def test_todo_create_and_list(client: TestClient, session_id: str) -> None:
    created = send_message(client, session_id, "帮我记一个待办：补充接口文档")
    assert created.status_code == 201
    assert created.json()["data"]["tool_calls"][0]["result"]["todo"]["title"] == "补充接口文档"

    listed = send_message(client, session_id, "我有哪些待办")
    assert listed.status_code == 201
    todos = listed.json()["data"]["tool_calls"][0]["result"]["todos"]
    assert [todo["title"] for todo in todos] == ["补充接口文档"]

    detail = client.get(f"/api/v1/sessions/{session_id}").json()["data"]
    assert any(message["role"] == "tool" for message in detail["messages"])
    assert len(detail["tool_calls"]) == 2


def test_empty_message_error(client: TestClient, session_id: str) -> None:
    response = send_message(client, session_id, "   ")

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "EMPTY_MESSAGE",
            "message": "消息内容不能为空。",
            "details": None,
        }
    }


def test_session_not_found_error(client: TestClient) -> None:
    missing_id = str(uuid4())
    response = send_message(client, missing_id, "你好")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"
    assert response.json()["error"]["details"] == {"session_id": missing_id}


def test_invalid_calculation_is_rejected_and_recorded(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_message(client, session_id, "计算 2 + abc")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TOOL_ARGUMENT_INVALID"

    detail = client.get(f"/api/v1/sessions/{session_id}").json()["data"]
    assert detail["tool_calls"][0]["tool_name"] == "calculator"
    assert detail["tool_calls"][0]["status"] == "failed"
    assert detail["tool_calls"][0]["error_code"] == "TOOL_ARGUMENT_INVALID"


def test_message_too_long_error(client: TestClient, session_id: str) -> None:
    response = send_message(client, session_id, "x" * 10_001)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MESSAGE_TOO_LONG"