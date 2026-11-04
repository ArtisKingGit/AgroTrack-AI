"""
Tests for AgroTrack AI Security Hardening, Persistence, and Rate Limiting.
"""

import pytest
import sqlite3
from fastapi.testclient import TestClient
from backend.main import app
from backend import security
from backend.db.database import (
    get_db_connection,
    save_record,
    get_record,
    list_records,
    DB_PATH
)


def test_config_endpoint_returns_environment_and_auth_policy(client):
    """Verifies /api/v1/config endpoint discloses environment configuration for frontend gating."""
    resp = client.get("/api/v1/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "environment" in data
    assert "allowDevMockAuth" in data
    assert isinstance(data["allowDevMockAuth"], bool)


def test_production_mode_strictly_rejects_mock_tokens(monkeypatch):
    """
    Ensures that when ALLOW_DEV_MOCK_AUTH is False or ENVIRONMENT is production,
    all mock tokens are strictly rejected with HTTP 401.
    """
    monkeypatch.setattr(security, "ALLOW_DEV_MOCK_AUTH", False)
    monkeypatch.setattr(security, "IS_PRODUCTION", True)

    with TestClient(app) as local_client:
        # 1. Reject mock token
        resp = local_client.get(
            "/api/v1/agrotrack/farms",
            headers={"Authorization": "Bearer mock-token-admin"}
        )
        assert resp.status_code == 401
        assert "strictly disabled" in resp.json()["detail"]

        # 2. Reject mock JWT
        resp = local_client.get(
            "/api/v1/agrotrack/farms",
            headers={"Authorization": "Bearer mock-jwt:usr_admin_001"}
        )
        assert resp.status_code == 401
        assert "strictly disabled" in resp.json()["detail"]


def test_sqlite_wal_persistence_and_pragmas():
    """
    Verifies that the SQLite database runs in WAL mode and persists data across connections.
    """
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode;")
    row = cur.fetchone()
    journal_mode = row[0].upper()
    conn.close()

    assert journal_mode == "WAL"

    # Verify document persistence
    test_doc = {
        "id": "frmr_persist_999",
        "orgId": "org_greenvalley_01",
        "firstName": "Persist",
        "lastName": "Test"
    }
    save_record("farmers", test_doc, org_id="org_greenvalley_01")

    # Fetch with a fresh connection
    fetched = get_record("farmers", "frmr_persist_999", org_id="org_greenvalley_01")
    assert fetched is not None
    assert fetched["firstName"] == "Persist"


def test_rate_limiter_triggers_429():
    """
    Verifies that exceeding the 30 req/min rate limit on compute/chat endpoints returns HTTP 429.
    """
    from backend.main import RATE_LIMIT_STORE
    RATE_LIMIT_STORE.clear()

    with TestClient(app) as local_client:
        # Send 30 requests within limit
        for _ in range(30):
            resp = local_client.post(
                "/chat",
                json={"message": "hello"}
            )
            assert resp.status_code != 429

        # The 31st request from same IP must receive HTTP 429 Too Many Requests
        resp_31 = local_client.post(
            "/chat",
            json={"message": "rate limit test"}
        )
        assert resp_31.status_code == 429
        assert "Rate limit exceeded" in resp_31.json()["error"]

    # Clean up rate limit store
    RATE_LIMIT_STORE.clear()
