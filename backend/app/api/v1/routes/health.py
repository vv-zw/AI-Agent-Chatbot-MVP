from fastapi import APIRouter

from app.core.llm_provider_state import runtime_llm_provider_state
from app.schemas.common import ApiResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[dict[str, str]])
def health_check() -> ApiResponse[dict[str, str]]:
    return ApiResponse(
        data={
            "status": "ok",
            "provider": runtime_llm_provider_state.provider,
        }
    )
