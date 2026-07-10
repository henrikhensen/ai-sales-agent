"""ORM model registry.

Importing this package ensures every model is attached to ``Base.metadata``
so table creation and relationship resolution work correctly.
"""

from backend.infrastructure.database.models.audit_log import AuditLogModel
from backend.infrastructure.database.models.beta_test_session import (
    BetaTestSessionModel,
)
from backend.infrastructure.database.models.company import CompanyModel
from backend.infrastructure.database.models.contact import ContactModel
from backend.infrastructure.database.models.data_retention_policy import (
    DataRetentionPolicyModel,
)
from backend.infrastructure.database.models.data_retention_run import (
    DataRetentionRunModel,
)
from backend.infrastructure.database.models.data_subject_request import (
    DataSubjectRequestModel,
)
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
from backend.infrastructure.database.models.icp_profile import ICPProfileModel
from backend.infrastructure.database.models.interaction import InteractionModel
from backend.infrastructure.database.models.lead import LeadModel
from backend.infrastructure.database.models.lead_candidate import LeadCandidateModel
from backend.infrastructure.database.models.lead_sourcing_campaign import (
    LeadSourcingCampaignModel,
)
from backend.infrastructure.database.models.lead_sourcing_run import (
    LeadSourcingRunModel,
)
from backend.infrastructure.database.models.offer_profile import OfferProfileModel
from backend.infrastructure.database.models.onboarding_status import (
    OnboardingStatusModel,
)
from backend.infrastructure.database.models.outreach_campaign import (
    OutreachCampaignModel,
)
from backend.infrastructure.database.models.outreach_dispatch import (
    OutreachDispatchModel,
)
from backend.infrastructure.database.models.outreach_queue_item import (
    OutreachQueueItemModel,
)
from backend.infrastructure.database.models.qualification_result import (
    QualificationResultModel,
)
from backend.infrastructure.database.models.qualification_run import (
    QualificationRunModel,
)
from backend.infrastructure.database.models.quality_score import QualityScoreModel
from backend.infrastructure.database.models.reply import ReplyModel
from backend.infrastructure.database.models.review_event import ReviewEventModel
from backend.infrastructure.database.models.user import UserModel
from backend.infrastructure.database.models.user_feedback import UserFeedbackModel
from backend.infrastructure.database.models.workflow_run import WorkflowRunModel
from backend.infrastructure.database.models.workspace_settings import (
    WorkspaceSettingsModel,
)

__all__ = [
    "AuditLogModel",
    "BetaTestSessionModel",
    "CompanyModel",
    "ContactModel",
    "DataRetentionPolicyModel",
    "DataRetentionRunModel",
    "DataSubjectRequestModel",
    "DoNotContactEntryModel",
    "EmailDraftModel",
    "EmailProviderConnectionModel",
    "ExternalEmailDraftModel",
    "ICPProfileModel",
    "InteractionModel",
    "LeadCandidateModel",
    "LeadModel",
    "LeadSourcingCampaignModel",
    "LeadSourcingRunModel",
    "OfferProfileModel",
    "OnboardingStatusModel",
    "OutreachCampaignModel",
    "OutreachDispatchModel",
    "OutreachQueueItemModel",
    "QualificationResultModel",
    "QualificationRunModel",
    "QualityScoreModel",
    "ReplyModel",
    "ReviewEventModel",
    "UserFeedbackModel",
    "UserModel",
    "WorkflowRunModel",
    "WorkspaceSettingsModel",
]
