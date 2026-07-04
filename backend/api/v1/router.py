from fastapi import APIRouter

from backend.api.v1.routes import companies, health, leads

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(companies.router)
api_router.include_router(leads.router)
