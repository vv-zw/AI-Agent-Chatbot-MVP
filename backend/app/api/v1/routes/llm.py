from fastapi import APIRouter

from app.core.config import get_settings
from app.core.llm_provider_state import (
    AVAILABLE_PROVIDERS,
    is_openai_configured,
    runtime_llm_provider_state,
)
from app.schemas.common import ApiResponse
from app.schemas.llm import (
    LLMProviderStatus,
    LLMProviderSwitchRequest,
    LLMProviderSwitchResponse,
)

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/provider", response_model=ApiResponse[LLMProviderStatus])
def get_llm_provider() -> ApiResponse[LLMProviderStatus]:
    settings = get_settings()
    return ApiResponse(
        data=LLMProviderStatus(
            provider=runtime_llm_provider_state.provider,
            available_providers=list(AVAILABLE_PROVIDERS),
            openai_configured=is_openai_configured(settings),
        )
    )


@router.post("/provider", response_model=ApiResponse[LLMProviderSwitchResponse])
def switch_llm_provider(
    payload: LLMProviderSwitchRequest,
) -> ApiResponse[LLMProviderSwitchResponse]:
    settings = get_settings()
    provider = runtime_llm_provider_state.switch(payload.provider, settings)
    return ApiResponse(
        data=LLMProviderSwitchResponse(
            provider=provider,
            openai_configured=is_openai_configured(settings),
        )
    )
