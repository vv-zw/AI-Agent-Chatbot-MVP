import asyncio
from typing import Any

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import AppError
from app.core.llm_provider_state import runtime_llm_provider_state
from app.llm.openai import OpenAICompatibleProvider


def test_default_provider_is_mock(client: TestClient) -> None:
    health = client.get("/api/v1/health")
    status = client.get("/api/v1/llm/provider")

    assert health.status_code == 200
    assert health.json()["data"]["provider"] == "mock"
    assert status.status_code == 200
    assert status.json()["data"] == {
        "provider": "mock",
        "available_providers": ["mock", "openai"],
        "openai_configured": False,
    }


def test_switch_to_mock_succeeds(client: TestClient) -> None:
    response = client.post("/api/v1/llm/provider", json={"provider": "mock"})

    assert response.status_code == 200
    assert response.json()["data"] == {
        "provider": "mock",
        "openai_configured": False,
    }


def test_switch_invalid_provider_fails(client: TestClient) -> None:
    response = client.post("/api/v1/llm/provider", json={"provider": "other"})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "LLM_PROVIDER_INVALID"
    assert payload["error"]["details"]["available_providers"] == ["mock", "openai"]


def test_switch_to_openai_without_api_key_fails(client: TestClient) -> None:
    response = client.post("/api/v1/llm/provider", json={"provider": "openai"})

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "LLM_CONFIGURATION_ERROR"
    assert "backend/.env" in payload["error"]["message"]
    assert "OPENAI_API_KEY" in payload["error"]["details"]["missing"]
    assert "sk-" not in response.text


def test_openai_mode_missing_key_does_not_break_mock(
    client: TestClient,
    session_id: str,
) -> None:
    failed = client.post("/api/v1/llm/provider", json={"provider": "openai"})
    assert failed.status_code == 503

    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "帮我算一下 128 * 36 + 520"},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["tool_calls"][0]["tool_name"] == "calculator"
    assert data["tool_calls"][0]["result"]["value"] == "5128"


def test_openai_provider_uses_compatible_chat_completion(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"choices": [{"message": {"content": "真实模型回复"}}]}

    class FakeClient:
        def __init__(self, timeout: float) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, headers: dict[str, str], json: dict[str, Any]) -> FakeResponse:
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("app.llm.openai.httpx.Client", FakeClient)
    provider = OpenAICompatibleProvider(
        Settings(
            llm_provider="openai",
            openai_api_key="test-key",
            openai_base_url="https://api.deepseek.com",
            openai_model="deepseek-chat",
        ),
        timeout=5,
    )

    result = provider.complete([{"role": "user", "content": "你好"}])

    assert result.content == "真实模型回复"
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "deepseek-chat"
    assert captured["json"]["messages"][-1] == {"role": "user", "content": "你好"}


def test_openai_provider_timeout_maps_to_unified_error(monkeypatch) -> None:
    class FakeClient:
        def __init__(self, timeout: float) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, *args: object, **kwargs: object) -> object:
            raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("app.llm.openai.httpx.Client", FakeClient)
    provider = OpenAICompatibleProvider(
        Settings(
            llm_provider="openai",
            openai_api_key="test-key",
            openai_base_url="https://api.deepseek.com",
            openai_model="deepseek-chat",
        )
    )

    try:
        provider.complete([{"role": "user", "content": "你好"}])
    except Exception as exc:
        assert getattr(exc, "code") == "LLM_CALL_TIMEOUT"
        assert "test-key" not in str(exc)
    else:
        raise AssertionError("Expected timeout error")




def test_mode_status_question_uses_request_provider(client: TestClient, session_id: str) -> None:
    mock_response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "现在是什么模式", "provider": "mock"},
    )
    assert mock_response.status_code == 201
    mock_content = mock_response.json()["data"]["assistant_message"]["content"]
    assert "Mock 演示模式" in mock_content
    assert "[Mock] 我收到了" not in mock_content

    openai_response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "现在是什么模式", "provider": "openai"},
    )
    assert openai_response.status_code == 201
    openai_content = openai_response.json()["data"]["assistant_message"]["content"]
    assert "真实接口模式" in openai_content
    assert "当前是 **Mock 演示模式" not in openai_content

def test_message_provider_override_uses_openai_even_when_runtime_is_mock(
    client: TestClient,
    session_id: str,
    monkeypatch,
) -> None:
    class FakeOpenAIProvider:
        def complete(self, messages: list[dict[str, str]]):
            from app.llm.base import LLMResult

            return LLMResult(content="请求级真实接口回复")

        def complete_with_tool_result(
            self,
            messages: list[dict[str, str]],
            tool_name: str,
            result: dict[str, Any],
        ) -> str:
            return "工具模式未启用"

    runtime_llm_provider_state.reset("mock")
    monkeypatch.setattr(
        "app.api.v1.routes.sessions.get_settings",
        lambda: Settings(
            llm_provider="mock",
            openai_api_key="test-key",
            openai_base_url="https://api.deepseek.com",
            openai_model="deepseek-chat",
        ),
    )
    monkeypatch.setattr("app.agents.service.OpenAICompatibleProvider", lambda settings: FakeOpenAIProvider())

    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "介绍一下自己", "provider": "openai"},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["assistant_message"]["content"] == "请求级真实接口回复"
    assert data["tool_calls"] == []

def test_openai_mode_plain_chat_can_use_mocked_provider(
    client: TestClient,
    session_id: str,
    monkeypatch,
) -> None:
    from app.api.v1.routes import sessions

    class FakeOpenAIProvider:
        def complete(self, messages: list[dict[str, str]]):
            from app.llm.base import LLMResult

            return LLMResult(content="来自真实模式的普通聊天回复")

        def complete_with_tool_result(
            self,
            messages: list[dict[str, str]],
            tool_name: str,
            result: dict[str, Any],
        ) -> str:
            return "工具模式未启用"

    runtime_llm_provider_state.reset("openai")
    monkeypatch.setattr(
        sessions,
        "get_settings",
        lambda: Settings(
            llm_provider="mock",
            openai_api_key="test-key",
            openai_base_url="https://api.deepseek.com",
            openai_model="deepseek-chat",
        ),
    )
    monkeypatch.setattr("app.agents.service.OpenAICompatibleProvider", lambda settings: FakeOpenAIProvider())

    response = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "你好"},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["assistant_message"]["content"] == "来自真实模式的普通聊天回复"
    assert data["tool_calls"] == []


def test_openai_provider_streams_deepseek_sse_deltas(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeStreamResponse:
        async def __aenter__(self) -> "FakeStreamResponse":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        async def aiter_lines(self):
            yield ': keep-alive'
            yield 'data: {"choices":[{"delta":{"role":"assistant","content":"你"}}]}'
            yield 'data: {"choices":[{"delta":{"content":"好"}}]}'
            yield 'data: {"choices":[],"usage":{"total_tokens":3}}'
            yield 'data: [DONE]'

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        def stream(
            self,
            method: str,
            url: str,
            headers: dict[str, str],
            json: dict[str, Any],
        ) -> FakeStreamResponse:
            captured.update(method=method, url=url, headers=headers, json=json)
            return FakeStreamResponse()

    monkeypatch.setattr("app.llm.openai.httpx.AsyncClient", FakeAsyncClient)
    provider = OpenAICompatibleProvider(
        Settings(
            llm_provider="openai",
            openai_api_key="test-key",
            openai_base_url="https://api.deepseek.com",
            openai_model="deepseek-chat",
        ),
        timeout=5,
    )

    async def collect() -> list[str]:
        messages = [{"role": "user", "content": "你好"}]
        return [delta async for delta in provider.stream(messages)]

    assert asyncio.run(collect()) == ["你", "好"]
    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["headers"]["Accept"] == "text/event-stream"
    assert captured["json"]["stream"] is True
    assert captured["json"]["messages"][-1] == {"role": "user", "content": "你好"}


def test_openai_provider_rejects_stream_without_done(monkeypatch) -> None:
    class FakeStreamResponse:
        async def __aenter__(self) -> "FakeStreamResponse":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        def raise_for_status(self) -> None:
            return None

        async def aiter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"partial"}}]}'

    class FakeAsyncClient:
        def __init__(self, timeout: float) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        def stream(self, *args: object, **kwargs: object) -> FakeStreamResponse:
            return FakeStreamResponse()

    monkeypatch.setattr("app.llm.openai.httpx.AsyncClient", FakeAsyncClient)
    provider = OpenAICompatibleProvider(
        Settings(
            llm_provider="openai",
            openai_api_key="test-key",
            openai_base_url="https://api.deepseek.com",
            openai_model="deepseek-chat",
        )
    )

    async def collect() -> None:
        async for _ in provider.stream([{"role": "user", "content": "hello"}]):
            pass

    try:
        asyncio.run(collect())
    except AppError as exc:
        assert exc.code == "LLM_STREAM_INTERRUPTED"
    else:
        raise AssertionError("Expected interrupted stream error")
