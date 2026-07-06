from fastapi import APIRouter

from backend.api.v1.routes import (
    agents,
    auth,
    companies,
    contacts,
    email_drafts,
    health,
    interactions,
    leads,
    reviews,
    settings,
    users,
    workflows,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(companies.router)
api_router.include_router(leads.router)
api_router.include_router(contacts.router)
api_router.include_router(interactions.router)
api_router.include_router(email_drafts.router)
api_router.include_router(agents.router)
api_router.include_router(workflows.router)
api_router.include_router(reviews.router)
api_router.include_router(settings.router)
