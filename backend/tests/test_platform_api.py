"""
Automated tests for Platform API endpoints, overview data, module registries, and Pydantic validation.
"""

from backend.models import Role


def test_list_roles_contract(client):
    """Verifies that /api/v1/auth/roles returns all 5 platform roles with correct permissions."""
    resp = client.get("/api/v1/auth/roles")
    assert resp.status_code == 200
    data = resp.json()
    assert "roles" in data
    assert len(data["roles"]) == 5

    role_names = [item["role"] for item in data["roles"]]
    assert Role.ORGANISATION_ADMIN.value in role_names
    assert Role.PROJECT_MANAGER.value in role_names
    assert Role.FIELD_OFFICER.value in role_names
    assert Role.ANALYST.value in role_names
    assert Role.VIEWER.value in role_names


def test_modules_status_registry(client, auth_headers):
    """Verifies module status registry lists all 4 platform modules."""
    headers = auth_headers(Role.VIEWER)
    resp = client.get("/api/v1/modules/status", headers=headers)
    assert resp.status_code == 200
    modules = resp.json()
    assert len(modules) == 4

    module_ids = {m["id"] for m in modules}
    assert module_ids == {"agrotrack", "marketlens", "impactos", "analyst"}

    # Verify status labels
    statuses = {m["id"]: m["status"] for m in modules}
    assert statuses["agrotrack"] == "active"
    assert statuses["marketlens"] in ["development", "operational", "active"]
    assert statuses["impactos"] in ["development", "operational", "active"]
    assert statuses["analyst"] in ["preview", "operational", "active"]


def test_platform_overview_schema_and_metrics(client, auth_headers):
    """Verifies platform overview metrics, organisation, and project summaries."""
    headers = auth_headers(Role.ORGANISATION_ADMIN)
    resp = client.get("/api/v1/platform/overview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Organisation details
    org = data["organisation"]
    assert org["name"] == "GreenValley AgTech Cooperative"
    assert org["code"] == "GV-AGTECH"

    # Metrics
    metrics = data["metrics"]
    assert metrics["activeFarms"] > 0
    assert metrics["registeredFarmers"] > 0
    assert metrics["diagnosticScans"] > 0

    # Modules
    assert len(data["modules"]) == 4

    # Projects
    assert len(data["projects"]) >= 1
    for p in data["projects"]:
        assert "targetBeneficiaries" in p
        assert "budget" in p

    # Recent Activity
    assert len(data["recentActivity"]) >= 1


def test_current_organisation_contract(client, auth_headers):
    """Verifies /api/v1/organisations/current endpoint."""
    headers = auth_headers(Role.FIELD_OFFICER)
    resp = client.get("/api/v1/organisations/current", headers=headers)
    assert resp.status_code == 200
    org = resp.json()
    assert org["id"] == "org_greenvalley_01"
    assert org["tier"] == "enterprise"
