"""Application settings, read once from the environment."""

from functools import lru_cache

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_UNSUPPORTED_URL_OPTIONS = {"ssl-mode", "ssl_mode", "sslmode"}


class Settings(BaseSettings):
    """Every value can be overridden in .env."""

    app_name: str = "ANANSE API"
    api_prefix: str = "/api"

    database_url: str = "sqlite:///./ananse.db"

    secret_key: str = "development-only-change-me"
    access_token_minutes: int = 10080
    algorithm: str = "HS256"
    google_client_id: str = ""

    allowed_origins: str = (
        "http://localhost:5500,"
        "http://127.0.0.1:5500,"
        "https://ananse-silk.vercel.app/,"
        "https://ananse-silk.vercel.app"    
    )
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    ollama_url: str = ""
    ollama_model: str = "llama3.2:1b"
    
    
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

    @property
    def database_host(self) -> str:
        """Return the configured database host without exposing credentials."""
        from urllib.parse import urlparse

        parsed = urlparse(self.database_url)
        return parsed.hostname or "no-host"


    

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()