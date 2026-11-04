"""
Pytest configuration and fixtures for AgroTrack AI testing.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import Role


@pytest.fixture(scope="session")
def client():
    """Provides a shared TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    """Helper to generate Authorization header for any supported role."""
    def _headers_for(role: Role) -> dict:
        mapping = {
            Role.ORGANISATION_ADMIN: "mock-token-admin",
            Role.PROJECT_MANAGER: "mock-token-manager",
            Role.FIELD_OFFICER: "mock-token-field",
            Role.ANALYST: "mock-token-analyst",
            Role.VIEWER: "mock-token-viewer",
        }
        token = mapping.get(role, "mock-token-viewer")
        return {"Authorization": f"Bearer {token}"}
    return _headers_for

from backend.db.database import reset_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Resets the persistent database to clean default seed state at test session start."""
    reset_db()
    yield
