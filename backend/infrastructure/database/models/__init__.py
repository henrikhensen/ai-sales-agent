"""ORM model registry.

Importing this package ensures every model is attached to ``Base.metadata``
so table creation and relationship resolution work correctly.
"""

from backend.infrastructure.database.models.company import CompanyModel
from backend.infrastructure.database.models.contact import ContactModel
from backend.infrastructure.database.models.interaction import InteractionModel
from backend.infrastructure.database.models.lead import LeadModel

__all__ = [
    "CompanyModel",
    "ContactModel",
    "InteractionModel",
    "LeadModel",
]
