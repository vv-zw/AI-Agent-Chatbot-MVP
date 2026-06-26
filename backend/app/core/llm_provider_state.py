from typing import Literal

from app.core.config import Settings, get_settings
from app.core.errors import AppError


LLMProviderName = Literal["mock", "openai"]
AVAILABLE_PROVIDERS: tuple[LLMProviderName, ...] = ("mock", "openai")


class RuntimeLLMProviderState:
    def __init__(self) -> None:
        self._provider = self._normalize_initial_provider(get_settings().llm_provider)

    @staticmethod
    def _normalize_initial_provider(provider: str) -> LLMProviderName:
        normalized = provider.strip().lower()
        if normalized in AVAILABLE_PROVIDERS:
            return normalized  # type: ignore[return-value]
        return "mock"

    @property
    def provider(self) -> LLMProviderName:
        return self._provider

    def reset(self, provider: str | None = None) -> None:
        self._provider = self._normalize_initial_provider(
            provider if provider is not None else get_settings().llm_provider
        )

    def switch(self, provider: str, settings: Settings) -> LLMProviderName:
        normalized = provider.strip().lower()
        if normalized not in AVAILABLE_PROVIDERS:
            raise AppError(
                code="LLM_PROVIDER_INVALID",
                message="LLM Provider 仅支持 mock 或 openai。",
                status_code=422,
                details={"provider": provider, "available_providers": list(AVAILABLE_PROVIDERS)},
            )

        if normalized == "openai":
            validate_openai_config(settings)

        self._provider = normalized  # type: ignore[assignment]
        return self._provider


def is_openai_configured(settings: Settings) -> bool:
    return bool(settings.openai_api_key and settings.openai_base_url and settings.openai_model)


def validate_openai_config(settings: Settings) -> None:
    missing = [
        name
        for name, value in (
            ("OPENAI_API_KEY", settings.openai_api_key),
            ("OPENAI_BASE_URL", settings.openai_base_url),
            ("OPENAI_MODEL", settings.openai_model),
        )
        if not value
    ]
    if missing:
        raise AppError(
            code="LLM_CONFIGURATION_ERROR",
            message=(
                "真实 API 模式未配置完整，请在 backend/.env 中配置 "
                "OPENAI_API_KEY、OPENAI_BASE_URL 和 OPENAI_MODEL。"
            ),
            status_code=503,
            details={"missing": missing},
        )


runtime_llm_provider_state = RuntimeLLMProviderState()
