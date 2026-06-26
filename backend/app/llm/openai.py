from typing import Any

import httpx

from app.core.config import Settings
from app.core.errors import AppError
from app.core.llm_provider_state import validate_openai_config
from app.llm.base import LLMResult


class OpenAICompatibleProvider:
    def __init__(self, settings: Settings, timeout: float = 30.0) -> None:
        validate_openai_config(settings)
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/") if settings.openai_base_url else ""
        self.model = settings.openai_model
        self.timeout = timeout

    def complete(self, messages: list[dict[str, str]]) -> LLMResult:
        response_payload = self._post_chat_completion(messages)
        content = self._extract_content(response_payload)
        return LLMResult(content=content)

    def complete_with_tool_result(
        self,
        messages: list[dict[str, str]],
        tool_name: str,
        result: dict[str, Any],
    ) -> str:
        return "真实 API 模式当前仅支持普通聊天；工具调用请切回 Mock 模式演示。"

    def _post_chat_completion(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": self._normalize_messages(messages),
                        "temperature": 0.7,
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AppError(
                code="LLM_CALL_TIMEOUT",
                message="真实模型调用超时，请稍后重试或切回 Mock 模式。",
                status_code=504,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise AppError(
                code="LLM_CALL_FAILED",
                message="真实模型调用失败，请检查后端模型配置或稍后重试。",
                status_code=502,
                details={"status_code": exc.response.status_code},
            ) from exc
        except httpx.HTTPError as exc:
            raise AppError(
                code="LLM_CALL_FAILED",
                message="真实模型网络请求失败，请检查网络、BASE_URL 或切回 Mock 模式。",
                status_code=502,
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise AppError(
                code="LLM_INVALID_RESPONSE",
                message="真实模型返回了无法解析的数据。",
                status_code=502,
            ) from exc

        if not isinstance(payload, dict):
            raise AppError(
                code="LLM_INVALID_RESPONSE",
                message="真实模型响应格式不正确。",
                status_code=502,
            )
        return payload

    @staticmethod
    def _normalize_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "你是 AI Agent Chatbot MVP 的真实模型助手。"
                    "当前真实 API 模式仅负责普通聊天；本地工具调用由 Mock 模式完整演示。"
                ),
            }
        ]
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            if not content:
                continue
            if role in {"user", "assistant", "system"}:
                normalized.append({"role": role, "content": content})
            elif role == "tool":
                normalized.append({"role": "system", "content": f"本地工具结果：{content}"})

        return normalized or [{"role": "user", "content": "你好"}]

    @staticmethod
    def _extract_content(payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise AppError(
                code="LLM_EMPTY_RESPONSE",
                message="真实模型未返回有效内容，请重试或切回 Mock 模式。",
                status_code=502,
            )

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise AppError(
                code="LLM_INVALID_RESPONSE",
                message="真实模型响应格式不正确。",
                status_code=502,
            )

        message = first_choice.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            raise AppError(
                code="LLM_EMPTY_RESPONSE",
                message="真实模型未返回有效内容，请重试或切回 Mock 模式。",
                status_code=502,
            )
        return content.strip()
