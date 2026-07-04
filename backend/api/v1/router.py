from fastapi import APIRouter

from backend.api.v1.routes import health

api_router = APIRouter()
api_router.include_router(health.router)
