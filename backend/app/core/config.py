"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AdPulse settings. Runtime defaults target SQLite for local/demo use;
    override with environment variables for PostgreSQL/Redis production stacks.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "AdPulse"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database: SQLite by default for local/demo; PostgreSQL in production.
    DATABASE_URL: str = "sqlite+aiosqlite:///./adpulse.db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_RECYCLE: int = 1800

    # Redis: unused in SQLite demo mode.
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_MAX_CONNECTIONS: int = 50

    # Security placeholders for future auth implementation.
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS whitelist (comma-separated string, no wildcard in production).
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # LLM provider placeholders for future agent integration.
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"

    # Agent memory.
    AGENT_MEMORY_TOP_K: int = 5

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS_ORIGINS as a list of strings."""
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]

    @property
    def is_postgres(self) -> bool:
        """Return True when the configured database driver is PostgreSQL."""
        return self.DATABASE_URL.startswith("postgresql")


settings = Settings()
