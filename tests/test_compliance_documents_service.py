"""Tests for Compliance Documents: static templates and notices.

Covers: the endpoint works, and it never claims to be legal advice or a
compliance certification.
"""

from backend.application.compliance.compliance_documents_service import (
    ComplianceDocumentsService,
)
from backend.shared.config import get_settings


def test_get_documents_returns_eight_documents():
    service = ComplianceDocumentsService(get_settings())
    response = service.get_documents()
    assert len(response.documents) == 8
    keys = {doc.key for doc in response.documents}
    assert "legal_review_required_notice" in keys
    assert "privacy_notice_template" in keys


def test_documents_never_claim_legal_advice_or_certification():
    service = ComplianceDocumentsService(get_settings())
    response = service.get_documents()
    full_text = response.disclaimer.lower() + " ".join(
        doc.body.lower() for doc in response.documents
    )
    assert "not legal advice" in full_text
    # The only mention of "certified compliant" must be in a negation
    # ("nothing ... is certified compliant"), never a bare positive claim.
    assert "nothing" in full_text and "is certified compliant" in full_text
    assert "this system is gdpr compliant" not in full_text
    assert "we are legally compliant" not in full_text
