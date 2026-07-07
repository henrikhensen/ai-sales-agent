"""ORM model registry.

Importing this package ensures every model is attached to ``Base.metadata``
so table creation and relationship resolution work correctly.
"""

from backend.infrastructure.database.models.audit_log import AuditLogModel
from backend.infrastructure.database.models.company import CompanyModel
from backend.infrastructure.database.models.contact import ContactModel
from backend.infrastructure.database.models.do_not_contact_entry import (
    DoNotContactEntryModel,
)
from backend.infrastructure.database.models.email_draft import EmailDraftModel
from backend.infrastructure.database.models.email_provider_connection import (
    EmailProviderConnectionModel,
)
from backend.infrastructure.database.models.external_email_draft import (
    ExternalEmailDraftModel,
)
from backend.infrastructure.database.models.interaction import InteractionModel
from backend.infrastructure.database.models.lead import LeadModel
from backend.infrastructure.database.models.reply import ReplyModel
from backend.infrastructure.database.models.review_event import ReviewEventModel
from backend.infrastructure.database.models.user import UserModel
from backend.infrastructure.database.models.workflow_run import WorkflowRunModel

__all__ = [
    "AuditLogModel",
    "CompanyModel",
    "ContactModel",
    "DoNotContactEntryModel",
    "EmailDraftModel",
    "EmailProviderConnectionModel",
    "ExternalEmailDraftModel",
    "InteractionModel",
    "LeadModel",
    "ReplyModel",
    "ReviewEventModel",
    "UserModel",
    "WorkflowRunModel",
]
