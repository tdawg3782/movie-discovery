"""Tests for the idempotent additive watchlist column migration."""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

# Import models FIRST to register them with Base.metadata
from app.models import Watchlist  # noqa: F401
from app.database import Base, _migrate_watchlist_columns


def _make_engine():
    """Shared in-memory SQLite engine (StaticPool keeps one connection)."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _create_legacy_table(engine):
    """Create a pre-migration watchlist table (true original schema)."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE watchlist ("
                "id INTEGER PRIMARY KEY, "
                "tmdb_id INTEGER, "
                "media_type TEXT, "
                "added_at TIMESTAMP, "
                "notes TEXT, "
                "status TEXT)"
            )
        )


def test_migration_adds_columns_to_legacy_table():
    engine = _make_engine()
    _create_legacy_table(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO watchlist "
                "(tmdb_id, media_type, status) VALUES (42, 'movie', 'pending')"
            )
        )

    _migrate_watchlist_columns(engine)

    columns = {c["name"] for c in inspect(engine).get_columns("watchlist")}
    # Generic/future-proof: every model column must exist after migration.
    for col in Base.metadata.tables["watchlist"].columns:
        assert col.name in columns, f"missing migrated column: {col.name}"
    # Specifically the columns this slice backfills.
    assert "selected_seasons" in columns
    assert "is_season_update" in columns
    assert "priority" in columns
    assert "tags" in columns

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT priority, tags, selected_seasons, is_season_update "
                "FROM watchlist"
            )
        ).fetchone()
    assert row[0] == 0
    assert row[1] is None
    assert row[2] is None
    assert row[3] == 0


def test_migration_is_idempotent():
    engine = _make_engine()
    _create_legacy_table(engine)

    _migrate_watchlist_columns(engine)
    _migrate_watchlist_columns(engine)  # second run must not raise

    columns = [c["name"] for c in inspect(engine).get_columns("watchlist")]
    assert columns.count("priority") == 1
    assert columns.count("tags") == 1


def test_fresh_create_all_has_new_columns():
    engine = _make_engine()
    Base.metadata.create_all(bind=engine)

    # migration is a no-op on a freshly created table
    _migrate_watchlist_columns(engine)

    columns = {c["name"] for c in inspect(engine).get_columns("watchlist")}
    assert "priority" in columns
    assert "tags" in columns
