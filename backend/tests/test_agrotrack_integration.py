"""
Automated integration tests for AgroTrack AI — AgroFast Core Integration.
Tests:
1. Image quality validation (resolution, sharpness, brightness, blur detection)
2. Crop diagnosis pipeline with spot severity analysis and quality report
3. Farm health score calculation
4. Environmental disease risk prediction
5. Smart irrigation advisory
6. Fertilizer NPK balancing and organic/synthetic recommendations
7. Crop calendar and growth stage progression
8. Crop profitability simulation
9. Multi-tenant Farm CRUD and Role-Based Access Control
10. Cross-organisation data isolation (anti-tamper / boundary check)
11. Expense CRUD and cascading deletion
12. Diagnostic scan history retrieval
"""

import io
import json
import pytest
from PIL import Image, ImageDraw
from backend.models import Role


def _make_test_image(width: int = 224, height: int = 224, color: tuple = (34, 139, 34), with_spots: bool = False) -> bytes:
    """Helper to generate in-memory synthetic images for testing."""
    img = Image.new("RGB", (width, height), color=color)
    draw = ImageDraw.Draw(img)
    # Draw leaf vein patterns for edge definition and sharpness
    for i in range(15, width - 15, 20):
        draw.line([(i, 0), (width - i, height)], fill=(20, 100, 20), width=2)
    if with_spots:
        # Add high-contrast spots representing leaf lesions
        draw.ellipse([50, 50, 80, 80], fill=(139, 69, 19))
        draw.ellipse([120, 100, 160, 140], fill=(160, 82, 45))
        draw.ellipse([70, 150, 100, 180], fill=(101, 67, 33))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


# ── 1. Image Quality Validation Tests ─────────────────────────────────────────

def test_image_quality_check_rejects_low_resolution(client):
    """Low resolution image (< 100x100) must fail quality validation."""
    tiny_img = _make_test_image(width=64, height=64)
    files = {"image": ("tiny.jpg", io.BytesIO(tiny_img), "image/jpeg")}
    resp = client.post("/api/v1/agrotrack/quality-check", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is False
    assert any("resolution" in w.lower() for w in data["warnings"])
    assert data["width"] == 64
    assert data["height"] == 64


def test_image_quality_check_accepts_valid_image(client):
    """Standard image (>= 100x100 with adequate contrast) passes quality validation."""
    good_img = _make_test_image(width=300, height=300, with_spots=True)
    files = {"image": ("leaf.jpg", io.BytesIO(good_img), "image/jpeg")}
    resp = client.post("/api/v1/agrotrack/quality-check", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_valid"] is True
    assert len(data["warnings"]) == 0
    assert data["width"] == 300
    assert data["height"] == 300
    assert "sharpness" in data
    assert "brightness" in data


def test_quality_check_rejects_unsupported_file_type(client):
    """Non-image files must be rejected with 400 Bad Request."""
    fake_doc = io.BytesIO(b"%PDF-1.4 simulated pdf document bytes")
    files = {"image": ("report.pdf", fake_doc, "application/pdf")}
    resp = client.post("/api/v1/agrotrack/quality-check", files=files)
    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]


# ── 2. Crop Diagnosis Pipeline Tests ──────────────────────────────────────────

def test_diagnose_pipeline_returns_full_analysis(client, auth_headers):
    """
    Diagnose endpoint runs quality validation, MobileNetV2 classification,
    PlantCV spot segmentation, severity estimation, and treatment lookup.
    Requires authentication.
    """
    headers = auth_headers(Role.FIELD_OFFICER)
    test_leaf = _make_test_image(width=224, height=224, with_spots=True)
    files = {"image": ("leaf_scan.jpg", io.BytesIO(test_leaf), "image/jpeg")}
    resp = client.post("/api/v1/agrotrack/diagnose", files=files, headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert "crop" in data
    assert "disease" in data
    assert "confidence" in data
    assert "severity_percentage" in data
    assert "severity_level" in data
    assert "boxes" in data
    assert "treatment" in data
    assert "quality_assessment" in data

    assert "treatment" in data
    assert isinstance(data["treatment"], (str, dict))
    assert len(data["treatment"]) > 0


# ── 3. Farm Health Scoring Tests ─────────────────────────────────────────────

def test_farm_health_scoring_unauthenticated_fails(client):
    """Farm health calculation requires an authenticated user."""
    resp = client.get("/api/v1/agrotrack/farms/farm_gv_101/health")
    assert resp.status_code == 401


def test_farm_health_scoring_authenticated(client, auth_headers):
    """Authenticated user receives multi-factor health scoring with recommendations."""
    headers = auth_headers(Role.FIELD_OFFICER)
    resp = client.get("/api/v1/agrotrack/farms/farm_gv_101/health", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "health_score" in data
    assert 0 <= data["health_score"] <= 100
    assert "health_grade" in data
    assert "grade_label" in data
    assert "breakdown" in data
    assert "disease_health" in data["breakdown"]
    assert "soil_fertility" in data["breakdown"]
    assert "irrigation_management" in data["breakdown"]
    assert "action_items" in data
    assert isinstance(data["action_items"], list)


# ── 4. Disease Risk Prediction Tests ─────────────────────────────────────────

def test_disease_risk_prediction_high_risk(client, auth_headers):
    """High temperature and high humidity conditions produce elevated fungal/bacterial risk."""
    headers = auth_headers(Role.VIEWER)
    payload = {
        "crop": "Tomato",
        "temperature": 24.5,
        "humidity": 88.0,
        "precipitation": 12.0
    }
    resp = client.post("/api/v1/agrotrack/disease-risk", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_risk_level"] in ["High Risk", "Moderate Risk"]
    assert data["risk_score"] >= 40
    assert len(data["potential_threats"]) > 0
    assert len(data["preventative_measures"]) > 0


def test_disease_risk_prediction_low_risk(client, auth_headers):
    """Cool, dry conditions yield low fungal risk."""
    headers = auth_headers(Role.VIEWER)
    payload = {
        "crop": "Wheat",
        "temperature": 15.0,
        "humidity": 35.0,
        "precipitation": 0.0
    }
    resp = client.post("/api/v1/agrotrack/disease-risk", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_risk_level"] == "Low Risk"
    assert data["risk_score"] < 40


# ── 5. Irrigation Advisory Tests ─────────────────────────────────────────────

def test_irrigation_advice_rain_hold(client, auth_headers):
    """Heavy recent precipitation triggers a hold on irrigation to prevent waterlogging."""
    headers = auth_headers(Role.FIELD_OFFICER)
    payload = {
        "crop": "Maize",
        "soil_type": "Clay",
        "temperature": 22.0,
        "humidity": 80.0,
        "precipitation_24h": 15.0,
        "irrigation_type": "Drip"
    }
    resp = client.post("/api/v1/agrotrack/irrigation-advice", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "Hold" in data["action"]
    assert data["recommended_volume_mm"] == 0.0


def test_irrigation_advice_dry_heat(client, auth_headers):
    """Hot dry weather calculates positive irrigation quota in mm and optimal window."""
    headers = auth_headers(Role.FIELD_OFFICER)
    payload = {
        "crop": "Tomato",
        "soil_type": "Sandy",
        "temperature": 32.0,
        "humidity": 35.0,
        "precipitation_24h": 0.0,
        "irrigation_type": "Drip"
    }
    resp = client.post("/api/v1/agrotrack/irrigation-advice", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "Increase" in data["action"]
    assert data["recommended_volume_mm"] > 0
    assert "optimal_window" in data


# ── 6. Fertilizer Advisory Tests ─────────────────────────────────────────────

def test_fertilizer_advice_nitrogen_deficit(client, auth_headers):
    """Nitrogen-depleted soil triggers nitrogen deficit recommendation with exact prescriptions."""
    headers = auth_headers(Role.ANALYST)
    payload = {
        "crop": "Maize",
        "n_percent": 18.0,
        "p_percent": 30.0,
        "k_percent": 25.0,
        "ph": 6.4
    }
    resp = client.post("/api/v1/agrotrack/fertilizer-advice", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["crop"] == "Maize"
    assert data["deficits"]["nitrogen_deficit"] > 0
    assert len(data["prescriptions"]) > 0


# ── 7. Crop Calendar & Profitability Tests ────────────────────────────────────

def test_crop_calendar_calculation(client, auth_headers):
    """Crop calendar calculates days elapsed, current stage, and harvest milestone."""
    headers = auth_headers(Role.VIEWER)
    payload = {
        "crop": "Maize",
        "planting_date": "2026-01-15"
    }
    resp = client.post("/api/v1/agrotrack/crop-calendar", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["crop"] == "Maize"
    assert "current_growth_stage" in data
    assert "days_elapsed" in data
    assert "days_to_harvest" in data
    assert "upcoming_milestone" in data


def test_profitability_simulation(client, auth_headers):
    """Calculates yield, revenue, expenses, profit, and return on investment."""
    headers = auth_headers(Role.ANALYST)
    payload = {
        "crop": "Tomato",
        "acreage": 3.0,
        "expected_yield_multiplier": 1.0,
        "market_price_per_kg": 65.0,
        "currency": "KES"
    }
    resp = client.post("/api/v1/agrotrack/profitability-simulation", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["crop"] == "Tomato"
    assert data["acreage"] == 3.0
    assert data["gross_revenue"] > 0
    assert data["total_production_cost"] > 0
    assert data["net_profit"] != 0
    assert "return_on_investment_pct" in data


# ── 8. Multi-Tenant Farm CRUD & RBAC Tests ────────────────────────────────────

def test_farms_list_scoped_to_organisation(client, auth_headers):
    """Listing farms returns only farms belonging to the user's organisation."""
    headers = auth_headers(Role.FIELD_OFFICER)
    resp = client.get("/api/v1/agrotrack/farms", headers=headers)
    assert resp.status_code == 200
    farms = resp.json()
    assert isinstance(farms, list)
    assert len(farms) >= 1
    for farm in farms:
        assert farm["orgId"] == "org_greenvalley_01"


def test_viewer_role_cannot_create_or_delete_farm(client, auth_headers):
    """Viewer role is read-only and must be forbidden from creating or deleting farms."""
    headers = auth_headers(Role.VIEWER)
    new_farm = {
        "name": "Unauthorized Plot",
        "size": 2.0,
        "unit": "acres",
        "crop": "Maize",
        "soil": "Loamy",
        "irrigation": "Rainfed",
        "waterSource": "River",
        "status": "Fallow",
        "budget": 20000.0
    }
    resp = client.post("/api/v1/agrotrack/farms", json=new_farm, headers=headers)
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"].lower()


def test_field_officer_can_create_and_update_farm(client, auth_headers):
    """Field Officer can create and update a farm within their organisation."""
    headers = auth_headers(Role.FIELD_OFFICER)
    new_farm = {
        "name": "East Valley Experimental Plot",
        "size": 4.5,
        "unit": "acres",
        "crop": "Coffee",
        "soil": "Volcanic",
        "irrigation": "Drip",
        "waterSource": "Borehole",
        "status": "Growing",
        "budget": 120000.0,
        "plantingDate": "2026-02-10",
        "soilNutrients": {"n": 52.0, "p": 38.0, "k": 30.0}
    }
    create_resp = client.post("/api/v1/agrotrack/farms", json=new_farm, headers=headers)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["name"] == "East Valley Experimental Plot"
    assert created["orgId"] == "org_greenvalley_01"
    farm_id = created["id"]

    # Update farm
    update_payload = {"budget": 135000.0, "status": "Flowering"}
    update_resp = client.put(f"/api/v1/agrotrack/farms/{farm_id}", json=update_payload, headers=headers)
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["budget"] == 135000.0
    assert updated["status"] == "Flowering"


# ── 9. Cross-Organisation Data Isolation Tests ───────────────────────────────

def test_cross_organisation_farm_access_is_forbidden(client, auth_headers):
    """
    CRITICAL MULTI-TENANCY TEST:
    A user from org_greenvalley_01 MUST NOT be able to read, update, or delete
    a farm belonging to org_highland_02 (e.g. farm_hl_201).
    """
    gv_headers = auth_headers(Role.ORGANISATION_ADMIN)  # Admin in GreenValley

    # 1. Attempt to read farm_hl_201 (Highland Tea Estate in org_highland_02)
    resp = client.get("/api/v1/agrotrack/farms/farm_hl_201", headers=gv_headers)
    assert resp.status_code == 403
    assert "belongs to a different organisation" in resp.json()["detail"]

    # 2. Attempt to update farm_hl_201
    resp = client.put("/api/v1/agrotrack/farms/farm_hl_201", json={"budget": 999999.0}, headers=gv_headers)
    assert resp.status_code == 403
    assert "belongs to a different organisation" in resp.json()["detail"]

    # 3. Attempt to delete farm_hl_201
    resp = client.delete("/api/v1/agrotrack/farms/farm_hl_201", headers=gv_headers)
    assert resp.status_code == 403
    assert "belongs to a different organisation" in resp.json()["detail"]


def test_tenant_user_can_access_own_farm(client):
    """A user authenticating under org_highland_02 CAN access farm_hl_201."""
    highland_user_token = "mock-jwt:" + json.dumps({
        "uid": "usr_hl_10",
        "email": "manager@highland.ai",
        "name": "Highland Manager",
        "role": "Project Manager",
        "orgId": "org_highland_02"
    })
    headers = {"Authorization": f"Bearer {highland_user_token}"}

    resp = client.get("/api/v1/agrotrack/farms/farm_hl_201", headers=headers)
    assert resp.status_code == 200
    farm = resp.json()
    assert farm["id"] == "farm_hl_201"
    assert farm["orgId"] == "org_highland_02"
    assert farm["name"] == "Kericho Highland Tea Estate"


# ── 10. Expenses CRUD and Cascading Delete Tests ──────────────────────────────

def test_expense_crud_and_farm_cascade(client, auth_headers):
    """
    Tests creating an expense, listing expenses, cross-tenant expense prevention,
    and cascading expense deletion when a farm is removed.
    """
    headers = auth_headers(Role.PROJECT_MANAGER)

    # 1. Create a dedicated farm to test expenses
    farm_resp = client.post("/api/v1/agrotrack/farms", json={
        "name": "Expense Cascade Test Field",
        "size": 1.0,
        "crop": "Beans",
        "soil": "Loamy",
        "budget": 30000.0
    }, headers=headers)
    assert farm_resp.status_code == 201
    test_farm_id = farm_resp.json()["id"]

    # 2. Create expense for this farm
    exp_resp = client.post("/api/v1/agrotrack/expenses", json={
        "farmId": test_farm_id,
        "category": "Seeds",
        "amount": 7500.0,
        "note": "Certified bean seeds"
    }, headers=headers)
    assert exp_resp.status_code == 201
    exp_data = exp_resp.json()
    exp_id = exp_data["id"]

    # 3. Verify expense shows up in organisation expense list
    list_resp = client.get("/api/v1/agrotrack/expenses", headers=headers)
    assert list_resp.status_code == 200
    exp_ids = [e["id"] for e in list_resp.json()]
    assert exp_id in exp_ids

    # 4. Attempt to create expense for farm belonging to another organisation -> 403
    cross_exp_resp = client.post("/api/v1/agrotrack/expenses", json={
        "farmId": "farm_hl_201",
        "category": "Fertilizer",
        "amount": 10000.0
    }, headers=headers)
    assert cross_exp_resp.status_code == 403

    # 5. Delete the test farm -> verifies cascading delete
    del_resp = client.delete(f"/api/v1/agrotrack/farms/{test_farm_id}", headers=headers)
    assert del_resp.status_code == 200

    # 6. Verify associated expense was cascade deleted
    after_list_resp = client.get("/api/v1/agrotrack/expenses", headers=headers)
    assert after_list_resp.status_code == 200
    after_exp_ids = [e["id"] for e in after_list_resp.json()]
    assert exp_id not in after_exp_ids


# ── 11. Diagnostic Scan History Tests ─────────────────────────────────────────

def test_scans_history_scoped_to_organisation(client, auth_headers):
    """Scans history returns recent leaf scans for the user's organisation."""
    headers = auth_headers(Role.VIEWER)
    resp = client.get("/api/v1/agrotrack/scans", headers=headers)
    assert resp.status_code == 200
    scans = resp.json()
    assert isinstance(scans, list)
    assert len(scans) >= 1
    for scan in scans:
        assert scan["orgId"] == "org_greenvalley_01"
        assert "crop" in scan
        assert "disease" in scan
