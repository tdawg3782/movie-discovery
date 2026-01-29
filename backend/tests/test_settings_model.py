"""Tests for Settings database model."""
import os
import pytest
from app.models import Settings
from app.database import engine, init_db
from sqlalchemy import inspect


@pytest.fixture(autouse=True)
def setup_database():
    """Ensure database is initialized before tests."""
    os.makedirs("data", exist_ok=True)
    init_db()


def test_settings_table_exists():
    """Settings table should exist in database."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "settings" in tables


def test_settings_model_fields():
    """Settings model should have required fields."""
    assert hasattr(Settings, "id")
    assert hasattr(Settings, "key")
    assert hasattr(Settings, "value")
    assert hasattr(Settings, "encrypted")
