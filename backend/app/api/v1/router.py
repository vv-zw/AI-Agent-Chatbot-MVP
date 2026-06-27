from fastapi import APIRouter

from app.api.v1.routes import health, llm, roles, sessions

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(llm.router)
api_router.include_router(roles.router)
api_router.include_router(sessions.router)
