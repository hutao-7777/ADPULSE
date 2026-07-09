"""Application configuration loaded from environment variables."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AdPulse settings. Runtime target is SQLite via aiosqlite."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "AdPulse"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite+aiosqlite:///./adpulse.db"

    # Security settings. SECRET_KEY must be explicitly set in production.
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS whitelist (comma-separated string). Wildcards are not allowed by default.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost"

    # LLM provider placeholders for the agent.
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"

    # Agent memory.
    AGENT_MEMORY_TOP_K: int = 5

    # Public registration control.
    ENABLE_PUBLIC_REGISTRATION: bool = False

    @model_validator(mode="after")
    def _validate_security(self):
        key = (self.SECRET_KEY or "").strip()
        if not key or key.lower() in {"change-me", "change-me-in-production", "secret"}:
            raise ValueError(
                "SECRET_KEY must be set to a non-default value. "
                "Set it via the SECRET_KEY environment variable."
            )
        if "*" in self.CORS_ORIGINS:
            raise ValueError(
                "CORS_ORIGINS cannot contain wildcards. "
                "Use a comma-separated list of exact origins."
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS_ORIGINS as a list of strings."""
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]


settings = Settings()
