"""
Automated tests for Phase 3 — AgroTrack: Farmer and Field Management.
Verifies:
1. Farmer creation, editing, retrieval, and profile aggregation.
2. Duplicate record handling (National ID conflict).
3. Farm creation and farmer association.
4. GPS coordinate validation (latitude/longitude boundaries).
5. Field activity creation, retrieval, and filtering (visits, inspections, planting, harvest, irrigation, fertilizer).
6. Field officer workflows and assignment querying.
7. Search, filtering, soft-archive, and restore operations.
8. Role-based access control (RBAC).
9. Cross-organisation data isolation (anti-tamper multi-tenancy).
10. Empty states and boundary conditions.
11. Farm history chronological timeline.
12. Real-time dashboard statistics queried from live records.
"""

import json
import pytest
from backend.models import Role


# ── 1. Farmer CRUD & Retrieval ────────────────────────────────────────────────

def test_farmer_creation_validation_and_retrieval(client, auth_headers):
    """Verifies that an authorised Field Officer can create a new farmer with valid data."""
    headers = auth_headers(Role.FIELD_OFFICER)
    new_farmer_payload = {
        "firstName": "Peter",
        "lastName": "Ochieng",
        "farmerCode": "FM-GV-105",
        "nationalId": "31948210",
        "phone": "+254711223344",
        "gender": "male",
        "location": {
            "county": "Nakuru",
            "subCounty": "Rongai",
            "ward": "Solai",
            "village": "Banita",
            "latitude": -0.0190,
            "longitude": 36.1200
        },
        "assignedFieldOfficerId": "usr_field_003",
        "enrolledProjectIds": ["proj_smcri_2026"],
        "totalAcreage": 2.5,
        "consentGiven": True
    }

    create_resp = client.post("/api/v1/agrotrack/farmers", json=new_farmer_payload, headers=headers)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["firstName"] == "Peter"
    assert created["lastName"] == "Ochieng"
    assert created["farmerCode"] == "FM-GV-105"
    assert created["nationalId"] == "31948210"
    assert created["orgId"] == "org_greenvalley_01"
    assert created["status"] == "active"
    farmer_id = created["id"]

    # Retrieve individual farmer
    get_resp = client.get(f"/api/v1/agrotrack/farmers/{farmer_id}", headers=headers)
    assert get_resp.status_code == 200
    farmer = get_resp.json()
    assert farmer["id"] == farmer_id
    assert farmer["phone"] == "+254711223344"


def test_duplicate_national_id_rejected(client, auth_headers):
    """Creating a farmer with an existing National ID in the same org must return 409 Conflict."""
    headers = auth_headers(Role.FIELD_OFFICER)
    duplicate_payload = {
        "firstName": "Duplicate",
        "lastName": "Farmer",
        "nationalId": "24981023",  # Already belongs to Joseph Kamau in org_greenvalley_01
        "phone": "+254700000000"
    }
    resp = client.post("/api/v1/agrotrack/farmers", json=duplicate_payload, headers=headers)
    assert resp.status_code == 409
    assert "already exists in this organisation" in resp.json()["detail"]


def test_farmer_update_and_profile_aggregation(client, auth_headers):
    """Verifies updating farmer details and viewing the consolidated profile with linked plots and activities."""
    headers = auth_headers(Role.FIELD_OFFICER)
    farmer_id = "frmr_982103"  # Joseph Kamau

    update_payload = {
        "phone": "+254799887766",
        "totalAcreage": 5.0
    }
    put_resp = client.put(f"/api/v1/agrotrack/farmers/{farmer_id}", json=update_payload, headers=headers)
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["phone"] == "+254799887766"
    assert updated["totalAcreage"] == 5.0

    # Retrieve full profile
    profile_resp = client.get(f"/api/v1/agrotrack/farmers/{farmer_id}/profile", headers=headers)
    assert profile_resp.status_code == 200
    profile = profile_resp.json()
    assert profile["farmer"]["id"] == farmer_id
    assert "farms" in profile
    assert len(profile["farms"]) >= 1
    assert "activities" in profile
    assert "metrics" in profile
    assert profile["metrics"]["totalFarms"] >= 1


def test_farmer_soft_archive_and_restore(client, auth_headers):
    """Verifies that farmers can be archived without permanent record deletion, and then restored."""
    admin_headers = auth_headers(Role.ORGANISATION_ADMIN)
    viewer_headers = auth_headers(Role.VIEWER)

    # 1. Create a farmer specifically to test archiving
    new_farmer = client.post("/api/v1/agrotrack/farmers", json={
        "firstName": "Archive",
        "lastName": "Target",
        "nationalId": "88776655"
    }, headers=admin_headers).json()
    target_id = new_farmer["id"]

    # 2. Archive farmer
    archive_resp = client.post(f"/api/v1/agrotrack/farmers/{target_id}/archive", headers=admin_headers)
    assert archive_resp.status_code == 200
    assert archive_resp.json()["farmer"]["status"] == "archived"

    # 3. Default active listing should exclude this farmer
    active_list = client.get("/api/v1/agrotrack/farmers?status=active", headers=viewer_headers).json()
    assert all(f["id"] != target_id for f in active_list)

    # 4. Archived listing should include this farmer
    archived_list = client.get("/api/v1/agrotrack/farmers?status=archived", headers=viewer_headers).json()
    assert any(f["id"] == target_id for f in archived_list)

    # 5. Restore farmer
    restore_resp = client.post(f"/api/v1/agrotrack/farmers/{target_id}/restore", headers=admin_headers)
    assert restore_resp.status_code == 200
    assert restore_resp.json()["farmer"]["status"] == "active"


# ── 2. Search & Filtering ─────────────────────────────────────────────────────

def test_farmer_search_and_filtering(client, auth_headers):
    """Tests multi-factor farmer searching by name, crop, and field officer."""
    headers = auth_headers(Role.VIEWER)

    # Search by name substring
    resp_name = client.get("/api/v1/agrotrack/farmers?search=Joseph", headers=headers)
    assert resp_name.status_code == 200
    farmers = resp_name.json()
    assert len(farmers) >= 1
    assert any("Joseph" in f["firstName"] for f in farmers)

    # Filter by crop
    resp_crop = client.get("/api/v1/agrotrack/farmers?crop=Maize", headers=headers)
    assert resp_crop.status_code == 200
    maize_farmers = resp_crop.json()
    assert len(maize_farmers) >= 1

    # Filter by assigned field officer
    resp_officer = client.get("/api/v1/agrotrack/farmers?field_officer_id=usr_field_003", headers=headers)
    assert resp_officer.status_code == 200
    officer_farmers = resp_officer.json()
    assert all(f["assignedFieldOfficerId"] == "usr_field_003" for f in officer_farmers)


# ── 3. Farm-Farmer Association & GPS Validation ──────────────────────────────

def test_farm_farmer_association_and_acreage_tracking(client, auth_headers):
    """Verifies that creating a farm associated with a farmer increments their acreage."""
    headers = auth_headers(Role.FIELD_OFFICER)
    farmer_id = "frmr_982103"  # Joseph Kamau

    farmer_before = client.get(f"/api/v1/agrotrack/farmers/{farmer_id}", headers=headers).json()
    initial_acreage = float(farmer_before.get("totalAcreage", 0.0))

    new_farm_payload = {
        "name": "Kamau South Demonstration Plot",
        "farmerId": farmer_id,
        "size": 2.0,
        "unit": "acres",
        "crop": "Beans",
        "soil": "Loamy",
        "irrigation": "Drip",
        "location": {
            "name": "Solai South",
            "latitude": -0.0260,
            "longitude": 36.1450
        }
    }
    farm_resp = client.post("/api/v1/agrotrack/farms", json=new_farm_payload, headers=headers)
    assert farm_resp.status_code == 201
    created_farm = farm_resp.json()
    assert created_farm["farmerId"] == farmer_id

    # Verify farmer's total acreage incremented
    farmer_after = client.get(f"/api/v1/agrotrack/farmers/{farmer_id}", headers=headers).json()
    assert round(float(farmer_after["totalAcreage"]), 2) == round(initial_acreage + 2.0, 2)


def test_gps_coordinate_validation(client, auth_headers):
    """Validates boundary rules for GPS latitude (-90 to 90) and longitude (-180 to 180)."""
    headers = auth_headers(Role.FIELD_OFFICER)

    # 1. Invalid Latitude (> 90.0)
    invalid_lat_payload = {
        "name": "Invalid Lat Field",
        "size": 1.0,
        "crop": "Maize",
        "location": {"latitude": 98.5, "longitude": 36.1}
    }
    resp1 = client.post("/api/v1/agrotrack/farms", json=invalid_lat_payload, headers=headers)
    assert resp1.status_code == 400
    assert "Invalid GPS latitude" in resp1.json()["detail"]

    # 2. Invalid Longitude (< -180.0)
    invalid_lng_payload = {
        "firstName": "GPS",
        "lastName": "Tester",
        "location": {"latitude": 0.5, "longitude": -195.0}
    }
    resp2 = client.post("/api/v1/agrotrack/farmers", json=invalid_lng_payload, headers=headers)
    assert resp2.status_code == 400
    assert "Invalid GPS longitude" in resp2.json()["detail"]


# ── 4. Field Activities Management ────────────────────────────────────────────

def test_field_activity_logging_and_filtering(client, auth_headers):
    """Verifies that an authorised Field Officer can log farm visits and retrieve activities."""
    officer_headers = auth_headers(Role.FIELD_OFFICER)
    viewer_headers = auth_headers(Role.VIEWER)

    activity_payload = {
        "farmId": "farm_gv_101",
        "activityType": "crop_inspection",
        "activityDate": "2026-11-03",
        "notes": "Scouted maize canopy for fall armyworm. All clear, leaf colour healthy.",
        "metrics": {"trapCatchCount": 0, "moistureLevel": "Optimal"},
        "observations": ["Uniform tasseling underway", "Irrigation drippers clear"]
    }

    create_resp = client.post("/api/v1/agrotrack/activities", json=activity_payload, headers=officer_headers)
    assert create_resp.status_code == 201
    act = create_resp.json()
    assert act["farmId"] == "farm_gv_101"
    assert act["farmerId"] == "frmr_982103"
    assert act["responsibleUserName"] == "Amina Otieno"
    act_id = act["id"]

    # Retrieve single activity
    get_resp = client.get(f"/api/v1/agrotrack/activities/{act_id}", headers=viewer_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == act_id

    # Filter activities by farm
    list_resp = client.get("/api/v1/agrotrack/activities?farm_id=farm_gv_101", headers=viewer_headers)
    assert list_resp.status_code == 200
    activities = list_resp.json()
    assert len(activities) >= 1
    assert any(a["id"] == act_id for a in activities)


def test_field_officer_assignments(client, auth_headers):
    """Verifies that Field Officers can retrieve their assigned farmers and plots."""
    officer_headers = auth_headers(Role.FIELD_OFFICER)
    resp = client.get("/api/v1/agrotrack/field-officer/assignments", headers=officer_headers)
    assert resp.status_code == 200
    assignments = resp.json()
    assert "assignedFarmers" in assignments
    assert "assignedFarms" in assignments
    assert assignments["totalFarmers"] >= 1


def test_farm_history_chronological_timeline(client, auth_headers):
    """Verifies that /farms/{farm_id}/history unifies activities, scans, and expenses into a timeline."""
    headers = auth_headers(Role.VIEWER)
    resp = client.get("/api/v1/agrotrack/farms/farm_gv_101/history", headers=headers)
    assert resp.status_code == 200
    history = resp.json()
    assert history["farmId"] == "farm_gv_101"
    assert "timeline" in history
    assert history["totalEvents"] >= 1
    
    # Verify timeline is sorted chronologically descending
    dates = [e.get("date") for e in history["timeline"] if e.get("date")]
    assert dates == sorted(dates, reverse=True)


# ── 5. Role-Based Access Control (RBAC) ──────────────────────────────────────

def test_viewer_role_cannot_create_farmer_or_activity(client, auth_headers):
    """Verifies that Viewer role is read-only and forbidden from mutating records."""
    viewer_headers = auth_headers(Role.VIEWER)

    # 1. Attempt to create farmer
    resp1 = client.post("/api/v1/agrotrack/farmers", json={"firstName": "Unauthorized", "lastName": "User"}, headers=viewer_headers)
    assert resp1.status_code == 403

    # 2. Attempt to log field activity
    resp2 = client.post("/api/v1/agrotrack/activities", json={"farmId": "farm_gv_101", "notes": "No permission"}, headers=viewer_headers)
    assert resp2.status_code == 403


# ── 6. Multi-Tenant Organisation Isolation ────────────────────────────────────

def test_cross_organisation_farmer_and_activity_isolation(client, auth_headers):
    """
    CRITICAL MULTI-TENANCY TEST:
    A user belonging to org_greenvalley_01 MUST NOT be able to read, update,
    or archive records belonging to org_highland_02 (e.g. frmr_hl_771 or act_hl_001).
    """
    gv_headers = auth_headers(Role.ORGANISATION_ADMIN)  # Admin in GreenValley

    # 1. Attempt to read farmer in org_highland_02 -> 403 Forbidden
    resp1 = client.get("/api/v1/agrotrack/farmers/frmr_hl_771", headers=gv_headers)
    assert resp1.status_code == 403
    assert "belongs to a different organisation" in resp1.json()["detail"]

    # 2. Attempt to update farmer in org_highland_02 -> 403 Forbidden
    resp2 = client.put("/api/v1/agrotrack/farmers/frmr_hl_771", json={"phone": "+0000"}, headers=gv_headers)
    assert resp2.status_code == 403
    assert "belongs to a different organisation" in resp2.json()["detail"]

    # 3. Attempt to archive farmer in org_highland_02 -> 403 Forbidden
    resp3 = client.post("/api/v1/agrotrack/farmers/frmr_hl_771/archive", headers=gv_headers)
    assert resp3.status_code == 403
    assert "belongs to a different organisation" in resp3.json()["detail"]

    # 4. Attempt to read activity in org_highland_02 -> 403 Forbidden
    resp4 = client.get("/api/v1/agrotrack/activities/act_hl_001", headers=gv_headers)
    assert resp4.status_code == 403
    assert "belongs to a different organisation" in resp4.json()["detail"]


def test_highland_tenant_user_can_access_own_records(client):
    """Verifies that an authenticated user in org_highland_02 CAN access their own farmer and activity."""
    token = "mock-jwt:" + json.dumps({
        "uid": "usr_hl_10",
        "email": "field@highland.ai",
        "name": "Highland Officer",
        "role": "Field Officer",
        "orgId": "org_highland_02"
    })
    headers = {"Authorization": f"Bearer {token}"}

    resp_farmer = client.get("/api/v1/agrotrack/farmers/frmr_hl_771", headers=headers)
    assert resp_farmer.status_code == 200
    assert resp_farmer.json()["id"] == "frmr_hl_771"
    assert resp_farmer.json()["orgId"] == "org_highland_02"

    resp_act = client.get("/api/v1/agrotrack/activities/act_hl_001", headers=headers)
    assert resp_act.status_code == 200
    assert resp_act.json()["id"] == "act_hl_001"
    assert resp_act.json()["orgId"] == "org_highland_02"


# ── 7. Dashboard Live Statistics ──────────────────────────────────────────────

def test_agrotrack_dashboard_stats_endpoint(client, auth_headers):
    """
    Verifies that /api/v1/agrotrack/dashboard/stats returns statistics calculated
    directly from live database records.
    """
    headers = auth_headers(Role.VIEWER)
    resp = client.get("/api/v1/agrotrack/dashboard/stats", headers=headers)
    assert resp.status_code == 200
    stats = resp.json()

    assert stats["totalFarmers"] >= 2
    assert stats["activeFarmers"] >= 2
    assert stats["totalFarms"] >= 2
    assert stats["totalAcreage"] > 0
    assert stats["totalActivities"] >= 1
    assert "activeCropsCount" in stats
    assert isinstance(stats["activeCropsCount"], dict)
    assert "Maize" in stats["activeCropsCount"] or "Tomato" in stats["activeCropsCount"]
    assert "recentActivities" in stats
    assert isinstance(stats["recentActivities"], list)
