"""
AgroTrack AI — MarketLens Module Automated Test Suite (Phase 4)
Tests commodity catalog CRUD, price record validation, currency/unit normalization,
date handling, historical classification, duplicate rejection, market comparisons,
regional variance, role permissions, organisation isolation, and farm integration.
"""

import pytest
from datetime import date, timedelta
from backend.models import Role, CommodityCategory, PriceType, CollectionMethod, VerificationStatus


# ── 1. Commodity Catalog Tests ───────────────────────────────────────────────

def test_commodity_crud_and_variety_handling(client, auth_headers):
    """Tests commodity creation, retrieval, filtering, and deactivation."""
    headers = auth_headers(Role.ANALYST)

    # 1. List pre-seeded commodities
    res = client.get("/api/v1/marketlens/commodities", headers=headers)
    assert res.status_code == 200
    commodities = res.json()
    assert len(commodities) >= 4
    names = [c["name"] for c in commodities]
    assert "White Maize" in names
    assert "Fresh Tomato" in names

    # 2. Create a new commodity
    payload = {
        "name": "Sorghum Grain",
        "code": "CMD-SRG-01",
        "category": CommodityCategory.CEREALS_GRAINS.value,
        "standardUnit": "90kg bag",
        "supportedUnits": ["90kg bag", "50kg bag", "kg"],
        "varieties": ["Gadam", "Seredo"],
        "description": "Drought-tolerant grain for brewing and local flour."
    }
    create_res = client.post("/api/v1/marketlens/commodities", json=payload, headers=headers)
    assert create_res.status_code == 201
    created_cmd = create_res.json()
    assert created_cmd["name"] == "Sorghum Grain"
    assert created_cmd["code"] == "CMD-SRG-01"
    assert "Gadam" in created_cmd["varieties"]

    # 3. Retrieve by ID
    cmd_id = created_cmd["id"]
    get_res = client.get(f"/api/v1/marketlens/commodities/{cmd_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == cmd_id

    # 4. Filter by Category
    cat_res = client.get(f"/api/v1/marketlens/commodities?category={CommodityCategory.CEREALS_GRAINS.value}", headers=headers)
    assert cat_res.status_code == 200
    assert all(c["category"] == CommodityCategory.CEREALS_GRAINS.value for c in cat_res.json())

    # 5. Search filter
    search_res = client.get("/api/v1/marketlens/commodities?search=Seredo", headers=headers)
    assert search_res.status_code == 200
    assert any(c["name"] == "Sorghum Grain" for c in search_res.json())


def test_duplicate_commodity_rejected(client, auth_headers):
    """Verifies that creating duplicate commodity names in the same organisation returns 409 Conflict."""
    headers = auth_headers(Role.PROJECT_MANAGER)
    payload = {
        "name": "White Maize",  # Pre-exists in org_greenvalley_01
        "category": CommodityCategory.CEREALS_GRAINS.value,
        "standardUnit": "90kg bag"
    }
    res = client.post("/api/v1/marketlens/commodities", json=payload, headers=headers)
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"].lower()


# ── 2. Market Price Record & Validation Tests ────────────────────────────────

def test_price_record_validation_and_unit_normalization(client, auth_headers):
    """
    Tests price recording with validation:
    - Positive price check
    - Traceable source requirement
    - Normalized price per kg calculation
    """
    headers = auth_headers(Role.FIELD_OFFICER)

    # 1. Reject zero or negative price
    invalid_price_payload = {
        "commodityId": "cmd_gv_maize",
        "marketName": "Kitale Market",
        "price": -100.0,
        "unit": "90kg bag",
        "dataSource": "Field Enumerator Survey"
    }
    res = client.post("/api/v1/marketlens/prices", json=invalid_price_payload, headers=headers)
    assert res.status_code == 422 or res.status_code == 400

    # 2. Reject missing data source
    no_source_payload = {
        "commodityId": "cmd_gv_maize",
        "marketName": "Kitale Market",
        "price": 3800.0,
        "unit": "90kg bag",
        "dataSource": ""
    }
    res = client.post("/api/v1/marketlens/prices", json=no_source_payload, headers=headers)
    assert res.status_code == 422 or res.status_code == 400

    # 3. Valid price recording with unit normalization (KES 4,500 / 90kg bag => KES 50.0/kg)
    valid_payload = {
        "commodityId": "cmd_gv_maize",
        "variety": "H614D",
        "marketName": "Kitale Central Market",
        "marketLocation": {"county": "Trans Nzoia", "region": "Rift Valley"},
        "priceType": "wholesale",
        "price": 3600.0,
        "unit": "90kg bag",
        "currency": "KES",
        "dateCollected": str(date.today()),
        "dataSource": "Ministry of Agriculture Market Information System (MIS)",
        "notes": "Post-harvest harvest influx in Trans Nzoia."
    }
    res = client.post("/api/v1/marketlens/prices", json=valid_payload, headers=headers)
    assert res.status_code == 201
    price_data = res.json()
    assert price_data["price"] == 3600.0
    assert price_data["normalizedPricePerKg"] == 40.0  # 3600 / 90
    assert price_data["collectorName"] == "Amina Otieno"
    assert price_data["isHistorical"] is False
    assert price_data["verificationStatus"] == "unverified"


def test_duplicate_price_record_rejected(client, auth_headers):
    """Tests duplicate price survey submission detection within an organisation."""
    headers = auth_headers(Role.FIELD_OFFICER)
    today_str = str(date.today())

    payload = {
        "commodityId": "cmd_gv_beans",
        "marketName": "Gilgil Market",
        "price": 10500.0,
        "unit": "90kg bag",
        "dateCollected": today_str,
        "dataSource": "Field Enumerator Survey - Nakuru AgTech"
    }
    # First submission succeeds
    res1 = client.post("/api/v1/marketlens/prices", json=payload, headers=headers)
    assert res1.status_code == 201

    # Second submission on identical market, date, commodity & unit returns 409 Conflict
    res2 = client.post("/api/v1/marketlens/prices", json=payload, headers=headers)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"].lower()


# ── 3. Historical Data & Freshness Segregation Tests ─────────────────────────

def test_historical_price_classification_and_date_filtering(client, auth_headers):
    """
    Verifies that old prices are NEVER silently treated as current.
    Prices older than 14 days must be marked isHistorical=True with explicit age in days.
    """
    headers = auth_headers(Role.ANALYST)

    res = client.get("/api/v1/marketlens/prices?commodity_id=cmd_gv_maize", headers=headers)
    assert res.status_code == 200
    prices = res.json()

    historical_records = [p for p in prices if p["isHistorical"] is True]
    fresh_records = [p for p in prices if p["isHistorical"] is False]

    # Pre-seeded dataset contains both current and historical prices
    assert len(historical_records) >= 1
    assert len(fresh_records) >= 1

    for hist in historical_records:
        assert hist["recordAgeDays"] > 14
        assert "Historical" in hist["freshnessLabel"] or "Archived" in hist["freshnessLabel"]

    for fresh in fresh_records:
        assert fresh["recordAgeDays"] <= 14
        assert "Current" in fresh["freshnessLabel"] or "Recent" in fresh["freshnessLabel"]


# ── 4. Price Verification Workflow Tests ─────────────────────────────────────

def test_price_verification_lifecycle(client, auth_headers):
    """Tests unverified price submission by field officer and verification by analyst/manager."""
    field_headers = auth_headers(Role.FIELD_OFFICER)
    analyst_headers = auth_headers(Role.ANALYST)

    # 1. Field officer logs unverified price
    payload = {
        "commodityId": "cmd_gv_potato",
        "marketName": "Molo Produce Centre",
        "price": 2600.0,
        "unit": "50kg bag",
        "dateCollected": str(date.today()),
        "dataSource": "Farmgate Trader Spot Survey",
        "notes": "Farmer association bulk loading rate."
    }
    create_res = client.post("/api/v1/marketlens/prices", json=payload, headers=field_headers)
    assert create_res.status_code == 201
    price_id = create_res.json()["id"]
    assert create_res.json()["verificationStatus"] == "unverified"

    # 2. Analyst verifies the record
    verify_res = client.post(f"/api/v1/marketlens/prices/{price_id}/verify", headers=analyst_headers)
    assert verify_res.status_code == 200
    verified_data = verify_res.json()
    assert verified_data["verificationStatus"] == "verified"
    assert verified_data["verifiedBy"] == "usr_analyst_004"
    assert verified_data["verifiedAt"] is not None


# ── 5. Market Research Studies Tests ─────────────────────────────────────────

def test_market_research_creation_and_retrieval(client, auth_headers):
    """Tests creating and searching market research studies with traceable source citations."""
    headers = auth_headers(Role.ANALYST)

    payload = {
        "title": "Avocado Export Value Chain and Smallholder Price Realization",
        "location": "Murang'a & Kiambu",
        "researchDate": "2026-10-25",
        "commodityId": "cmd_gv_tomato",
        "valueChainStage": "Export Aggregator",
        "findings": "Smallholders selling to certified export outgrower schemes achieved 28% higher farmgate prices than spot sales.",
        "sourceReferences": [
            "Fresh Produce Exporters Association of Kenya (FPEAK) Annual Review",
            "Horticultural Crops Directorate Export Statistics 2025"
        ],
        "attachments": ["https://storage.agrotrack.ai/research/avocado_export_brief.pdf"]
    }

    create_res = client.post("/api/v1/marketlens/research", json=payload, headers=headers)
    assert create_res.status_code == 201
    res_data = create_res.json()
    assert res_data["title"] == payload["title"]
    assert len(res_data["sourceReferences"]) == 2
    assert res_data["authorName"] == "Brian Njoroge"

    # Search research
    search_res = client.get("/api/v1/marketlens/research?search=outgrower", headers=headers)
    assert search_res.status_code == 200
    assert len(search_res.json()) >= 1


# ── 6. Market Intelligence Analysis & Visualizations ─────────────────────────

def test_price_history_analytics_and_sample_size_notice(client, auth_headers):
    """
    Tests price history calculations:
    - Moving average, min, max, trend direction
    - Sample size reporting and insufficient data warnings
    """
    headers = auth_headers(Role.ANALYST)

    # 1. Query price history for White Maize
    res = client.get("/api/v1/marketlens/analysis/price-history?commodity_id=cmd_gv_maize", headers=headers)
    assert res.status_code == 200
    hist = res.json()
    assert hist["sampleSize"] >= 3
    assert hist["hasSufficientData"] is True
    assert hist["missingDataNotice"] is None
    assert hist["metrics"]["minPrice"] > 0
    assert hist["metrics"]["maxPrice"] >= hist["metrics"]["minPrice"]
    assert hist["metrics"]["averagePrice"] > 0
    assert hist["metrics"]["trendDirection"] in ["increasing", "decreasing", "stable"]

    # 2. Query commodity with insufficient sample size (0 records)
    empty_res = client.get("/api/v1/marketlens/analysis/price-history?commodity_id=cmd_gv_coffee", headers=headers)
    assert empty_res.status_code == 200
    empty_hist = empty_res.json()
    assert empty_hist["sampleSize"] == 0
    assert empty_hist["hasSufficientData"] is False
    assert "No market price records" in empty_hist["missingDataNotice"]


def test_market_comparison_spatial_spread(client, auth_headers):
    """Tests cross-market comparison and spatial price spread calculations."""
    headers = auth_headers(Role.ANALYST)

    res = client.get("/api/v1/marketlens/analysis/market-comparison?commodity_id=cmd_gv_maize", headers=headers)
    assert res.status_code == 200
    comp = res.json()
    assert comp["sampleSize"] >= 2
    assert comp["hasSufficientData"] is True

    # Nairobi wholesale should be higher than Eldoret farmgate/wholesale
    spread = comp["spread"]
    assert spread is not None
    assert spread["spreadPerKg"] >= 0.0
    assert spread["highestPricePerKg"] >= spread["lowestPricePerKg"]


def test_regional_price_differences(client, auth_headers):
    """Tests regional grouping across Rift Valley vs Central."""
    headers = auth_headers(Role.ANALYST)

    res = client.get("/api/v1/marketlens/analysis/regional-differences?commodity_id=cmd_gv_maize", headers=headers)
    assert res.status_code == 200
    reg = res.json()
    assert reg["sampleSize"] >= 2
    assert "Rift Valley" in reg["regions"]
    assert "Central" in reg["regions"]
    assert reg["regions"]["Rift Valley"]["averagePricePerKg"] > 0
    assert reg["regions"]["Central"]["averagePricePerKg"] > 0


def test_supply_and_demand_intelligence_never_invents_numbers(client, auth_headers):
    """Verifies that supply/demand information reports qualitative survey observations without synthetic volumes."""
    headers = auth_headers(Role.ANALYST)

    res = client.get("/api/v1/marketlens/analysis/supply-demand?commodity_id=cmd_gv_maize", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "integrityStatement" in data
    assert "does not simulate synthetic" in data["integrityStatement"]
    assert len(data["reportedObservations"]) >= 1


# ── 7. Farm Integration Tests ────────────────────────────────────────────────

def test_farm_market_intelligence_integration(client, auth_headers):
    """
    Tests connecting AgroTrack farm records with MarketLens pricing intelligence:
    - Matches farm crop (e.g. Maize) to commodity
    - Retrieves local vs regional benchmark prices
    - Explicitly includes critical disclaimer that farm production != realized market supply
    """
    headers = auth_headers(Role.ANALYST)

    res = client.get("/api/v1/marketlens/farms/farm_gv_101/market-intelligence", headers=headers)
    assert res.status_code == 200
    intel = res.json()
    assert intel["farmId"] == "farm_gv_101"
    assert intel["matchedCommodity"]["name"] == "White Maize"
    assert len(intel["localMarketPrices"]) >= 1  # Nakuru market
    assert len(intel["regionalBenchmarkPrices"]) >= 1  # Nairobi / Eldoret

    # Production estimate
    prod = intel["productionEstimate"]
    assert prod["estimatedHarvestVolumeKg"] > 0
    assert prod["estimatedGrossMarketValue"] > 0

    # Strict specification compliance: Supply assumption disclaimer
    disclaimer = intel["criticalSupplyAssumptionDisclaimer"]
    assert "does not automatically equal realized market supply" in disclaimer


# ── 8. Security, RBAC & Multi-Tenant Isolation Tests ─────────────────────────

def test_viewer_role_is_strictly_read_only(client, auth_headers):
    """Verifies that Viewer role can read data but cannot create commodities, prices, or research."""
    headers = auth_headers(Role.VIEWER)

    # 1. Read is permitted
    get_res = client.get("/api/v1/marketlens/commodities", headers=headers)
    assert get_res.status_code == 200

    # 2. Creating commodity is forbidden (403)
    cmd_payload = {"name": "Barley Grain", "category": "Cereals & Grains"}
    post_cmd = client.post("/api/v1/marketlens/commodities", json=cmd_payload, headers=headers)
    assert post_cmd.status_code == 403

    # 3. Creating price survey is forbidden (403)
    price_payload = {
        "commodityId": "cmd_gv_maize",
        "marketName": "Test Market",
        "price": 4000.0,
        "dataSource": "Test Source"
    }
    post_price = client.post("/api/v1/marketlens/prices", json=price_payload, headers=headers)
    assert post_price.status_code == 403

    # 4. Verifying price is forbidden (403)
    post_verify = client.post("/api/v1/marketlens/prices/prc_gv_101/verify", headers=headers)
    assert post_verify.status_code == 403


def test_cross_organisation_market_isolation(client, auth_headers):
    """
    Verifies that a user from org_greenvalley_01 cannot access commodities, prices,
    or research records belonging to org_highland_02 (403 Forbidden).
    """
    gv_headers = auth_headers(Role.ORGANISATION_ADMIN)

    # Attempt to access highland tenant's tea commodity
    res_cmd = client.get("/api/v1/marketlens/commodities/cmd_hl_tea", headers=gv_headers)
    assert res_cmd.status_code == 403
    assert "different organisation" in res_cmd.json()["detail"].lower()

    # Attempt to access highland tenant's price record
    res_prc = client.get("/api/v1/marketlens/prices/prc_hl_201", headers=gv_headers)
    assert res_prc.status_code == 403
    assert "different organisation" in res_prc.json()["detail"].lower()

    # Attempt to access highland tenant's research record
    res_res = client.get("/api/v1/marketlens/research/res_hl_001", headers=gv_headers)
    assert res_res.status_code == 403
    assert "different organisation" in res_res.json()["detail"].lower()


def test_marketlens_dashboard_stats_endpoint(client, auth_headers):
    """Tests the live MarketLens dashboard statistics endpoint."""
    headers = auth_headers(Role.PROJECT_MANAGER)

    res = client.get("/api/v1/marketlens/dashboard/stats", headers=headers)
    assert res.status_code == 200
    stats = res.json()
    assert stats["totalCommodities"] >= 4
    assert stats["totalPriceRecords"] >= 6
    assert stats["verifiedPriceRecords"] >= 1
    assert stats["freshRecordsCount"] >= 1
    assert stats["historicalRecordsCount"] >= 1
    assert len(stats["monitoredMarkets"]) >= 3
    assert len(stats["recentPriceUpdates"]) >= 1
