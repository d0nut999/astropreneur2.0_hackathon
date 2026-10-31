"""Database engine and session management."""
import os
from sqlmodel import create_engine, Session, SQLModel
from .config import settings


# Create engine for SQLite
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=settings.app_env == "dev",
)


def init_db():
    """Create all tables."""
    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)
    os.makedirs("./data/uploads", exist_ok=True)
    os.makedirs("./data/llm_cache", exist_ok=True)

    # Create tables
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session dependency."""
    with Session(engine) as session:
        yield session
