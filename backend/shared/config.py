from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="AI Sales Agent", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")
    # Purely informational — shown in system status / deployment docs. Does
    # not affect CORS (see cors_allowed_origins) or OAuth redirects (see
    # oauth_redirect_base_url), which are configured independently.
    frontend_public_url: str = Field(
        default="http://localhost:3000", alias="FRONTEND_PUBLIC_URL"
    )
    backend_public_url: str = Field(
        default="http://localhost:8000", alias="BACKEND_PUBLIC_URL"
    )

    # PostgreSQL
    postgres_user: str = Field(default="sales_agent", alias="POSTGRES_USER")
    postgres_password: str = Field(default="sales_agent_password", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="sales_agent", alias="POSTGRES_DB")
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    # Optional full connection string override, for hosts (Render, Railway,
    # ...) that inject a single DATABASE_URL instead of discrete POSTGRES_*
    # parts. When set, this takes precedence over the POSTGRES_* fields
    # above in the `database_url` property below.
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")

    # Redis
    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    # Optional full connection string override, analogous to
    # database_url_override above.
    redis_url_override: str | None = Field(default=None, alias="REDIS_URL")

    # LLM / AI Agents
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-opus-4-8", alias="ANTHROPIC_MODEL")
    # Real (billable) provider calls stay disabled unless explicitly turned on,
    # even when LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY are both set — see
    # backend/infrastructure/llm/factory.py for the enforcement.
    llm_enable_real_calls: bool = Field(default=False, alias="LLM_ENABLE_REAL_CALLS")
    # Caps applied only to the real Anthropic provider (backend/infrastructure/
    # llm/anthropic_provider.py) — the mock provider ignores them since it
    # never makes a real, billable, or slow call.
    llm_max_input_chars: int = Field(default=12_000, alias="LLM_MAX_INPUT_CHARS")
    llm_max_output_tokens: int = Field(default=1200, alias="LLM_MAX_OUTPUT_TOKENS")
    llm_request_timeout_seconds: int = Field(
        default=30, alias="LLM_REQUEST_TIMEOUT_SECONDS"
    )

    # Email Draft Integration (Gmail/Outlook) — backend/infrastructure/
    # email_integration/. Only ever creates drafts, never sends: there is no
    # send method anywhere in this integration, by design.
    email_integration_provider: str = Field(
        default="mock", alias="EMAIL_INTEGRATION_PROVIDER"
    )
    # Real (billable-in-effort, not billable-in-money) provider calls stay
    # disabled unless explicitly turned on, even when a real provider and
    # its OAuth credentials are both configured — see
    # backend/infrastructure/email_integration/factory.py for the enforcement.
    email_integration_enable_real_drafts: bool = Field(
        default=False, alias="EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS"
    )
    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    microsoft_client_id: str | None = Field(default=None, alias="MICROSOFT_CLIENT_ID")
    microsoft_client_secret: str | None = Field(
        default=None, alias="MICROSOFT_CLIENT_SECRET"
    )
    microsoft_tenant_id: str = Field(default="common", alias="MICROSOFT_TENANT_ID")
    oauth_redirect_base_url: str = Field(
        default="http://localhost:8000", alias="OAUTH_REDIRECT_BASE_URL"
    )
    # Symmetric key (Fernet) used to encrypt OAuth tokens at rest. Only
    # required when EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=true.
    email_token_encryption_key: str | None = Field(
        default=None, alias="EMAIL_TOKEN_ENCRYPTION_KEY"
    )
    email_draft_max_subject_chars: int = Field(
        default=200, alias="EMAIL_DRAFT_MAX_SUBJECT_CHARS"
    )
    email_draft_max_body_chars: int = Field(
        default=20_000, alias="EMAIL_DRAFT_MAX_BODY_CHARS"
    )

    # Reply Tracking (Gmail/Outlook) — backend/infrastructure/reply_tracking/.
    # Only ever reads messages that already exist in a connected mailbox;
    # there is no send/reply method anywhere in this integration, by design.
    reply_tracking_provider: str = Field(
        default="mock", alias="REPLY_TRACKING_PROVIDER"
    )
    # Real read calls stay disabled unless explicitly turned on, even when a
    # real provider and its OAuth credentials are both configured — see
    # backend/infrastructure/reply_tracking/factory.py for the enforcement.
    reply_tracking_enable_real_reads: bool = Field(
        default=False, alias="REPLY_TRACKING_ENABLE_REAL_READS"
    )
    reply_tracking_max_messages_per_sync: int = Field(
        default=25, alias="REPLY_TRACKING_MAX_MESSAGES_PER_SYNC"
    )
    reply_tracking_lookback_days: int = Field(
        default=30, alias="REPLY_TRACKING_LOOKBACK_DAYS"
    )
    reply_tracking_timeout_seconds: int = Field(
        default=30, alias="REPLY_TRACKING_TIMEOUT_SECONDS"
    )
    # When true (default), only a short body_preview is stored for each
    # reply — the full body_text is discarded after analysis.
    reply_tracking_store_body_preview_only: bool = Field(
        default=True, alias="REPLY_TRACKING_STORE_BODY_PREVIEW_ONLY"
    )

    # Frontend / CORS
    cors_allowed_origins: str = Field(
        default="http://localhost:3000", alias="CORS_ALLOWED_ORIGINS"
    )

    # Auth (local JWT — no external provider, no OAuth in this phase)
    jwt_secret_key: str = Field(
        default="dev-only-insecure-secret-change-me", alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    # Accepts either env var name — JWT_ACCESS_TOKEN_EXPIRE_MINUTES is the
    # more explicit production name; ACCESS_TOKEN_EXPIRE_MINUTES is the
    # original name and keeps existing .env files working unchanged.
    access_token_expire_minutes: int = Field(
        default=60,
        validation_alias=AliasChoices(
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "ACCESS_TOKEN_EXPIRE_MINUTES"
        ),
    )

    # Website Research (backend/infrastructure/web/, backend/application/research/)
    # Fetches only the exact public URL a caller supplies — no automatic mass
    # research, no LinkedIn scraping, no LLM call in this phase.
    website_fetch_timeout_seconds: float = Field(
        default=10, alias="WEBSITE_FETCH_TIMEOUT_SECONDS"
    )
    website_fetch_max_bytes: int = Field(
        default=2_000_000, alias="WEBSITE_FETCH_MAX_BYTES"
    )
    website_research_max_pages: int = Field(
        default=1, alias="WEBSITE_RESEARCH_MAX_PAGES"
    )
    website_research_user_agent: str = Field(
        default="AI-Sales-Agent-WebsiteResearch/1.0",
        alias="WEBSITE_RESEARCH_USER_AGENT",
    )

    # Logging / Metrics / Backups (deployment & monitoring readiness)
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    # Per-request access log line (method, path, status, duration, request
    # id, user id if available). Never logs bodies, passwords, or tokens.
    enable_request_logging: bool = Field(
        default=True, alias="ENABLE_REQUEST_LOGGING"
    )
    # Gates GET /api/v1/metrics (admin-only). Off by default since it adds a
    # small amount of bookkeeping and is only useful once something is
    # actually watching it.
    enable_metrics: bool = Field(default=False, alias="ENABLE_METRICS")
    # Gates GET /api/v1/system/backups/status and documents intent for the
    # backup scripts under scripts/ — this flag does not itself schedule
    # backups (there is no built-in scheduler); backups are run manually or
    # via an external cron/scheduler calling scripts/backup_db.*.
    enable_backups: bool = Field(default=False, alias="ENABLE_BACKUPS")
    backup_dir: str = Field(default="./backups", alias="BACKUP_DIR")
    backup_retention_days: int = Field(default=7, alias="BACKUP_RETENTION_DAYS")
    healthcheck_timeout_seconds: float = Field(
        default=5, alias="HEALTHCHECK_TIMEOUT_SECONDS"
    )

    # Rate Limits — protect expensive/sensitive endpoints (auth, workflow,
    # LLM test, external draft, reply sync, do-not-contact check) from
    # abuse. Applied per authenticated user (from the JWT) or per hashed IP
    # otherwise — see backend/shared/rate_limit.py.
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    # "memory": in-process counters (fine for a single instance / local
    # dev). "redis": shared counters via the existing Redis connection —
    # required for correct limits across multiple backend instances. Falls
    # back to memory (with a logged warning, never a crash) if Redis is
    # unreachable when a request needs to be checked.
    rate_limit_backend: str = Field(default="memory", alias="RATE_LIMIT_BACKEND")
    rate_limit_default_per_minute: int = Field(
        default=60, alias="RATE_LIMIT_DEFAULT_PER_MINUTE"
    )
    rate_limit_auth_per_minute: int = Field(
        default=10, alias="RATE_LIMIT_AUTH_PER_MINUTE"
    )
    rate_limit_workflow_per_hour: int = Field(
        default=20, alias="RATE_LIMIT_WORKFLOW_PER_HOUR"
    )
    rate_limit_website_research_per_hour: int = Field(
        default=30, alias="RATE_LIMIT_WEBSITE_RESEARCH_PER_HOUR"
    )
    rate_limit_llm_test_per_hour: int = Field(
        default=10, alias="RATE_LIMIT_LLM_TEST_PER_HOUR"
    )
    rate_limit_external_draft_per_hour: int = Field(
        default=20, alias="RATE_LIMIT_EXTERNAL_DRAFT_PER_HOUR"
    )
    rate_limit_reply_sync_per_hour: int = Field(
        default=20, alias="RATE_LIMIT_REPLY_SYNC_PER_HOUR"
    )
    rate_limit_compliance_check_per_minute: int = Field(
        default=60, alias="RATE_LIMIT_COMPLIANCE_CHECK_PER_MINUTE"
    )

    # Audit Logs — system-wide, append-only trail of security/compliance-
    # relevant actions (login, workflow runs, review decisions, do-not-
    # contact changes, external drafts, reply syncs, rate limit hits, ...).
    # Never stores secrets, API keys, tokens, full email bodies, full LLM
    # prompts, or full reply bodies — see backend/application/audit/.
    audit_logs_enabled: bool = Field(default=True, alias="AUDIT_LOGS_ENABLED")
    # Informational for now (no automatic purge job exists yet) — documents
    # how long audit logs are intended to be kept.
    audit_log_retention_days: int = Field(
        default=180, alias="AUDIT_LOG_RETENTION_DAYS"
    )

    # Lead Sourcing (backend/application/lead_sourcing/) — finds and scores
    # candidate companies against an ICP, but never sends anything, never
    # contacts anyone, and never scrapes LinkedIn or anything behind a
    # login. "mock" is always safe (no external call, no config needed);
    # "search_api" only ever runs a real external search when
    # LEAD_SOURCING_ENABLE_REAL_SEARCH=true AND the provider is fully
    # configured — see backend/infrastructure/lead_sourcing/factory.py.
    lead_sourcing_provider: str = Field(default="mock", alias="LEAD_SOURCING_PROVIDER")
    lead_sourcing_enable_real_search: bool = Field(
        default=False, alias="LEAD_SOURCING_ENABLE_REAL_SEARCH"
    )
    lead_sourcing_max_results_per_run: int = Field(
        default=25, alias="LEAD_SOURCING_MAX_RESULTS_PER_RUN"
    )
    lead_sourcing_max_website_pages_per_company: int = Field(
        default=2, alias="LEAD_SOURCING_MAX_WEBSITE_PAGES_PER_COMPANY"
    )
    lead_sourcing_request_timeout_seconds: int = Field(
        default=30, alias="LEAD_SOURCING_REQUEST_TIMEOUT_SECONDS"
    )
    # Extracts a contact email only from text already rendered on the
    # public page fetched via Website Research — never a new/separate
    # scrape, never a guess.
    lead_sourcing_allow_public_website_email_extraction: bool = Field(
        default=True, alias="LEAD_SOURCING_ALLOW_PUBLIC_WEBSITE_EMAIL_EXTRACTION"
    )
    # When false (default), only role-based addresses (info@, sales@,
    # contact@, kontakt@, ...) are kept; anything that looks like a named
    # individual's address is dropped rather than stored.
    lead_sourcing_allow_personal_emails: bool = Field(
        default=False, alias="LEAD_SOURCING_ALLOW_PERSONAL_EMAILS"
    )
    # When true (default), a candidate only becomes a CRM Company/Lead once
    # a human explicitly approves it — never automatically on discovery.
    lead_sourcing_require_review_before_crm: bool = Field(
        default=True, alias="LEAD_SOURCING_REQUIRE_REVIEW_BEFORE_CRM"
    )

    rate_limit_lead_sourcing_runs_per_hour: int = Field(
        default=10, alias="RATE_LIMIT_LEAD_SOURCING_RUNS_PER_HOUR"
    )
    rate_limit_lead_import_per_hour: int = Field(
        default=20, alias="RATE_LIMIT_LEAD_IMPORT_PER_HOUR"
    )

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        """Comma-separated ``CORS_ALLOWED_ORIGINS`` as a list of origins."""
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def database_url(self) -> str:
        """Async SQLAlchemy connection URL for PostgreSQL.

        Prefers ``DATABASE_URL`` if set (common on managed hosts that inject
        a single connection string), normalized to the ``asyncpg`` driver;
        otherwise builds one from the discrete ``POSTGRES_*`` settings.
        """
        if self.database_url_override:
            url = self.database_url_override
            if url.startswith("postgres://"):
                url = "postgresql+asyncpg://" + url[len("postgres://") :]
            elif url.startswith("postgresql://"):
                url = "postgresql+asyncpg://" + url[len("postgresql://") :]
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Connection URL for Redis.

        Prefers ``REDIS_URL`` if set (common on managed hosts); otherwise
        builds one from the discrete ``REDIS_*`` settings.
        """
        if self.redis_url_override:
            return self.redis_url_override
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
