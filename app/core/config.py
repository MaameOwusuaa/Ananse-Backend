"""Application settings, read once from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

@property
def database_host(self) -> str:
    """Return the configured database host without exposing credentials."""
    from urllib.parse import urlparse

    parsed = urlparse(self.database_url)
    return parsed.hostname or "no-host"

class Settings(BaseSettings):
    """Every value can be overridden in .env."""

    app_name: str = "ANANSE API"
    api_prefix: str = "/api"

    database_url: str = "sqlite:///./ananse.db"

    secret_key: str = "development-only-change-me"
    access_token_minutes: int = 10080
    algorithm: str = "HS256"

    allowed_origins: str = (
        "http://localhost:5500,"
        "http://127.0.0.1:5500,"
        "http://localhost:5501,"
        "http://127.0.0.1:5501,"
        "http://localhost:8080"
    )
    
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:1b"
    tavily_api_key: str = "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"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

    @property
    def origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()