"""Tests for config settings integration."""
import os
import pytest
from app.config import get_setting
from app.database import init_db


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database is initialized before tests."""
    os.makedirs("data", exist_ok=True)
    init_db()


def test_get_setting_from_db():
    """get_setting should check database first."""
    # This will return None or env value if DB empty
    result = get_setting("tmdb_api_key")
    # Should not raise, returns value or None
    assert result is None or isinstance(result, str)
