from functools import lru_cache

from pydantic import Field
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
    debug: bool = Field(default=False, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    # PostgreSQL
    postgres_user: str = Field(default="sales_agent", alias="POSTGRES_USER")
    postgres_password: str = Field(default="sales_agent_password", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="sales_agent", alias="POSTGRES_DB")
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    # Redis
    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")

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

    # Frontend / CORS
    cors_allowed_origins: str = Field(
        default="http://localhost:3000", alias="CORS_ALLOWED_ORIGINS"
    )

    # Auth (local JWT — no external provider, no OAuth in this phase)
    jwt_secret_key: str = Field(
        default="dev-only-insecure-secret-change-me", alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
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
        """Async SQLAlchemy connection URL for PostgreSQL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        """Connection URL for Redis."""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
