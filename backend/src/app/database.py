"""Database connection and session management."""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency that provides database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_watchlist_columns(bind=engine) -> None:
    """Add columns introduced after the table already exists (SQLite ALTER ADD COLUMN). Idempotent."""
    inspector = inspect(bind)
    if "watchlist" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("watchlist")}
    stmts = []
    if "priority" not in existing:
        stmts.append("ALTER TABLE watchlist ADD COLUMN priority INTEGER NOT NULL DEFAULT 0")
    if "tags" not in existing:
        stmts.append("ALTER TABLE watchlist ADD COLUMN tags TEXT")
    if stmts:
        with bind.begin() as conn:
            for s in stmts:
                conn.execute(text(s))


def init_db():
    """Create all tables, then apply lightweight additive migrations."""
    Base.metadata.create_all(bind=engine)
    _migrate_watchlist_columns()
