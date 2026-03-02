from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    IMPORTANT: Do not hardcode secrets. Configure via .env in deployment.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database (provided by database container)
    POSTGRES_URL: str = Field(
        ...,
        description=(
            "PostgreSQL connection URL. Provided by the platform. "
            "Example: postgresql://user:pass@host:port/dbname"
        ),
    )

    # Auth/JWT
    JWT_SECRET: str = Field(
        ...,
        description="Secret used to sign JWT access tokens.",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm.",
    )
    JWT_EXPIRES_MINUTES: int = Field(
        default=60 * 24,
        description="Access token expiration in minutes.",
    )

    # Feature flags / policy
    REQUIRE_ADMIN_APPROVAL: bool = Field(
        default=True,
        description="If true, new users start as pending and must be approved by an admin.",
    )

    OTP_TTL_SECONDS: int = Field(
        default=10 * 60,
        description="OTP validity window in seconds.",
    )

    OTP_TEST_BYPASS: bool = Field(
        default=False,
        description=(
            "If true, OTP is returned in API response for local development/testing. "
            "Never enable in production."
        ),
    )


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """Get cached Settings instance.

    Returns:
        Settings: application configuration.
    """
    # Simple singleton; FastAPI will import once in typical usage.
    global _SETTINGS  # noqa: PLW0603
    try:
        return _SETTINGS
    except NameError:
        _SETTINGS = Settings()  # type: ignore[assignment]
        return _SETTINGS
