"""Configuration settings from environment."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration."""

    # App
    app_env: str = "dev"
    secret_key: str = "change-me"
    database_url: str = "sqlite:///./data/hireguard.db"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    # LLM (OpenAI-compatible)
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = "meta-llama/llama-2-7b-chat"
    llm_fallback_models: str = ""  # comma-separated
    llm_temperature: float = 0.0
    llm_cache_enabled: bool = True
    llm_max_attempts: int = 2

    # Email
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    imap_host: str = "mailpit"
    imap_port: int = 1143
    imap_user: str = ""
    imap_password: str = ""
    hr_mailbox: str = "hr@fictional-company.test"

    # Limits
    max_upload_mb: int = 5
    max_video_mb: int = 100
    portal_token_ttl_hours: int = 72

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
