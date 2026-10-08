from typing import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from api.config import settings


def make_engine(url: str) -> Engine:
    """Create a SQLAlchemy engine with pre-ping enabled.

    Args:
        url: Database connection URL.

    Returns:
        The created `Engine`.
    """
    return create_engine(url, pool_pre_ping=True)


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def ping(target: Engine = engine) -> None:
    """Check connectivity by running a trivial query against the engine.

    Args:
        target: Engine to check; defaults to the module's primary engine.

    Raises:
        Exception: Whatever the underlying driver raises if the connection
            or query fails.
    """
    with target.connect() as conn:
        conn.execute(text("SELECT 1"))


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a request-scoped database session.

    Yields:
        A `Session` bound to the primary engine, closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
