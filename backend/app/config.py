import warnings

from pydantic_settings import BaseSettings

_INSECURE_DEFAULT_KEY = "your-secret-key-change-in-production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # JWT Configuration
    SECRET_KEY: str = _INSECURE_DEFAULT_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Database
    DATABASE_URL: str = "sqlite:///./fantasy_cricket.db"

    # Sentry
    SENTRY_DSN: str = ""
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1

    # CORS Configuration (comma-separated origins for production)
    CORS_ORIGINS: str = "http://localhost:3000"
    FRONTEND_URL: str = "http://localhost:3000"

    def get_cors_origins(self) -> list[str]:
        """Parse CORS_ORIGINS string into list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()

if settings.SECRET_KEY == _INSECURE_DEFAULT_KEY:
    warnings.warn(
        "SECRET_KEY is using the insecure default. "
        "Set a strong SECRET_KEY in your .env file for production.",
        stacklevel=1,
    )
