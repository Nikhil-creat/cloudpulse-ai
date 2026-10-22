from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CloudPulse AI"
    database_url: str = "postgresql+asyncpg://cloudpulse:cloudpulse@localhost:5432/cloudpulse"
    sync_database_url: str = "postgresql+psycopg://cloudpulse:cloudpulse@localhost:5432/cloudpulse"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    jwt_secret: str = "change-me"
    jwt_alg: str = "HS256"
    jwt_ttl_minutes: int = 60
    fernet_key: str = ""
    admin_email: str = "admin@cloudpulse.local"
    admin_password: str = "change-me-now"

    groq_api_key: str = ""
    gemini_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-2.5-flash"
    llm_timeout_s: float = 20.0
    breaker_cooldown_s: float = 30.0
    cache_threshold: float = 0.92
    cache_ttl_s: int = 3600

    blast_radius_max: int = 10
    otlp_endpoint: str = ""
    cors_origins: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
