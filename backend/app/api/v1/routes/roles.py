from fastapi import APIRouter

from app.schemas.common import ApiResponse
from app.schemas.roles import RoleRead
from app.services.roles import list_roles

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=ApiResponse[list[RoleRead]])
def get_roles() -> ApiResponse[list[RoleRead]]:
    return ApiResponse(data=[RoleRead(**role.__dict__) for role in list_roles()])
