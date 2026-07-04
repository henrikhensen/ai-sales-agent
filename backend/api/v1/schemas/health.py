from typing import Literal

from pydantic import BaseModel


class ComponentHealth(BaseModel):
    """Health state of a single infrastructure component."""

    status: Literal["up", "down"]


class HealthResponse(BaseModel):
    """Response body for the health check endpoint."""

    status: Literal["ok", "degraded"]
    service: str
    environment: str
    components: dict[str, ComponentHealth]
