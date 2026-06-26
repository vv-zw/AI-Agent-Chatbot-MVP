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
    response = send_message(client, session_id, "你好，简单介绍一下你自己。")

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["user_message"]["content"] == "你好，简单介绍一下你自己。"
    assert data["assistant_message"]["role"] == "assistant"
    assert "Mock AI 助手" in data["assistant_message"]["content"]
    assert data["tool_calls"] == []


def test_time_tool_call(client: TestClient, session_id: str) -> None:
    response = send_message(client, session_id, "现在几点？")

    assert response.status_code == 201
    tool_call = response.json()["data"]["tool_calls"][0]
    assert tool_call["tool_name"] == "get_current_time"
    assert tool_call["status"] == "succeeded"
    assert set(tool_call["result"]) == {"date", "time", "timezone", "weekday"}

def test_mock_lists_available_tools(client: TestClient, session_id: str) -> None:
    response = send_message(client, session_id, "你都有哪些工具可以调用")

    assert response.status_code == 201
    data = response.json()["data"]
    assert "Mock 模式目前可以演示基础聊天和 3 个本地工具" in data["assistant_message"]["content"]
    assert "get_current_time" in data["assistant_message"]["content"]
    assert "calculator" in data["assistant_message"]["content"]
    assert "todo_tool" in data["assistant_message"]["content"]
    assert data["tool_calls"] == []


def test_mock_describes_current_mode_features(client: TestClient, session_id: str) -> None:
    for prompt in (
        "你现在的这个模式都能实现哪些功能",
        "你都能做什么，可以完成哪些工具调用",
        "你都能做什么",
        "你有什么能力",
        "Mock 模式支持什么功能",
    ):
        response = send_message(client, session_id, prompt)

        assert response.status_code == 201
        content = response.json()["data"]["assistant_message"]["content"]
        assert "基础聊天" in content
        assert "get_current_time" in content
        assert "calculator" in content
        assert "todo_tool" in content


def test_mock_intro_short_phrase(client: TestClient, session_id: str) -> None:
    response = send_message(client, session_id, "介绍自己")

    assert response.status_code == 201
    content = response.json()["data"]["assistant_message"]["content"]
    assert "Mock AI 助手" in content
    assert "待办" in content


def test_mock_short_todo_lists_items(client: TestClient, session_id: str) -> None:
    response = send_message(client, session_id, "待办")

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["tool_calls"][0]["tool_name"] == "todo_tool"
    assert data["tool_calls"][0]["status"] == "succeeded"
    assert "待办" in data["assistant_message"]["content"]

def test_calculator_tool_call(client: TestClient, session_id: str) -> None:
    response = send_message(client, session_id, "帮我算一下 128 * 36 + 520")

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["tool_calls"][0]["tool_name"] == "calculator"
    assert data["tool_calls"][0]["result"]["value"] == "5128"
    assert "= 5128" in data["assistant_message"]["content"]


def test_todo_create_and_list(client: TestClient, session_id: str) -> None:
    created = send_message(client, session_id, "帮我记一个待办：明天提交笔试项目")
    assert created.status_code == 201
    assert created.json()["data"]["tool_calls"][0]["result"]["todo"]["title"] == "明天提交笔试项目"

    listed = send_message(client, session_id, "我有哪些待办？")
    assert listed.status_code == 201
    todos = listed.json()["data"]["tool_calls"][0]["result"]["todos"]
    assert [todo["title"] for todo in todos] == ["明天提交笔试项目"]

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
            "details": {},
        }
    }


def test_session_not_found_error(client: TestClient) -> None:
    missing_id = str(uuid4())
    response = send_message(client, missing_id, "你好")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"
    assert response.json()["error"]["details"] == {"session_id": missing_id}


def test_invalid_calculation_is_returned_and_recorded(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_message(client, session_id, "计算 2 + abc")

    assert response.status_code == 201
    data = response.json()["data"]
    tool_call = data["tool_calls"][0]
    assert tool_call["tool_name"] == "calculator"
    assert tool_call["status"] == "failed"
    assert tool_call["error_code"] == "TOOL_ARGUMENT_INVALID"
    assert tool_call["error_message"] == "表达式格式不正确。"
    assert "调用失败" in data["assistant_message"]["content"]

    detail = client.get(f"/api/v1/sessions/{session_id}").json()["data"]
    assert detail["tool_calls"][0]["status"] == "failed"
    tool_messages = [item for item in detail["messages"] if item["role"] == "tool"]
    assert len(tool_messages) == 1
    assert '"status":"failed"' in tool_messages[0]["content"]


def test_message_too_long_error(client: TestClient, session_id: str) -> None:
    response = send_message(client, session_id, "x" * 10_001)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MESSAGE_TOO_LONG"


def test_mock_remembers_project_name_in_current_session(
    client: TestClient,
    session_id: str,
) -> None:
    first = send_message(client, session_id, "我这个项目叫 ToolMind Chatbot。")
    second = send_message(client, session_id, "我刚刚说项目叫什么？")

    assert first.status_code == 201
    assert second.status_code == 201
    assert "ToolMind Chatbot" in second.json()["data"]["assistant_message"]["content"]


def test_framework_http_errors_use_unified_format(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "ROUTE_NOT_FOUND",
            "message": "请求的接口不存在。",
            "details": {"status_code": 404},
        }
    }

def test_validation_error_does_not_echo_raw_input(client: TestClient) -> None:
    secret_input = "sk-test-sensitive-value"
    response = client.post(
        "/api/v1/sessions",
        json={"title": {"unexpected": secret_input}},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert secret_input not in response.text
    assert set(payload["error"]["details"][0]) == {"type", "loc", "msg"}


def test_unhandled_error_response_hides_internal_details(
    client: TestClient,
    session_id: str,
    monkeypatch,
) -> None:
    from app.api.v1.routes import sessions

    leaked_detail = "C:\\private\\project\\.env sk-secret-key"

    def fail_run(*args, **kwargs):
        raise RuntimeError(leaked_detail)

    monkeypatch.setattr(sessions.AgentService, "run", fail_run)
    response = send_message(client, session_id, "触发服务端异常")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "服务暂时不可用，请稍后重试。",
            "details": {},
        }
    }
    assert leaked_detail not in response.text


def test_localhost_and_loopback_frontends_are_allowed_by_cors(client: TestClient) -> None:
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_messages_and_tool_calls_are_isolated_by_session(client: TestClient) -> None:
    first = client.post("/api/v1/sessions", json={}).json()["data"]["id"]
    second = client.post("/api/v1/sessions", json={}).json()["data"]["id"]

    sent = send_message(client, first, "现在几点？")
    assert sent.status_code == 201

    first_detail = client.get(f"/api/v1/sessions/{first}").json()["data"]
    second_detail = client.get(f"/api/v1/sessions/{second}").json()["data"]
    assert len(first_detail["messages"]) == 3
    assert len(first_detail["tool_calls"]) == 1
    assert second_detail["messages"] == []
    assert second_detail["tool_calls"] == []

def test_delete_session_removes_related_records(client: TestClient, session_id: str) -> None:
    sent = send_message(client, session_id, "现在几点？")
    assert sent.status_code == 201

    deleted = client.delete(f"/api/v1/sessions/{session_id}")
    assert deleted.status_code == 200
    assert deleted.json()["data"] == {"id": session_id, "status": "deleted"}

    detail = client.get(f"/api/v1/sessions/{session_id}")
    assert detail.status_code == 404

    listed = client.get("/api/v1/sessions")
    assert session_id not in [item["id"] for item in listed.json()["data"]]
