from functools import lru_cache
from pathlib import Path
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the repository
BASE_DIR = Path(__file__).resolve().parent.parent.parent

VALID_ENVIRONMENTS = {"development", "test", "testing", "staging", "production"}

PROHIBITED_PRODUCTION_TOKENS = {
    # Default and example tokens from .env.example, README, and configuration templates
    "demo-admin-token",
    "demo-approver-token",
    "demo-planner-token",
    "demo-viewer-token",
    # Demo credentials from DEMO_CREDENTIALS
    "admin-token-2026",
    "approver-token-2026",
    "planner-token-2026",
    "viewer-token-2026",
    "restricted-token-2026",
    # Trivial / weak default secrets
    "admin",
    "administrator",
    "password",
    "secret",
    "changeme",
    "default",
    "test",
    "testing",
    "123456",
    "12345678",
    "123456789",
    "root",
}

MIN_PRODUCTION_TOKEN_LENGTH = 16


class Settings(BaseSettings):
    """Application configuration settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/trackmeld"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:postgres@localhost:5433/trackmeld"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    TIMEZONE: str = "Asia/Kolkata"

    # Worker configuration
    WORKER_POLL_INTERVAL_SECONDS: float = 1.0
    WORKER_HEARTBEAT_INTERVAL_SECONDS: float = 5.0
    WORKER_STALE_TIMEOUT_SECONDS: float = 30.0
    WORKER_MAX_ATTEMPTS: int = 3
    PLANNING_JOB_TIMEOUT_SECONDS: float = 120.0

    # CORS configuration
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Authentication credentials configuration (env-driven)
    AUTH_ADMIN_TOKEN: str | None = None
    AUTH_APPROVER_TOKEN: str | None = None
    AUTH_PLANNER_TOKEN: str | None = None
    AUTH_VIEWER_TOKEN: str | None = None

    # Demo authentication configuration (opt-in; strictly permitted only in development/testing)
    ENABLE_DEMO_AUTH: bool = False

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean == "prod":
            raise ValueError(
                "Invalid environment 'prod'. Did you mean 'production'? Environment names must not be abbreviated."
            )
        if clean not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment '{v}'. Permitted environments are: {', '.join(sorted(VALID_ENVIRONMENTS))}."
            )
        return clean

    @model_validator(mode="after")
    def validate_production_tokens(self) -> "Settings":
        """Reject weak, default, or example authentication tokens in production or staging at startup."""
        if not self.is_production:
            return self

        tokens = {
            "AUTH_ADMIN_TOKEN": self.AUTH_ADMIN_TOKEN,
            "AUTH_APPROVER_TOKEN": self.AUTH_APPROVER_TOKEN,
            "AUTH_PLANNER_TOKEN": self.AUTH_PLANNER_TOKEN,
            "AUTH_VIEWER_TOKEN": self.AUTH_VIEWER_TOKEN,
        }

        seen_tokens: dict[str, str] = {}
        for token_name, token_val in tokens.items():
            if token_val is None:
                continue

            cleaned = token_val.strip()
            if not cleaned:
                raise ValueError(
                    f"{token_name} in production must not be empty or whitespace-only."
                )

            if cleaned.lower() in PROHIBITED_PRODUCTION_TOKENS:
                raise ValueError(
                    f"{token_name} in production cannot use default, demo, or example token '{token_val}'. "
                    f"A secure, unique production token is required."
                )

            if len(cleaned) < MIN_PRODUCTION_TOKEN_LENGTH:
                raise ValueError(
                    f"{token_name} in production is too weak ({len(cleaned)} characters). "
                    f"Minimum required length is {MIN_PRODUCTION_TOKEN_LENGTH} characters."
                )

            if cleaned in seen_tokens:
                raise ValueError(
                    f"Configured production tokens must be unique across roles. "
                    f"{token_name} has the same token as {seen_tokens[cleaned]}."
                )
            seen_tokens[cleaned] = token_name

        return self

    @property
    def cors_allowed_origins(self) -> list[str]:
        """Parsed list of allowed origins for CORS validation."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        env = self.ENVIRONMENT.lower().strip()
        return env in ("production", "prod", "staging")

    @property
    def is_demo_auth_allowed(self) -> bool:
        """Demo credentials can only be enabled in explicitly permitted local environments."""
        env = self.ENVIRONMENT.lower().strip()
        return env in ("development", "test", "testing") and not self.is_production

    @property
    def is_demo_auth_active(self) -> bool:
        """Demo authentication requires explicit opt-in AND an allowed non-production environment."""
        return bool(self.ENABLE_DEMO_AUTH and self.is_demo_auth_allowed)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
