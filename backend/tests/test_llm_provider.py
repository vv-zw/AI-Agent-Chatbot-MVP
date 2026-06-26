from typing import Any

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
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
