"""Mock Lead Sourcing Provider — the default provider.

Returns a small, deterministic, hand-written pool of example companies.
Makes no external call of any kind, needs no secrets, and is safe to run
in any environment. Deliberately spans several industries (including one
explicitly excludable one) so ICP matching, do-not-contact blocking, and
duplicate detection can all be exercised locally without real data.
"""

from __future__ import annotations

from backend.infrastructure.lead_sourcing.base import (
    LeadSourcingProvider,
    LeadSourcingProviderStatus,
    LeadSourcingSearchQuery,
    RawLeadCandidate,
)

_MOCK_COMPANIES: list[RawLeadCandidate] = [
    RawLeadCandidate(
        company_name="Nordwind Logistik GmbH",
        company_domain="nordwind-logistik.example",
        company_website_url="https://nordwind-logistik.example",
        industry="Logistics",
        location="Hamburg, Germany",
        description=(
            "Mittelstaendischer Logistikdienstleister mit eigener Flotte. "
            "Sucht nach Loesungen fuer Sendungsverfolgung, Fleet Management "
            "und manuelle Dispositionsprozesse. Kontakt: info@nordwind-logistik.example"
        ),
        source_url="https://nordwind-logistik.example",
        source_name="mock-directory",
        confidence_score=0.82,
    ),
    RawLeadCandidate(
        company_name="Blauwerk SaaS Solutions",
        company_domain="blauwerk-saas.example",
        company_website_url="https://blauwerk-saas.example",
        industry="Software",
        location="Berlin, Germany",
        description=(
            "B2B SaaS Anbieter fuer Team-Kollaboration, kuerzlich neue "
            "Finanzierungsrunde erhalten und expandiert das Vertriebsteam. "
            "Kontakt: hello@blauwerk-saas.example"
        ),
        source_url="https://blauwerk-saas.example",
        source_name="mock-directory",
        confidence_score=0.77,
    ),
    RawLeadCandidate(
        company_name="Rheinmetall Fertigung AG",
        company_domain="rheinmetall-fertigung.example",
        company_website_url="https://rheinmetall-fertigung.example",
        industry="Manufacturing",
        location="Duesseldorf, Germany",
        description=(
            "Industrielle Fertigung mit Fokus auf Praezisionsteile. Nutzt "
            "SAP fuer die Produktionsplanung und sucht nach besserer "
            "Sichtbarkeit der Lieferkette. Kontakt: kontakt@rheinmetall-fertigung.example"
        ),
        source_url="https://rheinmetall-fertigung.example",
        source_name="mock-directory",
        confidence_score=0.71,
    ),
    RawLeadCandidate(
        company_name="Gruener Handel Retail GmbH",
        company_domain="gruener-handel.example",
        company_website_url="https://gruener-handel.example",
        industry="Retail",
        location="Muenchen, Germany",
        description=(
            "Regionale Einzelhandelskette mit zehn Filialen, sucht nach "
            "einer besseren Warenwirtschaft und Kundenbindung. "
            "Kontakt: sales@gruener-handel.example"
        ),
        source_url="https://gruener-handel.example",
        source_name="mock-directory",
        confidence_score=0.65,
    ),
    RawLeadCandidate(
        company_name="Alpin Consulting Partners",
        company_domain="alpin-consulting.example",
        company_website_url="https://alpin-consulting.example",
        industry="Consulting",
        location="Zuerich, Switzerland",
        description=(
            "Strategieberatung fuer den Mittelstand, aktuell in einer "
            "Wachstumsphase mit neuen Standorten. Kontakt: office@alpin-consulting.example"
        ),
        source_url="https://alpin-consulting.example",
        source_name="mock-directory",
        confidence_score=0.6,
    ),
    RawLeadCandidate(
        company_name="Kuestenwind Spedition",
        company_domain="kuestenwind-spedition.example",
        company_website_url="https://kuestenwind-spedition.example",
        industry="Logistics",
        location="Bremen, Germany",
        description=(
            "Spedition mit Schwerpunkt Seefracht, moechte den manuellen "
            "Dispositionsprozess digitalisieren und nutzt bereits SAP. "
            "Kontakt: info@kuestenwind-spedition.example"
        ),
        source_url="https://kuestenwind-spedition.example",
        source_name="mock-directory",
        confidence_score=0.8,
    ),
    RawLeadCandidate(
        company_name="Lucky Spin Gambling Co",
        company_domain="lucky-spin-gambling.example",
        company_website_url="https://lucky-spin-gambling.example",
        industry="Gambling",
        location="Malta",
        description=(
            "Online-Gluecksspielanbieter. Dies ist ein Beispiel-Kandidat, "
            "um ausgeschlossene Branchen im ICP Matching zu testen."
        ),
        source_url="https://lucky-spin-gambling.example",
        source_name="mock-directory",
        confidence_score=0.4,
    ),
    RawLeadCandidate(
        company_name="Studenten Semesterprojekt e.V.",
        company_domain="studenten-semesterprojekt.example",
        company_website_url="https://studenten-semesterprojekt.example",
        industry="Education",
        location="Leipzig, Germany",
        description=(
            "Dies ist ein studentisches Semesterprojekt ohne kommerziellen "
            "Hintergrund — Beispiel-Kandidat zum Testen von negative_keywords."
        ),
        source_url="https://studenten-semesterprojekt.example",
        source_name="mock-directory",
        confidence_score=0.3,
    ),
]


class MockLeadSourcingProvider(LeadSourcingProvider):
    """Deterministic, network-free provider. Always safe to run."""

    name = "mock"

    async def get_provider_status(self) -> LeadSourcingProviderStatus:
        return LeadSourcingProviderStatus(
            provider="mock",
            status="mock_ready",
            real_search_enabled=False,
            warnings=[],
        )

    async def search_companies(
        self, query: LeadSourcingSearchQuery
    ) -> list[RawLeadCandidate]:
        excluded = [k.strip().lower() for k in query.excluded_keywords if k.strip()]
        target_keywords = [k.strip().lower() for k in query.target_keywords if k.strip()]

        matches: list[tuple[int, RawLeadCandidate]] = []
        for company in _MOCK_COMPANIES:
            corpus = " ".join(
                filter(
                    None,
                    [company.industry, company.location, company.description],
                )
            ).lower()

            if query.target_industry and query.target_industry.lower() not in (
                company.industry or ""
            ).lower():
                continue
            if query.target_location and query.target_location.lower() not in (
                company.location or ""
            ).lower():
                continue
            if any(keyword in corpus for keyword in excluded):
                continue

            keyword_hits = sum(1 for keyword in target_keywords if keyword in corpus)
            matches.append((keyword_hits, company))

        # Highest keyword-match count first; stable otherwise (preserves
        # the pool's own order for equal scores).
        matches.sort(key=lambda pair: pair[0], reverse=True)
        return [company for _, company in matches[: query.max_results]]
