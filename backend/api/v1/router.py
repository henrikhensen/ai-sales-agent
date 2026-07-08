from fastapi import APIRouter

from backend.api.v1.routes import (
    agents,
    audit_logs,
    auth,
    companies,
    compliance,
    contacts,
    email_drafts,
    health,
    integrations,
    interactions,
    lead_qualification,
    lead_sourcing,
    leads,
    metrics,
    outreach,
    outreach_dispatch,
    pipeline,
    replies,
    research,
    reviews,
    sales_strategy,
    settings,
    system,
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
api_router.include_router(research.router)
api_router.include_router(pipeline.router)
api_router.include_router(compliance.router)
api_router.include_router(integrations.router)
api_router.include_router(integrations.reply_status_router)
api_router.include_router(replies.router)
api_router.include_router(system.router)
api_router.include_router(metrics.router)
api_router.include_router(audit_logs.router)
api_router.include_router(sales_strategy.router)
api_router.include_router(lead_sourcing.router)
api_router.include_router(lead_qualification.router)
api_router.include_router(outreach.router)
api_router.include_router(outreach_dispatch.router)
