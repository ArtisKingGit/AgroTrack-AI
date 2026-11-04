"""
Automated Test Suite for ImpactOS (Phase 5): Project & Development Management
Verifies:
1. Project CRUD, validation, chronological date checks, duplicate code rejection, archiving.
2. Beneficiary management, project enrollment, PII minimization, and role-based masking.
3. Indicators and targets, progress percentage calculations, audit logging without invented results.
4. Field activity tracking with disaggregated attendance (female, male, youth) and output evidence.
5. Dashboard statistics calculated strictly from real database records.
6. M&E Report generation with explicit segregation of verified results vs unverified observations.
7. CSV and clean printable HTML report export endpoints.
8. Role-based access control (Admin, PM, Field Officer, Analyst, Viewer).
9. Multi-tenant organisation isolation.
"""

import pytest
from backend.models import Role, ProjectStatus, BeneficiaryCategory, IndicatorCategory, ReportingFrequency


def test_project_crud_and_validation(client, auth_headers):
    """Verifies complete project lifecycle: create, retrieve, update, and soft archive."""
    admin_headers = auth_headers(Role.ORGANISATION_ADMIN)
    pm_headers = auth_headers(Role.PROJECT_MANAGER)

    # 1. Create project
    create_payload = {
        "name": "Baringo Dryland Sorghum Commercialization",
        "code": "SORGHUM-BAR-26",
        "description": "Drought-tolerant sorghum seed multiplication and value addition.",
        "startDate": "2026-03-01",
        "endDate": "2026-12-31",
        "targetBeneficiaries": 850,
        "budget": 3800000.0,
        "sectors": ["Cereals", "Dryland Agriculture"],
        "donor": "WFP Resilience Grant",
        "locations": [{"county": "Baringo", "subCounty": "Mogotio"}],
    }
    resp = client.post("/api/v1/impactos/projects", json=create_payload, headers=admin_headers)
    assert resp.status_code == 201
    proj_data = resp.json()
    assert proj_data["code"] == "SORGHUM-BAR-26"
    assert proj_data["targetBeneficiaries"] == 850
    assert proj_data["budget"] == 3800000.0
    assert proj_data["status"] == "active"
    proj_id = proj_data["id"]

    # 2. Retrieve by ID
    get_resp = client.get(f"/api/v1/impactos/projects/{proj_id}", headers=pm_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Baringo Dryland Sorghum Commercialization"

    # 3. List and filter by search
    list_resp = client.get("/api/v1/impactos/projects?search=Sorghum", headers=pm_headers)
    assert list_resp.status_code == 200
    assert any(p["id"] == proj_id for p in list_resp.json())

    # 4. Update project
    update_payload = {
        "budget": 4200000.0,
        "targetBeneficiaries": 950,
    }
    put_resp = client.put(f"/api/v1/impactos/projects/{proj_id}", json=update_payload, headers=pm_headers)
    assert put_resp.status_code == 200
    assert put_resp.json()["budget"] == 4200000.0
    assert put_resp.json()["targetBeneficiaries"] == 950

    # 5. Soft archive project
    arch_resp = client.post(f"/api/v1/impactos/projects/{proj_id}/archive", headers=pm_headers)
    assert arch_resp.status_code == 200
    assert arch_resp.json()["project"]["isArchived"] is True
    assert arch_resp.json()["project"]["status"] == "archived"


def test_project_date_validation(client, auth_headers):
    """Verifies that project end date cannot precede start date."""
    headers = auth_headers(Role.ORGANISATION_ADMIN)
    invalid_payload = {
        "name": "Invalid Date Sequence Project",
        "code": "INV-DATE-01",
        "description": "Testing reverse date validation error catching.",
        "startDate": "2026-10-01",
        "endDate": "2026-05-01",  # End is before start!
        "targetBeneficiaries": 100,
        "budget": 500000.0,
    }
    resp = client.post("/api/v1/impactos/projects", json=invalid_payload, headers=headers)
    assert resp.status_code == 400
    assert "cannot be earlier than start date" in resp.json()["detail"].lower()


def test_duplicate_project_code_rejected(client, auth_headers):
    """Verifies that creating duplicate project codes returns 409 Conflict."""
    headers = auth_headers(Role.ORGANISATION_ADMIN)
    payload = {
        "name": "Duplicate Code Test Initiative",
        "code": "SMCRI-2026",  # Pre-existing code in seed data
        "description": "Duplicate code test description.",
        "startDate": "2026-01-01",
        "endDate": "2026-12-31",
        "targetBeneficiaries": 200,
        "budget": 100000.0,
    }
    resp = client.post("/api/v1/impactos/projects", json=payload, headers=headers)
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"].lower()


def test_beneficiary_crud_and_project_linkage(client, auth_headers):
    """Verifies beneficiary registration, project enrollment linkage, and demographics."""
    field_headers = auth_headers(Role.FIELD_OFFICER)
    pm_headers = auth_headers(Role.PROJECT_MANAGER)

    payload = {
        "firstName": "Gladys",
        "lastName": "Cherotich",
        "category": BeneficiaryCategory.WOMEN_COOPERATIVE.value,
        "gender": "female",
        "ageGroup": "youth_18_35",
        "phone": "+254712998877",
        "nationalId": "32456789",
        "projectId": "proj_smcri_2026",
        "supportReceived": ["Certified Maize Seed", "Mulching Workshop"],
    }
    resp = client.post("/api/v1/impactos/beneficiaries", json=payload, headers=field_headers)
    assert resp.status_code == 201
    ben_data = resp.json()
    assert ben_data["firstName"] == "Gladys"
    assert ben_data["gender"] == "female"
    assert len(ben_data["enrolledProjects"]) == 1
    assert ben_data["enrolledProjects"][0]["projectId"] == "proj_smcri_2026"
    ben_id = ben_data["id"]

    # Verify project enrolled count incremented
    proj_resp = client.get("/api/v1/impactos/projects/proj_smcri_2026", headers=pm_headers)
    assert proj_resp.status_code == 200
    assert proj_resp.json()["enrolledBeneficiariesCount"] >= 4

    # Update beneficiary category
    upd_resp = client.put(
        f"/api/v1/impactos/beneficiaries/{ben_id}",
        json={"category": BeneficiaryCategory.YOUTH_AGRIPRENEUR.value},
        headers=pm_headers,
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["category"] == BeneficiaryCategory.YOUTH_AGRIPRENEUR.value


def test_beneficiary_pii_minimization_and_masking(client, auth_headers):
    """
    Minimises personal data collection and verifies that sensitive PII
    (phone, nationalId) is masked for Viewer role and exposed only to authorised roles.
    """
    admin_headers = auth_headers(Role.ORGANISATION_ADMIN)
    viewer_headers = auth_headers(Role.VIEWER)

    # 1. Authorised Admin view
    admin_resp = client.get("/api/v1/impactos/beneficiaries/ben_gv_01", headers=admin_headers)
    assert admin_resp.status_code == 200
    admin_ben = admin_resp.json()
    assert admin_ben["phone"] == "+254722123456"
    assert admin_ben["nationalId"] == "29871120"

    # 2. Viewer view: PII must be masked!
    viewer_resp = client.get("/api/v1/impactos/beneficiaries/ben_gv_01", headers=viewer_headers)
    assert viewer_resp.status_code == 200
    viewer_ben = viewer_resp.json()
    assert "***" in viewer_ben["phone"]
    assert viewer_ben["phone"] != "+254722123456"
    assert "******20" in viewer_ben["nationalId"]

    # 3. List endpoint also applies masking for Viewer
    viewer_list = client.get("/api/v1/impactos/beneficiaries", headers=viewer_headers)
    assert viewer_list.status_code == 200
    for b in viewer_list.json():
        if b.get("phone"):
            assert "***" in b["phone"]
        if b.get("nationalId"):
            assert "*" in b["nationalId"]


def test_indicators_creation_and_measurable_progress_calculation(client, auth_headers):
    """
    Verifies indicator creation, validation, and mathematically sound progress calculation
    without inventing arbitrary results.
    """
    pm_headers = auth_headers(Role.PROJECT_MANAGER)

    # 1. Non-positive target must be rejected
    invalid_target = {
        "projectId": "proj_smcri_2026",
        "name": "Invalid Zero Target Indicator",
        "code": "IND-ZERO-01",
        "description": "Testing zero target rejection.",
        "category": "output",
        "unit": "farmers",
        "baselineValue": 0.0,
        "targetValue": 0.0,  # Invalid
    }
    fail_resp = client.post("/api/v1/impactos/indicators", json=invalid_target, headers=pm_headers)
    assert fail_resp.status_code in [400, 422]

    # 2. Valid indicator creation
    create_payload = {
        "projectId": "proj_smcri_2026",
        "name": "Beneficiary Households with Improved Food Security",
        "code": "IND-HFS-04",
        "description": "Households reporting at least 2 food-secure meals per day during lean season.",
        "category": IndicatorCategory.OUTCOME.value,
        "unit": "households",
        "baselineValue": 100.0,
        "targetValue": 600.0,
        "currentValue": 250.0,
        "reportingFrequency": ReportingFrequency.SEMI_ANNUALLY.value,
    }
    resp = client.post("/api/v1/impactos/indicators", json=create_payload, headers=pm_headers)
    assert resp.status_code == 201
    ind_data = resp.json()
    # Expected progress = ((250 - 100) / (600 - 100)) * 100 = 150 / 500 * 100 = 30.0%
    assert ind_data["progressPercent"] == 30.0
    assert ind_data["status"] == "critical"  # < 40% is critical


def test_indicator_progress_recording_audit_trail(client, auth_headers):
    """Verifies auditable recording of indicator progress updates."""
    fo_headers = auth_headers(Role.FIELD_OFFICER)

    progress_payload = {
        "period": "Q4-2026 Verification",
        "measuredValue": 450.0,
        "measurementDate": "2026-11-01",
        "source": "Sentinel Farm Agronomic Harvest Survey",
        "notes": "Post-harvest threshing confirmed substantial acreage expansion.",
        "isVerified": True,
        "verificationSource": "Sub-County Agricultural Inspectorate",
    }
    resp = client.post("/api/v1/impactos/indicators/ind_smcri_01/progress", json=progress_payload, headers=fo_headers)
    assert resp.status_code == 200
    data = resp.json()

    ind = data["indicator"]
    assert ind["currentValue"] == 450.0
    # Baseline: 0.0, Target: 500.0 -> 450 / 500 * 100 = 90.0%
    assert ind["progressPercent"] == 90.0
    assert ind["status"] == "on_track"
    assert ind["isVerified"] is True
    assert ind["verificationSource"] == "Sub-County Agricultural Inspectorate"

    audit = data["auditLog"]
    assert audit["measuredValue"] == 450.0
    assert audit["source"] == "Sentinel Farm Agronomic Harvest Survey"


def test_activity_tracking_and_attendance_disaggregation(client, auth_headers):
    """Verifies field activity tracking with gender and youth disaggregated attendance."""
    fo_headers = auth_headers(Role.FIELD_OFFICER)

    activity_payload = {
        "projectId": "proj_smcri_2026",
        "title": "Post-Harvest Moisture Meter Calibration Clinic",
        "activityType": "training_workshop",
        "activityDate": "2026-10-28",
        "location": "Visoi Farmers Cooperative Hall, Nakuru",
        "targetAttendance": 75,
        "actualAttendance": 68,
        "femaleAttendance": 41,
        "maleAttendance": 27,
        "youthAttendance": 35,
        "outputs": [
            "68 moisture meters calibrated to 13.5% safe storage standard",
            "Distributed 68 grain storage tarpaulins",
        ],
        "supportingNotes": "Farmers demonstrated proficiency in operating digital handheld moisture probes.",
        "evidenceAttachments": ["https://images.unsplash.com/photo-1592417817098-8f3d6910985c"],
        "status": "completed",
        "isVerified": True,
    }
    resp = client.post("/api/v1/impactos/activities", json=activity_payload, headers=fo_headers)
    assert resp.status_code == 201
    act = resp.json()
    assert act["actualAttendance"] == 68
    assert act["femaleAttendance"] == 41
    assert act["youthAttendance"] == 35
    assert len(act["outputs"]) == 2
    assert act["isVerified"] is True


def test_impactos_dashboard_stats_endpoint(client, auth_headers):
    """Verifies that all M&E dashboard statistics are calculated from actual records."""
    headers = auth_headers(Role.VIEWER)
    resp = client.get("/api/v1/impactos/dashboard/stats", headers=headers)
    assert resp.status_code == 200
    stats = resp.json()

    assert stats["activeProjectsCount"] >= 2
    assert stats["totalBeneficiariesCount"] >= 4
    assert stats["femaleBeneficiariesPercent"] > 0.0
    assert stats["youthBeneficiariesPercent"] > 0.0
    assert stats["totalIndicatorsCount"] >= 4
    assert stats["overallTargetProgressPercent"] > 0.0
    assert "on_track" in stats["indicatorPerformanceBreakdown"]
    assert stats["totalBudget"] > 0.0
    assert len(stats["recentActivities"]) >= 1


def test_report_generation_distinguishes_verified_from_field_observations(client, auth_headers):
    """
    Verifies that generated M&E reports strictly segregate verified results
    from unverified field observations.
    """
    analyst_headers = auth_headers(Role.ANALYST)

    report_payload = {
        "projectId": "proj_smcri_2026",
        "reportingPeriod": "Q3-2026",
        "includeUnverified": True,
    }
    resp = client.post("/api/v1/impactos/reports/generate", json=report_payload, headers=analyst_headers)
    assert resp.status_code == 201
    report = resp.json()

    assert report["projectName"] == "Smallholder Maize Climate Resilience Initiative"
    assert report["reportingPeriod"] == "Q3-2026"
    assert "executiveSummary" in report

    # 1. Check Verified Results (audited)
    verified = report["verifiedResults"]
    assert len(verified) >= 1
    for v in verified:
        assert v["isVerified"] is True

    # 2. Check Field Observations (unverified)
    unverified = report["fieldObservations"]
    assert len(unverified) >= 1
    for u in unverified:
        assert u["isVerified"] is False

    # 3. Demographic stats present
    assert "beneficiaryStats" in report
    assert report["beneficiaryStats"]["totalBeneficiaries"] >= 3

    # 4. Fetch the report back by ID
    rep_id = report["reportId"]
    get_rep = client.get(f"/api/v1/impactos/reports/{rep_id}", headers=analyst_headers)
    assert get_rep.status_code == 200
    assert get_rep.json()["reportId"] == rep_id


def test_report_export_csv_and_html(client, auth_headers):
    """Verifies structured CSV and formatted printable HTML export endpoints."""
    analyst_headers = auth_headers(Role.ANALYST)
    viewer_headers = auth_headers(Role.VIEWER)

    # First generate a report to export
    gen_resp = client.post(
        "/api/v1/impactos/reports/generate",
        json={"projectId": "proj_smcri_2026", "reportingPeriod": "Q3-2026"},
        headers=analyst_headers,
    )
    assert gen_resp.status_code == 201
    report_id = gen_resp.json()["reportId"]

    # 1. Export CSV
    csv_resp = client.get(f"/api/v1/impactos/reports/{report_id}/export/csv", headers=analyst_headers)
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
    csv_text = csv_resp.text
    assert "AGROTRACK AI — IMPACTOS MONITORING & EVALUATION REPORT" in csv_text
    assert "M&E INDICATORS PERFORMANCE" in csv_text
    assert "AUDITED & VERIFIED RESULTS" in csv_text

    # 2. Export Printable HTML
    html_resp = client.get(f"/api/v1/impactos/reports/{report_id}/export/html", headers=viewer_headers)
    assert html_resp.status_code == 200
    assert "text/html" in html_resp.headers["content-type"]
    html_text = html_resp.text
    assert "<title>M&E Report" in html_text
    assert "Executive Performance Summary" in html_text
    assert "Verified Results" in html_text


def test_role_permissions_rbac_enforcement(client, auth_headers):
    """
    Verifies role-based access control:
    - Viewer is read-only (denied 403 on create/edit/delete/archive/generate).
    - Field Officer can enroll beneficiaries and log activities, but cannot create projects or indicators.
    - Analyst can view and generate/export reports, but cannot create projects or enroll beneficiaries.
    - Project Manager and Admin have full management permissions.
    """
    viewer = auth_headers(Role.VIEWER)
    field = auth_headers(Role.FIELD_OFFICER)
    analyst = auth_headers(Role.ANALYST)
    pm = auth_headers(Role.PROJECT_MANAGER)

    # 1. Viewer denied write access
    assert client.post("/api/v1/impactos/projects", json={"name": "X", "code": "X", "description": "X", "startDate": "2026-01-01", "endDate": "2026-12-31", "targetBeneficiaries": 10}, headers=viewer).status_code == 403
    assert client.post("/api/v1/impactos/beneficiaries", json={"firstName": "X", "lastName": "Y"}, headers=viewer).status_code == 403
    assert client.post("/api/v1/impactos/indicators", json={"projectId": "proj_smcri_2026", "name": "X", "code": "X", "description": "X", "targetValue": 10}, headers=viewer).status_code == 403
    assert client.post("/api/v1/impactos/activities", json={"projectId": "proj_smcri_2026", "title": "X", "activityType": "other", "location": "X"}, headers=viewer).status_code == 403
    assert client.post("/api/v1/impactos/reports/generate", json={"reportingPeriod": "Q3"}, headers=viewer).status_code == 403

    # 2. Field Officer denied project creation and indicator creation, but allowed beneficiary and activity creation
    assert client.post("/api/v1/impactos/projects", json={"name": "X", "code": "X", "description": "X", "startDate": "2026-01-01", "endDate": "2026-12-31", "targetBeneficiaries": 10}, headers=field).status_code == 403
    assert client.post("/api/v1/impactos/indicators", json={"projectId": "proj_smcri_2026", "name": "X", "code": "X", "description": "X", "targetValue": 10}, headers=field).status_code == 403
    assert client.post("/api/v1/impactos/reports/generate", json={"reportingPeriod": "Q3"}, headers=field).status_code == 403

    # 3. Analyst denied project creation and beneficiary enrollment, but allowed report generation
    assert client.post("/api/v1/impactos/projects", json={"name": "X", "code": "X", "description": "X", "startDate": "2026-01-01", "endDate": "2026-12-31", "targetBeneficiaries": 10}, headers=analyst).status_code == 403
    assert client.post("/api/v1/impactos/beneficiaries", json={"firstName": "X", "lastName": "Y"}, headers=analyst).status_code == 403


def test_cross_organisation_impactos_isolation(client, auth_headers):
    """Verifies that an organisation cannot access projects, beneficiaries, or indicators of another organisation."""
    greenvalley_user = auth_headers(Role.ORGANISATION_ADMIN)  # belongs to org_greenvalley_01

    # Attempt to access project of org_highland_02
    resp = client.get("/api/v1/impactos/projects/proj_highland_tea_2026", headers=greenvalley_user)
    assert resp.status_code == 404

    # Attempt to access beneficiary of org_highland_02
    resp_ben = client.get("/api/v1/impactos/beneficiaries/ben_hl_01", headers=greenvalley_user)
    assert resp_ben.status_code == 404

    # Attempt to access indicator of org_highland_02
    resp_ind = client.get("/api/v1/impactos/indicators/ind_hl_01", headers=greenvalley_user)
    assert resp_ind.status_code == 404
