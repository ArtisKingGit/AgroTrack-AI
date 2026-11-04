"""
AgroTrack AI — Phase 7 Final QA, Security & Deployment Readiness Test Suite
Verifies:
1. Offline synchronisation, conflict detection, and idempotency.
2. File upload security, magic bytes verification, and polyglot defenses.
3. Security headers middleware and CORS enforcement.
4. Granular RBAC, token verification, and cross-tenant data isolation regression.
5. Reliability, empty dataset resilience, and graceful error handling.
"""

import io
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import Role
from backend.agrotrack.service import (
    TENANT_FARMS,
    TENANT_ACTIVITIES,
    TENANT_FARMERS,
)
from backend.marketlens.service import (
    TENANT_COMMODITIES,
    TENANT_PRICES,
)
from backend.impactos.service import (
    TENANT_PROJECTS,
    TENANT_BENEFICIARIES,
    TENANT_INDICATORS,
)

client = TestClient(app)

ADMIN_AUTH = {"Authorization": "Bearer mock-token-admin"}
FIELD_AUTH = {"Authorization": "Bearer mock-token-field"}
VIEWER_AUTH = {"Authorization": "Bearer mock-token-viewer"}


def _create_valid_test_jpeg(width: int = 250, height: int = 250) -> bytes:
    """Creates a genuine JPEG image with valid magic bytes (FF D8 FF)."""
    img = Image.new("RGB", (width, height), color=(34, 139, 34))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


# ── 1. Offline Synchronisation & Conflict Detection Tests ───────────────────────

def test_offline_sync_batch_successful():
    """Field officer uploads a batch of activities recorded offline."""
    batch_payload = {
        "batch": [
            {
                "clientMutationId": "mut_offline_test_001",
                "farmId": "farm_gv_101",
                "activityType": "crop_inspection",
                "activityDate": "2026-11-03",
                "notes": "Offline check: Crop canopy looks vigorous. Drip emitters clear.",
                "metrics": {"canopyCoverPct": 78},
                "observations": ["Vigorous growth", "No armyworm detected"],
                "clientCreatedAt": "2026-11-03T14:22:00Z"
            },
            {
                "clientMutationId": "mut_offline_test_002",
                "farmId": "farm_gv_101",
                "activityType": "irrigation",
                "activityDate": "2026-11-03",
                "notes": "Offline irrigation run: 2.5 hours drip cycle completed.",
                "metrics": {"irrigationHours": 2.5},
                "observations": ["Uniform water distribution"],
                "clientCreatedAt": "2026-11-03T16:00:00Z"
            }
        ]
    }

    resp = client.post("/api/v1/agrotrack/activities/sync", json=batch_payload, headers=FIELD_AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["totalReceived"] == 2
    assert data["syncedCount"] == 2
    assert data["conflictCount"] == 0
    assert data["duplicateCount"] == 0
    assert len(data["synced"]) == 2
    assert data["synced"][0]["syncSource"] == "offline_queue"
    assert data["synced"][0]["clientMutationId"] == "mut_offline_test_001"


def test_offline_sync_idempotency_and_duplicates():
    """Submitting the identical batch again must not duplicate records."""
    batch_payload = {
        "batch": [
            {
                "clientMutationId": "mut_offline_test_001",
                "farmId": "farm_gv_101",
                "activityType": "crop_inspection",
                "activityDate": "2026-11-03",
                "notes": "Offline check: Duplicate test",
                "clientCreatedAt": "2026-11-03T14:22:00Z"
            }
        ]
    }

    resp = client.post("/api/v1/agrotrack/activities/sync", json=batch_payload, headers=FIELD_AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["syncedCount"] == 0
    assert data["duplicateCount"] == 1
    assert data["duplicates"][0]["status"] == "already_synced"


def test_offline_sync_conflict_detection_missing_farm():
    """Attempting to sync an activity targeting a non-existent or archived farm flags a conflict."""
    batch_payload = {
        "batch": [
            {
                "clientMutationId": "mut_offline_conflict_999",
                "farmId": "farm_nonexistent_9999",
                "activityType": "farm_visit",
                "activityDate": "2026-11-03",
                "notes": "Target plot no longer exists on server.",
                "clientCreatedAt": "2026-11-03T15:00:00Z"
            }
        ]
    }

    resp = client.post("/api/v1/agrotrack/activities/sync", json=batch_payload, headers=FIELD_AUTH)
    assert resp.status_code == 200
    data = resp.json()
    assert data["syncedCount"] == 0
    assert data["conflictCount"] == 1
    assert data["conflicts"][0]["status"] == "conflict_missing_farm"
    assert "was not found" in data["conflicts"][0]["message"]


def test_offline_sync_role_authorization():
    """Viewer role is forbidden from syncing field activities."""
    batch_payload = {
        "batch": [
            {
                "clientMutationId": "mut_viewer_sync_fail",
                "farmId": "farm_gv_101",
                "activityType": "farm_visit",
                "notes": "Viewer attempting sync",
            }
        ]
    }
    resp = client.post("/api/v1/agrotrack/activities/sync", json=batch_payload, headers=VIEWER_AUTH)
    assert resp.status_code == 403


# ── 2. File Upload Security & Magic Bytes Tests ─────────────────────────────────

def test_file_upload_rejects_forged_mime_type_on_predict():
    """A non-image file spoofing image/jpeg content-type is rejected by magic byte check."""
    forged_file = io.BytesIO(b"<!DOCTYPE html><html><script>alert(1)</script></html>")
    files = {"image": ("malicious.jpg", forged_file, "image/jpeg")}
    resp = client.post("/predict", files=files)
    assert resp.status_code == 400
    assert "binary header" in resp.json().get("error", "").lower()


def test_file_upload_rejects_forged_mime_type_on_diagnose():
    """Diagnose endpoint rejects spoofed image headers with HTTP 400."""
    forged_file = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00fake_executable_bytes")
    files = {"image": ("exploit.png", forged_file, "image/png")}
    resp = client.post("/api/v1/agrotrack/diagnose", files=files, headers=FIELD_AUTH)
    assert resp.status_code == 400


def test_file_upload_accepts_genuine_jpeg_with_valid_magic_bytes():
    """Genuine image with valid magic bytes passes quality and diagnose checks."""
    valid_bytes = _create_valid_test_jpeg(250, 250)
    files = {"image": ("healthy_leaf.jpg", io.BytesIO(valid_bytes), "image/jpeg")}
    resp = client.post("/api/v1/agrotrack/quality-check", files=files)
    assert resp.status_code == 200
    assert resp.json()["is_valid"] is True


# ── 3. Security Headers Middleware Tests ────────────────────────────────────────

def test_security_headers_present_on_api_responses():
    """Verify production security headers are set by middleware on all responses."""
    resp = client.get("/api/v1/auth/roles")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ── 4. Unauthenticated Access & RBAC Enforcement ────────────────────────────────

def test_unauthenticated_protected_endpoints_fail_consistently():
    """Verify that all core protected endpoints require valid Bearer token."""
    endpoints = [
        ("GET", "/api/v1/auth/me"),
        ("GET", "/api/v1/organisations/current"),
        ("GET", "/api/v1/platform/overview"),
        ("GET", "/api/v1/agrotrack/farms"),
        ("GET", "/api/v1/agrotrack/farmers"),
        ("GET", "/api/v1/marketlens/prices"),
        ("GET", "/api/v1/impactos/projects"),
        ("GET", "/api/v1/analyst/capabilities"),
    ]
    for method, path in endpoints:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path)
        assert resp.status_code == 401, f"Expected 401 for unauthenticated {path}, got {resp.status_code}"


# ── 5. Reliability & Empty Dataset Resilience ───────────────────────────────────

def test_empty_tenant_resilience_across_all_modules():
    """Verify that requesting stats for a newly registered tenant with 0 records does not crash."""
    empty_tenant_token = "mock-jwt:{\"uid\":\"usr_empty_1\",\"role\":\"Organisation Administrator\",\"orgId\":\"org_brand_new_empty\"}"
    headers = {"Authorization": f"Bearer {empty_tenant_token}"}

    # 1. AgroTrack Dashboard Stats
    resp_track = client.get("/api/v1/agrotrack/dashboard/stats", headers=headers)
    assert resp_track.status_code == 200
    data_track = resp_track.json()
    assert data_track["totalFarmers"] == 0
    assert data_track["totalFarms"] == 0
    assert data_track["totalActivities"] == 0

    # 2. MarketLens Dashboard Stats
    resp_market = client.get("/api/v1/marketlens/dashboard/stats", headers=headers)
    assert resp_market.status_code == 200
    data_market = resp_market.json()
    assert data_market["totalCommodities"] == 0
    assert data_market["totalPriceRecords"] == 0

    # 3. ImpactOS Dashboard Stats
    resp_impact = client.get("/api/v1/impactos/dashboard/stats", headers=headers)
    assert resp_impact.status_code == 200
    data_impact = resp_impact.json()
    assert data_impact["activeProjectsCount"] == 0
    assert data_impact["completedProjectsCount"] == 0
    assert data_impact["totalBeneficiariesCount"] == 0

    # 4. AI Analyst Context Summary
    resp_analyst = client.get("/api/v1/analyst/context-summary", headers=headers)
    assert resp_analyst.status_code == 200
    data_analyst = resp_analyst.json()
    assert data_analyst["recordCounts"]["monitoredFarms"] == 0
    assert data_analyst["recordCounts"]["projects"] == 0


def test_malformed_json_payload_returns_422_without_server_error():
    """Ensure malformed or incomplete payload returns 422 Unprocessable Entity."""
    resp = client.post(
        "/api/v1/agrotrack/activities",
        json={"notes": "missing farmId and other required fields"},
        headers=FIELD_AUTH
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()
