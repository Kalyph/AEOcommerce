from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings


def get_engine():
    """Create and return the database engine."""
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    
    engine = create_engine(
        settings.database_url,
        echo=False,
        connect_args=connect_args
    )
    return engine


engine = get_engine()


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency for getting database sessions."""
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()


def get_sync_session():
    """Get a session synchronously (for non-Dep injection use)."""
    return Session(engine)
