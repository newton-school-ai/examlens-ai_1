"""Database session setup."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings

engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency that yields a database session and ensures it's closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
