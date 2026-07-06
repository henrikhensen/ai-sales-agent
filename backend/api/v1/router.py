from fastapi import APIRouter

from backend.api.v1.routes import (
    agents,
    companies,
    contacts,
    email_drafts,
    health,
    interactions,
    leads,
    workflows,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(companies.router)
api_router.include_router(leads.router)
api_router.include_router(contacts.router)
api_router.include_router(interactions.router)
api_router.include_router(email_drafts.router)
api_router.include_router(agents.router)
api_router.include_router(workflows.router)
