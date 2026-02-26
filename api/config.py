"""
API Configuration Module

Centralized configuration with validation and type safety.
Compatible with both pydantic v2 and pydantic-settings.
"""

from typing import Literal

# Try pydantic-settings first (recommended for v2.10+)
try:
    from pydantic import Field
    from pydantic import field_validator as validator_decorator
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        """Application settings with validation."""

        # Environment
        ENVIRONMENT: Literal["development", "production", "staging"] = Field(
            default="development", description="Application environment"
        )

        # Supabase
        SUPABASE_URL: str = Field(default="https://test.supabase.co", description="Supabase project URL")
        SUPABASE_SERVICE_KEY: str = Field(default="test-service-key", description="Supabase service role key")

        # WorkOS
        WORKOS_AUDIENCE: str = Field(default="api.workos.com", description="WorkOS audience")
        WORKOS_ISSUER: str = Field(default="api.workos.com", description="WorkOS issuer")
        WORKOS_CLIENT_ID: str = Field(default="test-client-id", description="WorkOS client ID")
        WORKOS_JWKS_URL: str = Field(default="https://api.workos.com/v1/jwks", description="WorkOS JWKS URL")

        # PayHere
        PAYHERE_MERCHANT_ID: str = Field(default="test-merchant-id", description="PayHere merchant ID")
        PAYHERE_MERCHANT_SECRET: str = Field(default="test-merchant-secret", description="PayHere merchant secret")
        PAYHERE_SANDBOX: bool = Field(default=True, description="Use PayHere sandbox")
        PAYHERE_CREDIT_RATE_LKR: float = Field(default=350.0, description="Credit rate in LKR")

        # Workers
        HTTP_WORKER_URL: str | None = Field(default=None, description="HTTP worker URL")
        BROWSER_WORKER_URL: str | None = Field(default=None, description="Browser worker URL")
        SDK_WORKER_URL: str | None = Field(default=None, description="SDK worker URL")

        # Orchestrator
        ORCHESTRATOR_URL: str | None = Field(default=None, description="Orchestrator URL")

        # Google Cloud
        GOOGLE_CLOUD_PROJECT: str = Field(default="test-project", description="Google Cloud project ID")
        CLOUD_RUN_LOCATION: str = Field(default="us-central1", description="Cloud Run location")

        # Frontend
        FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend URL")

        # API
        API_URL: str = Field(default="http://localhost:8080", description="API URL")
        PORT: int = Field(default=8080, description="API port")

        # Cloud Tasks Queue
        QUEUE_PATH: str | None = Field(default=None, description="Cloud Tasks queue path")
        PAYHERE_ALLOWED_IPS: str | None = Field(default=None, description="PayHere allowed IPs")

        # Development Mode (CRITICAL: Never enable in production)
        DEV_MODE: bool = Field(
            default=False,
            description="Enable development mode (bypasses credit checks - NEVER enable in production)",
        )

        model_config: SettingsConfigDict = {
            "case_sensitive": False,
            "env_file": ".env",
            "env_prefix": "SEO_PRO_",
            "extra": "ignore",
        }

        @validator_decorator("ENVIRONMENT")
        @classmethod
        def validate_environment(cls, v: str, info) -> str:
            if isinstance(v, str) and v not in ["development", "production", "staging"]:
                raise ValueError("ENVIRONMENT must be development, production, or staging")
            return v

        @validator_decorator("DEV_MODE")
        @classmethod
        def validate_dev_mode(cls, v: bool, info) -> bool:
            """Prevent DEV_MODE in production/staging environments."""
            if v and info.data.get("ENVIRONMENT") in ["production", "staging"]:
                raise ValueError(
                    "CRITICAL SECURITY: DEV_MODE cannot be enabled in production or staging. "
                    "This would bypass all credit checks and payment processing."
                )
            return v

        @property
        def workos_audience(self) -> str:
            """Get WorkOS audience based on environment."""
            if self.ENVIRONMENT == "production":
                return "api.workos.com"
            return "api.workos.com/staging"

        @property
        def workos_issuer(self) -> str:
            """Get WorkOS issuer based on environment."""
            if self.ENVIRONMENT == "production":
                return "api.workos.com"
            return "api.workos.com/staging"

        @property
        def is_production(self) -> bool:
            """Check if running in production."""
            return self.ENVIRONMENT == "production"

        @property
        def queue_path(self) -> str:
            """Get Cloud Tasks queue path."""
            if self.QUEUE_PATH:
                return self.QUEUE_PATH
            return f"projects/{self.GOOGLE_CLOUD_PROJECT}/locations/{self.CLOUD_RUN_LOCATION}/queues/seo-audit-queue"

        @property
        def allowed_origins(self) -> list:
            """Get allowed CORS origins."""
            origins = [self.FRONTEND_URL, "http://localhost:3000"]
            return [o for o in origins if o]  # Filter out None

        @property
        def docs_enabled(self) -> bool:
            """Check if docs should be enabled."""
            return self.ENVIRONMENT != "production"

except ImportError:
    # Fallback to older pydantic for environments without pydantic-settings
    from pydantic import BaseModel, Field, validator

    class Settings(BaseModel):
        """Application settings with validation (fallback mode)."""

        # Environment
        ENVIRONMENT: Literal["development", "production", "staging"] = Field(
            default="development", description="Application environment"
        )

        # Supabase
        SUPABASE_URL: str = Field(default="https://test.supabase.co", description="Supabase project URL")
        SUPABASE_SERVICE_KEY: str = Field(default="test-service-key", description="Supabase service role key")

        # WorkOS
        WORKOS_AUDIENCE: str = Field(default="api.workos.com", description="WorkOS audience")
        WORKOS_ISSUER: str = Field(default="api.workos.com", description="WorkOS issuer")
        WORKOS_CLIENT_ID: str = Field(default="test-client-id", description="WorkOS client ID")
        WORKOS_JWKS_URL: str = Field(default="https://api.workos.com/v1/jwks", description="WorkOS JWKS URL")

        # PayHere
        PAYHERE_MERCHANT_ID: str = Field(default="test-merchant-id", description="PayHere merchant ID")
        PAYHERE_MERCHANT_SECRET: str = Field(default="test-merchant-secret", description="PayHere merchant secret")
        PAYHERE_SANDBOX: bool = Field(default=True, description="Use PayHere sandbox")
        PAYHERE_CREDIT_RATE_LKR: float = Field(default=350.0, description="Credit rate in LKR")

        # Workers
        HTTP_WORKER_URL: str | None = Field(default=None, description="HTTP worker URL")
        BROWSER_WORKER_URL: str | None = Field(default=None, description="Browser worker URL")
        SDK_WORKER_URL: str | None = Field(default=None, description="SDK worker URL")

        # Orchestrator
        ORCHESTRATOR_URL: str | None = Field(default=None, description="Orchestrator URL")

        # Google Cloud
        GOOGLE_CLOUD_PROJECT: str = Field(default="test-project", description="Google Cloud project ID")
        CLOUD_RUN_LOCATION: str = Field(default="us-central1", description="Cloud Run location")

        # Frontend
        FRONTEND_URL: str = Field(default="http://localhost:3000", description="Frontend URL")

        # API
        API_URL: str = Field(default="http://localhost:8080", description="API URL")
        PORT: int = Field(default=8080, description="API port")

        # Cloud Tasks Queue
        QUEUE_PATH: str | None = Field(default=None, description="Cloud Tasks queue path")
        PAYHERE_ALLOWED_IPS: str | None = Field(default=None, description="PayHere allowed IPs")

        # Development Mode (CRITICAL: Never enable in production)
        DEV_MODE: bool = Field(
            default=False,
            description="Enable development mode (bypasses credit checks - NEVER enable in production)",
        )

        class Config:
            case_sensitive = False
            env_file = ".env"
            extra = "ignore"

        @validator("ENVIRONMENT")
        @classmethod
        def validate_environment(cls, v: str) -> str:
            if v not in ["development", "production", "staging"]:
                raise ValueError("ENVIRONMENT must be development, production, or staging")
            return v

        @validator("DEV_MODE")
        @classmethod
        def validate_dev_mode(cls, v: bool, values) -> bool:
            """Prevent DEV_MODE in production/staging environments."""
            if v and values.get("ENVIRONMENT") in ["production", "staging"]:
                raise ValueError(
                    "CRITICAL SECURITY: DEV_MODE cannot be enabled in production or staging. "
                    "This would bypass all credit checks and payment processing."
                )
            return v

        @property
        def workos_audience(self) -> str:
            """Get WorkOS audience based on environment."""
            if self.ENVIRONMENT == "production":
                return "api.workos.com"
            return "api.workos.com/staging"

        @property
        def workos_issuer(self) -> str:
            """Get WorkOS issuer based on environment."""
            if self.ENVIRONMENT == "production":
                return "api.workos.com"
            return "api.workos.com/staging"

        @property
        def is_production(self) -> bool:
            """Check if running in production."""
            return self.ENVIRONMENT == "production"

        @property
        def queue_path(self) -> str:
            """Get Cloud Tasks queue path."""
            if self.QUEUE_PATH:
                return self.QUEUE_PATH
            return f"projects/{self.GOOGLE_CLOUD_PROJECT}/locations/{self.CLOUD_RUN_LOCATION}/queues/seo-audit-queue"

        @property
        def allowed_origins(self) -> list:
            """Get allowed CORS origins."""
            origins = [self.FRONTEND_URL, "http://localhost:3000"]
            return [o for o in origins if o]  # Filter out None

        @property
        def docs_enabled(self) -> bool:
            """Check if docs should be enabled."""
            return self.ENVIRONMENT != "production"


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def validate_required_settings() -> None:
    """Validate that all required settings are present."""
    settings = get_settings()
    required_errors = []

    # Base required vars (always needed)
    required_vars: dict[str, str] = {}

    # Check required based on environment
    if settings.is_production:
        required_vars = {
            "SUPABASE_URL": "Supabase project URL",
            "SUPABASE_SERVICE_KEY": "Supabase service role key",
            "WORKOS_AUDIENCE": "WorkOS audience for JWT validation",
            "WORKOS_ISSUER": "WorkOS issuer for JWT tokens",
            "WORKOS_CLIENT_ID": "WorkOS client ID",
            "PAYHERE_MERCHANT_ID": "PayHere merchant ID",
            "PAYHERE_MERCHANT_SECRET": "PayHere merchant secret for hash generation",
            "FRONTEND_URL": "Frontend application URL",
            "GOOGLE_CLOUD_PROJECT": "Google Cloud project ID",
        }

        # Workers are required in production
        required_vars.update(
            {
                "HTTP_WORKER_URL": "HTTP worker URL for task execution",
                "BROWSER_WORKER_URL": "Browser worker URL for visual analysis",
            }
        )

    # Validate
    for var_name, description in required_vars.items():
        value = getattr(settings, var_name, None)
        if not value:
            required_errors.append(f"  - {var_name} ({description})")

    if required_errors:
        error_msg = "Missing required environment variables:\n" + "\n".join(required_errors)
        raise RuntimeError(error_msg)


def get_supabase_client():
    """Get Supabase client using centralized configuration."""
    from supabase import create_client

    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def get_database_url(setting_name: str) -> str:
    """Get database URL from settings with fallback."""
    settings = get_settings()
    url = getattr(settings, setting_name, None)
    if not url:
        raise RuntimeError(f"Database URL {setting_name} not configured")
    return url


def is_sandbox_mode() -> bool:
    """Check if PayHere sandbox mode is enabled."""
    settings = get_settings()
    return settings.PAYHERE_SANDBOX


def get_credit_rate_lkr() -> float:
    """Get credit rate in LKR."""
    settings = get_settings()
    return settings.PAYHERE_CREDIT_RATE_LKR
