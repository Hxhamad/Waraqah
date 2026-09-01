"""Pytest fixtures for Waraqah tests."""
import os
import pytest
from fastapi.testclient import TestClient

from waraqah.core.db import init_db
from waraqah.api.main import app


@pytest.fixture(scope="session")
def test_db():
    """Create a test database."""
    db_path = "test_waraqah.db"
    os.environ["DATABASE_PATH"] = db_path
    init_db(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client(test_db):
    """Create a test client."""
    return TestClient(app)
