"""
Automated tests for Authentication and Role-Based Access Control (RBAC).
Verifies:
- 401 on unauthenticated or malformed requests
- Access permissions across all 5 roles:
  * Organisation Administrator
  * Project Manager
  * Field Officer
  * Analyst
  * Viewer
"""

import pytest
from backend.models import Role


def test_unauthenticated_request_rejected(client):
    """Endpoints requiring authentication must return 401 Unauthorized when token is missing."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_invalid_bearer_token_rejected(client):
    """Malformed or invalid tokens must return 401 Unauthorized."""
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token-xyz"})
    assert response.status_code == 401


def test_admin_full_access(client, auth_headers):
    """Organisation Administrator must have access to all protected endpoints."""
    headers = auth_headers(Role.ORGANISATION_ADMIN)

    # 1. Profile
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["activeRole"] == Role.ORGANISATION_ADMIN.value

    # 2. Members List (Admin / PM only)
    members = client.get("/api/v1/organisations/members", headers=headers)
    assert members.status_code == 200
    assert len(members.json()) >= 1

    # 3. Add Member (Admin only)
    new_member_payload = {
        "name": "Jane Muthoni",
        "email": "jane.muthoni@agrotrack.ai",
        "role": Role.FIELD_OFFICER.value
    }
    added = client.post("/api/v1/organisations/members", json=new_member_payload, headers=headers)
    assert added.status_code == 201
    assert added.json()["email"] == "jane.muthoni@agrotrack.ai"

    # 4. Create Project
    proj_payload = {
        "name": "Highland Tea Quality Project",
        "code": "TEA-Q26",
        "targetBeneficiaries": 300,
        "budget": 1500000.0
    }
    proj = client.post("/api/v1/projects", json=proj_payload, headers=headers)
    assert proj.status_code == 201


def test_project_manager_permissions(client, auth_headers):
    """Project Manager can manage projects and view members, but cannot add organisation members."""
    headers = auth_headers(Role.PROJECT_MANAGER)

    # Can view members
    members = client.get("/api/v1/organisations/members", headers=headers)
    assert members.status_code == 200

    # CANNOT add members (Admin only) -> 403 Forbidden
    forbidden_add = client.post(
        "/api/v1/organisations/members",
        json={"name": "Test", "email": "test@agrotrack.ai", "role": Role.VIEWER.value},
        headers=headers
    )
    assert forbidden_add.status_code == 403

    # Can create projects
    proj = client.post(
        "/api/v1/projects",
        json={"name": "PM Managed Project", "code": "PM-PROJ", "targetBeneficiaries": 100, "budget": 500000.0},
        headers=headers
    )
    assert proj.status_code == 201


def test_field_officer_permissions(client, auth_headers):
    """Field Officer can register farmers, but cannot view member management or export reports."""
    headers = auth_headers(Role.FIELD_OFFICER)

    # Can register farmers
    farmer_payload = {
        "firstName": "Peter",
        "lastName": "Ochieng",
        "phone": "+254711223344",
        "county": "Kisumu",
        "acreage": 2.5
    }
    registered = client.post("/api/v1/farmers", json=farmer_payload, headers=headers)
    assert registered.status_code == 201
    assert registered.json()["assignedRole"] == Role.FIELD_OFFICER.value

    # Cannot view members (403)
    assert client.get("/api/v1/organisations/members", headers=headers).status_code == 403

    # Cannot create projects (403)
    assert client.post(
        "/api/v1/projects",
        json={"name": "FO Project", "code": "FO-01", "targetBeneficiaries": 50, "budget": 100000.0},
        headers=headers
    ).status_code == 403

    # Cannot export impact reports (403)
    assert client.get("/api/v1/reports/export", headers=headers).status_code == 403


def test_analyst_permissions(client, auth_headers):
    """Analyst can export impact reports, but cannot register farmers or create projects."""
    headers = auth_headers(Role.ANALYST)

    # Can export impact reports
    report = client.get("/api/v1/reports/export", headers=headers)
    assert report.status_code == 200
    assert report.json()["generatedRole"] == Role.ANALYST.value

    # Cannot register farmers (403)
    assert client.post(
        "/api/v1/farmers",
        json={"firstName": "X", "lastName": "Y", "phone": "123", "county": "Z", "acreage": 1.0},
        headers=headers
    ).status_code == 403

    # Cannot create projects (403)
    assert client.post(
        "/api/v1/projects",
        json={"name": "A Project", "code": "AP-01", "targetBeneficiaries": 50, "budget": 100000.0},
        headers=headers
    ).status_code == 403


def test_viewer_read_only_restriction(client, auth_headers):
    """Viewer role has read access to overview, but is denied on all mutating operations."""
    headers = auth_headers(Role.VIEWER)

    # Can view platform overview
    overview = client.get("/api/v1/platform/overview", headers=headers)
    assert overview.status_code == 200
    assert overview.json()["user"]["activeRole"] == Role.VIEWER.value

    # Denied on members (403)
    assert client.get("/api/v1/organisations/members", headers=headers).status_code == 403

    # Denied on farmer creation (403)
    assert client.post(
        "/api/v1/farmers",
        json={"firstName": "V", "lastName": "W", "phone": "000", "county": "C", "acreage": 1.0},
        headers=headers
    ).status_code == 403

    # Denied on project creation (403)
    assert client.post(
        "/api/v1/projects",
        json={"name": "V Proj", "code": "VP-01", "targetBeneficiaries": 10, "budget": 10000.0},
        headers=headers
    ).status_code == 403

    # Denied on report export (403)
    assert client.get("/api/v1/reports/export", headers=headers).status_code == 403
