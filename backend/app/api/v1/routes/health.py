from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import ApiResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[dict[str, str]])
def health_check() -> ApiResponse[dict[str, str]]:
    settings = get_settings()
    return ApiResponse(
        data={
            "status": "ok",
            "provider": settings.llm_provider,
        }
    )

