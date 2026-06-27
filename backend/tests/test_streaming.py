import json
from typing import Any

from fastapi.testclient import TestClient

from app.core.errors import AppError


def send_stream(
    client: TestClient,
    session_id: str,
    content: str,
    provider: str = "mock",
):
    return client.post(
        f"/api/v1/sessions/{session_id}/messages/stream",
        json={"content": content, "provider": provider},
    )


def parse_events(body: str) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    for block in body.replace("\r\n", "\n").strip().split("\n\n"):
        event = next(line[6:].strip() for line in block.splitlines() if line.startswith("event:"))
        data = "\n".join(line[5:].lstrip() for line in block.splitlines() if line.startswith("data:"))
        events.append((event, json.loads(data)))
    return events


def test_stream_endpoint_returns_mock_delta_events(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_stream(client, session_id, "hello streaming")
    events = parse_events(response.text)
    names = [name for name, _ in events]

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert names[0] == "user_message_saved"
    assert names[-1] == "assistant_done"
    assert names.count("assistant_delta") >= 2
    deltas = "".join(data["delta"] for name, data in events if name == "assistant_delta")
    assert deltas == events[-1][1]["assistant_message"]["content"]


def test_stream_tool_events_are_ordered_and_persisted(
    client: TestClient,
    session_id: str,
) -> None:
    response = send_stream(client, session_id, "calculate 2 + 3")
    events = parse_events(response.text)
    names = [name for name, _ in events]

    assert names.index("tool_call_start") < names.index("tool_call_result")
    assert names.index("tool_call_result") < names.index("assistant_delta")
    start = next(data for name, data in events if name == "tool_call_start")
    result = next(data for name, data in events if name == "tool_call_result")
    assert start["tool_call"]["status"] == "pending"
    assert result["tool_call"]["status"] == "succeeded"
    assert result["tool_call"]["result"]["value"] == "5"

    detail = client.get(f"/api/v1/sessions/{session_id}").json()["data"]
    assert any(message["role"] == "tool" for message in detail["messages"])
    assert detail["tool_calls"][0]["tool_message_id"] is not None
    assert detail["tool_calls"][0]["assistant_message_id"] is not None


def test_stream_error_event_uses_unified_error_shape(
    client: TestClient,
    session_id: str,
    monkeypatch,
) -> None:
    from app.api.v1.routes import sessions

    def fail_run(*args, **kwargs):
        raise AppError(code="STREAM_TEST_ERROR", message="stream test failed", status_code=502)

    monkeypatch.setattr(sessions.AgentService, "run", fail_run)
    response = send_stream(client, session_id, "trigger error")
    events = parse_events(response.text)

    assert response.status_code == 200
    assert events[0][0] == "user_message_saved"
    assert events[1] == (
        "error",
        {
            "error": {
                "code": "STREAM_TEST_ERROR",
                "message": "stream test failed",
                "details": {},
            }
        },
    )
    detail = client.get(f"/api/v1/sessions/{session_id}").json()["data"]
    assert [(message["role"], message["content"]) for message in detail["messages"]] == [
        ("user", "trigger error")
    ]


def test_original_non_stream_endpoint_remains_available(
    client: TestClient,
    session_id: str,
) -> None:
    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "ordinary request", "provider": "mock"},
    )

    assert response.status_code == 201
    assert response.json()["data"]["assistant_message"]["role"] == "assistant"


def test_openai_mode_forwards_native_deltas_and_persists_on_done(
    client: TestClient,
    session_id: str,
    monkeypatch,
) -> None:
    from app.api.v1.routes import sessions

    class FakeStreamingProvider:
        async def stream(self, messages: list[dict[str, str]]):
            assert messages[-1] == {"role": "user", "content": "真实流式请求"}
            yield "真实"
            yield "接口"
            yield "回复"

    monkeypatch.setattr(
        sessions,
        "get_llm_provider",
        lambda settings, provider_name=None: FakeStreamingProvider(),
    )

    response = send_stream(client, session_id, "真实流式请求", provider="openai")
    events = parse_events(response.text)
    names = [name for name, _ in events]

    assert names == [
        "user_message_saved",
        "assistant_delta",
        "assistant_delta",
        "assistant_delta",
        "assistant_done",
    ]
    assert [data["delta"] for name, data in events if name == "assistant_delta"] == [
        "真实",
        "接口",
        "回复",
    ]
    done = events[-1][1]
    assert done["assistant_message"]["content"] == "真实接口回复"
    assert done["tool_calls"] == []

    detail = client.get(f"/api/v1/sessions/{session_id}").json()["data"]
    assert [(message["role"], message["content"]) for message in detail["messages"]] == [
        ("user", "真实流式请求"),
        ("assistant", "真实接口回复"),
    ]


def test_openai_stream_error_keeps_user_without_partial_assistant(
    client: TestClient,
    session_id: str,
    monkeypatch,
) -> None:
    from app.api.v1.routes import sessions

    class FailingStreamingProvider:
        async def stream(self, messages: list[dict[str, str]]):
            yield "部分内容"
            raise AppError(
                code="LLM_STREAM_INTERRUPTED",
                message="真实模型流式连接提前结束，请重试。",
                status_code=502,
            )

    monkeypatch.setattr(
        sessions,
        "get_llm_provider",
        lambda settings, provider_name=None: FailingStreamingProvider(),
    )

    response = send_stream(client, session_id, "触发真实流异常", provider="openai")
    events = parse_events(response.text)

    assert [name for name, _ in events] == [
        "user_message_saved",
        "assistant_delta",
        "error",
    ]
    assert events[-1][1]["error"]["code"] == "LLM_STREAM_INTERRUPTED"
    detail = client.get(f"/api/v1/sessions/{session_id}").json()["data"]
    assert [(message["role"], message["content"]) for message in detail["messages"]] == [
        ("user", "触发真实流异常")
    ]
