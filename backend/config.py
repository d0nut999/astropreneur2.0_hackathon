"""Application configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"
    DATABASE_URL: str = "postgresql://hackathon_user:hackathon_password@localhost:5432/hackathon_db"
    FRONTEND_URL: str = "http://localhost:5173"
    
    class Config:
        env_file = ".env"


settings = Settings()
