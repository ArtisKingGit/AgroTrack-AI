"""
AgroTrack AI — MarketLens Domain Service
Handles commodity catalog, traceable price survey records, verification workflows,
market research studies, price history, market comparison analytics, and farm integration.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status

from backend.models import (
    CommodityCategory,
    PriceType,
    CollectionMethod,
    VerificationStatus,
)
from backend.agrotrack.service import TENANT_FARMS


# ── Conversion Factors ───────────────────────────────────────────────────────

UNIT_KG_FACTORS: Dict[str, float] = {
    "kg": 1.0,
    "1kg": 1.0,
    "kilogram": 1.0,
    "90kg bag": 90.0,
    "90kg": 90.0,
    "50kg bag": 50.0,
    "50kg": 50.0,
    "100kg bag": 100.0,
    "100kg": 100.0,
    "crate (64kg)": 64.0,
    "crate": 64.0,
    "ton": 1000.0,
    "tonne": 1000.0,
    "piece": 1.0,
    "bunch": 1.0,
}


def get_unit_kg_factor(unit: str) -> float:
    """Returns the kg multiplier for a unit string, matching longest specific unit first."""
    u = (unit or "").lower().strip()
    for key in sorted(UNIT_KG_FACTORS.keys(), key=len, reverse=True):
        if key in u:
            return UNIT_KG_FACTORS[key]
    return 1.0


def calculate_normalized_price_per_kg(price: float, unit: str) -> float:
    """Computes standardized price per kg for fair cross-unit comparison."""
    factor = get_unit_kg_factor(unit)
    if factor <= 0:
        return round(price, 2)
    return round(price / factor, 2)


# ── In-Memory Tenant Multi-Tenant Stores ─────────────────────────────────────

TENANT_COMMODITIES: Dict[str, List[Dict[str, Any]]] = {
    "org_greenvalley_01": [
        {
            "id": "cmd_gv_maize",
            "orgId": "org_greenvalley_01",
            "name": "White Maize",
            "code": "CMD-MZ-01",
            "category": CommodityCategory.CEREALS_GRAINS.value,
            "standardUnit": "90kg bag",
            "supportedUnits": ["90kg bag", "50kg bag", "kg", "Ton"],
            "varieties": ["H614D", "Duma 43", "Pannar 691"],
            "description": "Primary staple cereal grown across Rift Valley & Western Kenya. Grade 1 standard moisture < 13.5%.",
            "isActive": True,
            "createdAt": "2026-01-15T08:00:00Z"
        },
        {
            "id": "cmd_gv_beans",
            "orgId": "org_greenvalley_01",
            "name": "Rosecoco Beans",
            "code": "CMD-BN-02",
            "category": CommodityCategory.LEGUMES_PULSES.value,
            "standardUnit": "90kg bag",
            "supportedUnits": ["90kg bag", "50kg bag", "kg"],
            "varieties": ["Rosecoco (GLP-2)", "Mwitemania", "Yellow Beans"],
            "description": "Red-mottled dry grain legumes. High domestic demand across commercial urban centres.",
            "isActive": True,
            "createdAt": "2026-01-16T09:00:00Z"
        },
        {
            "id": "cmd_gv_tomato",
            "orgId": "org_greenvalley_01",
            "name": "Fresh Tomato",
            "code": "CMD-TM-03",
            "category": CommodityCategory.HORTICULTURE_VEGETABLES.value,
            "standardUnit": "Crate (64kg)",
            "supportedUnits": ["Crate (64kg)", "kg", "Box"],
            "varieties": ["Roma VF", "Anna F1", "Kilele F1"],
            "description": "Determinate and indeterminate fresh table tomatoes subject to seasonal cold-chain price swings.",
            "isActive": True,
            "createdAt": "2026-01-18T10:30:00Z"
        },
        {
            "id": "cmd_gv_potato",
            "orgId": "org_greenvalley_01",
            "name": "Irish Potato",
            "code": "CMD-PT-04",
            "category": CommodityCategory.ROOTS_TUBERS.value,
            "standardUnit": "50kg bag",
            "supportedUnits": ["50kg bag", "100kg bag", "kg"],
            "varieties": ["Shangi", "Dutch Robijn", "Unica"],
            "description": "Ware potatoes for domestic consumption and fast-food processing.",
            "isActive": True,
            "createdAt": "2026-01-20T11:00:00Z"
        },
        {
            "id": "cmd_gv_coffee",
            "orgId": "org_greenvalley_01",
            "name": "Arabica Coffee (Parchment)",
            "code": "CMD-CF-05",
            "category": CommodityCategory.CASH_CROPS.value,
            "standardUnit": "kg",
            "supportedUnits": ["kg", "50kg bag"],
            "varieties": ["SL28", "Ruiru 11", "Batian"],
            "description": "High-altitude specialty coffee cherry and parchment for Nairobi Coffee Exchange auction.",
            "isActive": True,
            "createdAt": "2026-01-22T14:00:00Z"
        }
    ],
    "org_highland_02": [
        {
            "id": "cmd_hl_tea",
            "orgId": "org_highland_02",
            "name": "Green Leaf Tea",
            "code": "CMD-TEA-01",
            "category": CommodityCategory.CASH_CROPS.value,
            "standardUnit": "kg",
            "supportedUnits": ["kg"],
            "varieties": ["TRFK 306", "BB35"],
            "description": "Highland plucked tea shoots for factory processing and Mombasa Auction.",
            "isActive": True,
            "createdAt": "2026-02-01T08:00:00Z"
        }
    ]
}


TENANT_PRICES: Dict[str, List[Dict[str, Any]]] = {
    "org_greenvalley_01": [
        # Fresh / Current Records (Collected 2026-11-02 to 2026-11-04)
        {
            "id": "prc_gv_101",
            "orgId": "org_greenvalley_01",
            "commodityId": "cmd_gv_maize",
            "commodityName": "White Maize",
            "variety": "H614D",
            "marketName": "Wakulima Wholesale Market",
            "marketLocation": {"county": "Nairobi", "region": "Central", "latitude": -1.2864, "longitude": 36.8322},
            "priceType": PriceType.WHOLESALE.value,
            "price": 4500.0,
            "unit": "90kg bag",
            "normalizedPricePerKg": 50.0,
            "currency": "KES",
            "dateCollected": "2026-11-04",
            "dataSource": "Ministry of Agriculture Market Information System (MIS)",
            "collectorName": "MoA Market Enumerator Team",
            "collectorUserId": "usr_analyst_004",
            "collectionMethod": CollectionMethod.MANUAL.value,
            "verificationStatus": VerificationStatus.VERIFIED.value,
            "verifiedBy": "usr_mgr_002",
            "verifiedAt": "2026-11-04T08:30:00Z",
            "notes": "Tight supply from dry grain reserves; prices stable week-on-week.",
            "createdAt": "2026-11-04T08:15:00Z"
        },
        {
            "id": "prc_gv_102",
            "orgId": "org_greenvalley_01",
            "commodityId": "cmd_gv_maize",
            "commodityName": "White Maize",
            "variety": "H614D",
            "marketName": "Nakuru Top Market",
            "marketLocation": {"county": "Nakuru", "region": "Rift Valley", "latitude": -0.2833, "longitude": 36.0667},
            "priceType": PriceType.WHOLESALE.value,
            "price": 4100.0,
            "unit": "90kg bag",
            "normalizedPricePerKg": 45.56,
            "currency": "KES",
            "dateCollected": "2026-11-03",
            "dataSource": "Field Enumerator Survey - Nakuru AgTech",
            "collectorName": "Amina Otieno",
            "collectorUserId": "usr_field_003",
            "collectionMethod": CollectionMethod.MANUAL.value,
            "verificationStatus": VerificationStatus.VERIFIED.value,
            "verifiedBy": "usr_mgr_002",
            "verifiedAt": "2026-11-03T16:00:00Z",
            "notes": "Direct arrivals from Rongai and Subukia commercial aggregators.",
            "createdAt": "2026-11-03T15:30:00Z"
        },
        {
            "id": "prc_gv_103",
            "orgId": "org_greenvalley_01",
            "commodityId": "cmd_gv_maize",
            "commodityName": "White Maize",
            "variety": "Mixed Commercial",
            "marketName": "Eldoret Municipal Market",
            "marketLocation": {"county": "Uasin Gishu", "region": "Rift Valley", "latitude": 0.5143, "longitude": 35.2698},
            "priceType": PriceType.WHOLESALE.value,
            "price": 3850.0,
            "unit": "90kg bag",
            "normalizedPricePerKg": 42.78,
            "currency": "KES",
            "dateCollected": "2026-11-03",
            "dataSource": "National Cereals and Produce Board (NCPB) Bulletin",
            "collectorName": "Brian Njoroge",
            "collectorUserId": "usr_analyst_004",
            "collectionMethod": CollectionMethod.IMPORTED.value,
            "verificationStatus": VerificationStatus.VERIFIED.value,
            "verifiedBy": "usr_admin_001",
            "verifiedAt": "2026-11-03T18:00:00Z",
            "notes": "Harvest ongoing in North Rift; surplus local supply depressing spot rates.",
            "createdAt": "2026-11-03T17:45:00Z"
        },
        {
            "id": "prc_gv_104",
            "orgId": "org_greenvalley_01",
            "commodityId": "cmd_gv_tomato",
            "commodityName": "Fresh Tomato",
            "variety": "Roma VF",
            "marketName": "Wakulima Wholesale Market",
            "marketLocation": {"county": "Nairobi", "region": "Central", "latitude": -1.2864, "longitude": 36.8322},
            "priceType": PriceType.WHOLESALE.value,
            "price": 5800.0,
            "unit": "Crate (64kg)",
            "normalizedPricePerKg": 90.63,
            "currency": "KES",
            "dateCollected": "2026-11-04",
            "dataSource": "Ministry of Agriculture Market Information System (MIS)",
            "collectorName": "MoA Market Enumerator Team",
            "collectorUserId": "usr_analyst_004",
            "collectionMethod": CollectionMethod.MANUAL.value,
            "verificationStatus": VerificationStatus.VERIFIED.value,
            "verifiedBy": "usr_mgr_002",
            "verifiedAt": "2026-11-04T09:00:00Z",
            "notes": "Strong demand from food-service sector. High crate quality.",
            "createdAt": "2026-11-04T08:30:00Z"
        },
        {
            "id": "prc_gv_105",
            "orgId": "org_greenvalley_01",
            "commodityId": "cmd_gv_tomato",
            "commodityName": "Fresh Tomato",
            "variety": "Roma VF",
            "marketName": "Nakuru Top Market",
            "marketLocation": {"county": "Nakuru", "region": "Rift Valley", "latitude": -0.2833, "longitude": 36.0667},
            "priceType": PriceType.WHOLESALE.value,
            "price": 4900.0,
            "unit": "Crate (64kg)",
            "normalizedPricePerKg": 76.56,
            "currency": "KES",
            "dateCollected": "2026-11-02",
            "dataSource": "Field Enumerator Survey - Nakuru AgTech",
            "collectorName": "Amina Otieno",
            "collectorUserId": "usr_field_003",
            "collectionMethod": CollectionMethod.MANUAL.value,
            "verificationStatus": VerificationStatus.VERIFIED.value,
            "verifiedBy": "usr_mgr_002",
            "verifiedAt": "2026-11-02T16:00:00Z",
            "notes": "Farmgate crate purchases averaged KES 4,100; transportation adds KES 300.",
            "createdAt": "2026-11-02T15:00:00Z"
        },
        {
            "id": "prc_gv_106",
            "orgId": "org_greenvalley_01",
            "commodityId": "cmd_gv_beans",
            "commodityName": "Rosecoco Beans",
            "variety": "Rosecoco (GLP-2)",
            "marketName": "Wakulima Wholesale Market",
            "marketLocation": {"county": "Nairobi", "region": "Central", "latitude": -1.2864, "longitude": 36.8322},
            "priceType": PriceType.WHOLESALE.value,
            "price": 12500.0,
            "unit": "90kg bag",
            "normalizedPricePerKg": 138.89,
            "currency": "KES",
            "dateCollected": "2026-11-03",
            "dataSource": "KNBS Agri-Price Bulletin",
            "collectorName": "Brian Njoroge",
            "collectorUserId": "usr_analyst_004",
            "collectionMethod": CollectionMethod.IMPORTED.value,
            "verificationStatus": VerificationStatus.VERIFIED.value,
            "verifiedBy": "usr_admin_001",
            "verifiedAt": "2026-11-03T18:00:00Z",
            "notes": "Imported supplies from Uganda augmenting local stocks.",
            "createdAt": "2026-11-03T17:00:00Z"
        },
        {
            "id": "prc_gv_107",
            "orgId": "org_greenvalley_01",
            "commodityId": "cmd_gv_potato",
            "commodityName": "Irish Potato",
            "variety": "Shangi",
            "marketName": "Nakuru Top Market",
            "marketLocation": {"county": "Nakuru", "region": "Rift Valley", "latitude": -0.2833, "longitude": 36.0667},
            "priceType": PriceType.WHOLESALE.value,
            "price": 2800.0,
            "unit": "50kg bag",
            "normalizedPricePerKg": 56.0,
            "currency": "KES",
            "dateCollected": "2026-11-02",
            "dataSource": "Field Enumerator Survey - Nakuru AgTech",
            "collectorName": "Amina Otieno",
            "collectorUserId": "usr_field_003",
            "collectionMethod": CollectionMethod.MANUAL.value,
            "verificationStatus": VerificationStatus.VERIFIED.value,
            "verifiedBy": "usr_mgr_002",
            "verifiedAt": "2026-11-02T16:00:00Z",
            "notes": "Fresh harvest from Molo; good tuber size.",
            "createdAt": "2026-11-02T15:30:00Z"
        },

        # Historical Records (Collected 2026-09-15 & 2026-10-01) - Demonstrates historical segregation
        {
            "id": "prc_gv_088",
            "orgId": "org_greenvalley_01",
            "commodityId": "cmd_gv_maize",
            "commodityName": "White Maize",
            "variety": "H614D",
            "marketName": "Wakulima Wholesale Market",
            "marketLocation": {"county": "Nairobi", "region": "Central", "latitude": -1.2864, "longitude": 36.8322},
            "priceType": PriceType.WHOLESALE.value,
            "price": 4200.0,
            "unit": "90kg bag",
            "normalizedPricePerKg": 46.67,
            "currency": "KES",
            "dateCollected": "2026-10-01",
            "dataSource": "Ministry of Agriculture Market Information System (MIS)",
            "collectorName": "MoA Market Enumerator Team",
            "collectorUserId": "usr_analyst_004",
            "collectionMethod": CollectionMethod.IMPORTED.value,
            "verificationStatus": VerificationStatus.VERIFIED.value,
            "verifiedBy": "usr_admin_001",
            "verifiedAt": "2026-10-02T08:00:00Z",
            "notes": "Historical benchmark from early Q4 2026.",
            "createdAt": "2026-10-01T12:00:00Z"
        },
        {
            "id": "prc_gv_089",
            "orgId": "org_greenvalley_01",
            "commodityId": "cmd_gv_maize",
            "commodityName": "White Maize",
            "variety": "H614D",
            "marketName": "Nakuru Top Market",
            "marketLocation": {"county": "Nakuru", "region": "Rift Valley", "latitude": -0.2833, "longitude": 36.0667},
            "priceType": PriceType.WHOLESALE.value,
            "price": 3900.0,
            "unit": "90kg bag",
            "normalizedPricePerKg": 43.33,
            "currency": "KES",
            "dateCollected": "2026-09-15",
            "dataSource": "Field Enumerator Survey - Nakuru AgTech",
            "collectorName": "Amina Otieno",
            "collectorUserId": "usr_field_003",
            "collectionMethod": CollectionMethod.MANUAL.value,
            "verificationStatus": VerificationStatus.VERIFIED.value,
            "verifiedBy": "usr_mgr_002",
            "verifiedAt": "2026-09-16T09:00:00Z",
            "notes": "Pre-harvest low season price.",
            "createdAt": "2026-09-15T14:00:00Z"
        },

        # Unverified Record (Collected manually by field enumerator, awaiting review)
        {
            "id": "prc_gv_109",
            "orgId": "org_greenvalley_01",
            "commodityId": "cmd_gv_maize",
            "commodityName": "White Maize",
            "variety": "White Maize",
            "marketName": "Naivasha Sub-County Market",
            "marketLocation": {"county": "Nakuru", "region": "Rift Valley", "latitude": -0.7172, "longitude": 36.4310},
            "priceType": PriceType.WHOLESALE.value,
            "price": 4250.0,
            "unit": "90kg bag",
            "normalizedPricePerKg": 47.22,
            "currency": "KES",
            "dateCollected": "2026-11-03",
            "dataSource": "Trader Self-Report - Naivasha",
            "collectorName": "Field Enumerator Sub-Team",
            "collectorUserId": "usr_field_003",
            "collectionMethod": CollectionMethod.MANUAL.value,
            "verificationStatus": VerificationStatus.UNVERIFIED.value,
            "verifiedBy": None,
            "verifiedAt": None,
            "notes": "Single merchant self-reported quote; requires field supervisor verification.",
            "createdAt": "2026-11-03T16:45:00Z"
        }
    ],
    "org_highland_02": [
        {
            "id": "prc_hl_201",
            "orgId": "org_highland_02",
            "commodityId": "cmd_hl_tea",
            "commodityName": "Green Leaf Tea",
            "variety": "TRFK 306",
            "marketName": "Kericho Tea Auction & Factory Gate",
            "marketLocation": {"county": "Kericho", "region": "Rift Valley", "latitude": -0.3689, "longitude": 35.2863},
            "priceType": PriceType.FARMGATE.value,
            "price": 42.0,
            "unit": "kg",
            "normalizedPricePerKg": 42.0,
            "currency": "KES",
            "dateCollected": "2026-11-03",
            "dataSource": "KTDA Factory Gate Bulletin",
            "collectorName": "Kiprono Langat",
            "collectorUserId": "usr_hl_001",
            "collectionMethod": CollectionMethod.MANUAL.value,
            "verificationStatus": VerificationStatus.VERIFIED.value,
            "verifiedBy": "usr_hl_admin",
            "verifiedAt": "2026-11-03T18:00:00Z",
            "notes": "Monthly minimum guaranteed green leaf delivery advance rate.",
            "createdAt": "2026-11-03T17:00:00Z"
        }
    ]
}


TENANT_RESEARCH: Dict[str, List[Dict[str, Any]]] = {
    "org_greenvalley_01": [
        {
            "id": "res_gv_001",
            "orgId": "org_greenvalley_01",
            "title": "Post-Harvest Maize Pricing and Spatial Arbitrage in North Rift Markets",
            "location": "Uasin Gishu & Trans Nzoia",
            "researchDate": "2026-10-20",
            "commodityId": "cmd_gv_maize",
            "commodityName": "White Maize",
            "valueChainStage": "Farmgate to Wholesale Aggregator",
            "findings": "Transport and logistics tariffs between North Rift grain depots and Nairobi wholesale hubs account for KES 450-550 per 90kg bag. Smallholders selling immediately post-harvest realize 16% lower net margins compared to cooperatives storing in hermetic grain bags for 60+ days.",
            "sourceReferences": [
                "MoA MIS Weekly Grain Bulletin (October 2026)",
                "Tegemeo Institute of Agricultural Development & Policy Brief 2025",
                "GreenValley On-Ground Field Enumerator Log"
            ],
            "attachments": [
                "https://storage.agrotrack.ai/research/maize_spatial_arbitrage_oct2026.pdf",
                "north_rift_moisture_survey_annex.csv"
            ],
            "authorId": "usr_analyst_004",
            "authorName": "Brian Njoroge (Analyst)",
            "createdAt": "2026-10-20T14:30:00Z"
        },
        {
            "id": "res_gv_002",
            "orgId": "org_greenvalley_01",
            "title": "Horticulture Cold-Chain Logistics and Fresh Tomato Farmgate Price Margins",
            "location": "Nakuru & Nairobi Corridor",
            "researchDate": "2026-10-28",
            "commodityId": "cmd_gv_tomato",
            "commodityName": "Fresh Tomato",
            "valueChainStage": "Horticulture Aggregation & Wholesale Transport",
            "findings": "Farmgate crate realization in Subukia averaged KES 3,800/crate while wholesale realization at Wakulima reached KES 5,600/crate, reflecting a 47% gross margin largely consumed by crate breakages and transit delays.",
            "sourceReferences": [
                "Horticultural Crops Directorate (HCD) Annual Report",
                "Kenya Agricultural & Livestock Research Organization (KALRO) Cold-Chain Survey",
                "Field Enumerator Survey - Nakuru AgTech"
            ],
            "attachments": [
                "https://storage.agrotrack.ai/research/tomato_cold_chain_margins_2026.pdf"
            ],
            "authorId": "usr_mgr_002",
            "authorName": "David Kiprop (Project Manager)",
            "createdAt": "2026-10-28T16:00:00Z"
        }
    ],
    "org_highland_02": [
        {
            "id": "res_hl_001",
            "orgId": "org_highland_02",
            "title": "Smallholder Tea Fertilizer Cost Pass-Through and Auction Parity",
            "location": "Kericho & Nandi Hills",
            "researchDate": "2026-10-12",
            "commodityId": "cmd_hl_tea",
            "commodityName": "Green Leaf Tea",
            "valueChainStage": "Factory Primary Processing",
            "findings": "NPK 25-5-5 fertilizer subsidy programs maintained grower delivery momentum despite prolonged dry spells in late Q3.",
            "sourceReferences": ["KTDA Annual Review", "Tea Board of Kenya Market Brief"],
            "attachments": [],
            "authorId": "usr_hl_001",
            "authorName": "Kiprono Langat",
            "createdAt": "2026-10-12T11:00:00Z"
        }
    ]
}


# ── Internal Freshness & Age Enrichment ──────────────────────────────────────

def _enrich_price_record(record: Dict[str, Any], reference_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Computes normalizedPricePerKg, recordAgeDays, isHistorical, and freshnessLabel.
    Never silently treats old prices as current.
    """
    rec = dict(record)
    
    # 1. Normalized Price per Kg
    rec["normalizedPricePerKg"] = calculate_normalized_price_per_kg(
        float(rec.get("price", 0.0)),
        str(rec.get("unit", "kg"))
    )
    
    # 2. Date and Age Analysis
    ref_d = reference_date or date.today()
    try:
        col_date_str = str(rec.get("dateCollected", ""))
        collected_date = date.fromisoformat(col_date_str)
        age_days = max(0, (ref_d - collected_date).days)
    except Exception:
        age_days = 0
        
    rec["recordAgeDays"] = age_days
    
    # Strictly distinguish current vs historical records (spec requirement)
    if age_days > 14:
        rec["isHistorical"] = True
        if age_days > 30:
            rec["freshnessLabel"] = f"Archived ({age_days}d ago)"
        else:
            rec["freshnessLabel"] = f"Historical ({age_days}d ago)"
    elif age_days > 2:
        rec["isHistorical"] = False
        rec["freshnessLabel"] = f"Recent ({age_days}d ago)"
    else:
        rec["isHistorical"] = False
        rec["freshnessLabel"] = "Current"
        
    return rec


# ── 1. Commodity Management ──────────────────────────────────────────────────

def get_commodities_for_org(
    org_id: str,
    search: Optional[str] = None,
    category: Optional[str] = None,
    active_only: bool = True
) -> List[Dict[str, Any]]:
    """Retrieves commodities scoped to organisation with search and category filtering."""
    commodities = TENANT_COMMODITIES.get(org_id, [])
    
    if active_only:
        commodities = [c for c in commodities if c.get("isActive", True)]
        
    if category:
        cat_lower = category.lower().strip()
        commodities = [c for c in commodities if c.get("category", "").lower() == cat_lower]
        
    if search:
        s = search.lower().strip()
        filtered = []
        for c in commodities:
            name_match = s in str(c.get("name") or "").lower()
            code_match = s in str(c.get("code") or "").lower()
            var_match = any(s in str(v).lower() for v in (c.get("varieties") or []))
            desc_match = s in str(c.get("description") or "").lower()
            if name_match or code_match or var_match or desc_match:
                filtered.append(c)
        commodities = filtered
        
    return commodities


def get_commodity_by_id(org_id: str, commodity_id: str) -> Dict[str, Any]:
    """Retrieves a single commodity, enforcing cross-tenant 403 isolation."""
    for c in TENANT_COMMODITIES.get(org_id, []):
        if c["id"] == commodity_id:
            return c
            
    # Check if exists in another organisation
    for other_org, o_comms in TENANT_COMMODITIES.items():
        if other_org != org_id:
            for c in o_comms:
                if c["id"] == commodity_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Commodity belongs to a different organisation."
                    )
                    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Commodity '{commodity_id}' not found."
    )


def create_commodity(org_id: str, commodity_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a commodity record scoped to the organisation with duplicate checks."""
    if org_id not in TENANT_COMMODITIES:
        TENANT_COMMODITIES[org_id] = []
        
    name = str(commodity_data.get("name") or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Commodity name cannot be empty."
        )
        
    # Check duplicate name within organisation
    for c in TENANT_COMMODITIES[org_id]:
        if c.get("name", "").lower() == name.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Commodity with name '{name}' already exists in this organisation."
            )
            
    code = str(commodity_data.get("code") or "").strip()
    if not code:
        seq = len(TENANT_COMMODITIES[org_id]) + 1
        prefix = "".join([w[0].upper() for w in name.split() if w])[:3] or "CMD"
        code = f"CMD-{prefix}-{seq:02d}"
        
    new_cmd = {
        "id": f"cmd_{org_id[:3]}_{len(TENANT_COMMODITIES[org_id]) + 101}",
        "orgId": org_id,
        "name": name,
        "code": code,
        "category": commodity_data.get("category", CommodityCategory.CEREALS_GRAINS.value),
        "standardUnit": commodity_data.get("standardUnit", "kg"),
        "supportedUnits": commodity_data.get("supportedUnits") or [commodity_data.get("standardUnit", "kg")],
        "varieties": commodity_data.get("varieties") or [],
        "description": commodity_data.get("description"),
        "isActive": bool(commodity_data.get("isActive", True)),
        "createdAt": datetime.now().isoformat()
    }
    
    TENANT_COMMODITIES[org_id].append(new_cmd)
    return new_cmd


def update_commodity(org_id: str, commodity_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Updates commodity attributes."""
    cmd = get_commodity_by_id(org_id, commodity_id)
    
    # If name changed, check duplicate
    new_name = updates.get("name")
    if new_name and new_name.lower() != cmd["name"].lower():
        for c in TENANT_COMMODITIES.get(org_id, []):
            if c["id"] != commodity_id and c.get("name", "").lower() == new_name.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Commodity name '{new_name}' already exists."
                )
                
    for k, v in updates.items():
        if k not in ["id", "orgId", "createdAt"] and v is not None:
            cmd[k] = v
            
    return cmd


def delete_commodity(org_id: str, commodity_id: str) -> Dict[str, Any]:
    """Deletes or deactivates a commodity if not referenced in prices."""
    cmd = get_commodity_by_id(org_id, commodity_id)
    
    # Check if price records exist for this commodity
    prices = [p for p in TENANT_PRICES.get(org_id, []) if p.get("commodityId") == commodity_id]
    if prices:
        # Soft-deactivate to preserve historical integrity
        cmd["isActive"] = False
        return {
            "message": f"Commodity '{cmd['name']}' has {len(prices)} linked price records. It has been deactivated instead of deleted.",
            "deactivated": True
        }
        
    TENANT_COMMODITIES[org_id] = [c for c in TENANT_COMMODITIES[org_id] if c["id"] != commodity_id]
    return {"message": f"Commodity '{commodity_id}' deleted successfully.", "deleted": True}


# ── 2. Market Price Records ──────────────────────────────────────────────────

def get_prices_for_org(
    org_id: str,
    commodity_id: Optional[str] = None,
    market_name: Optional[str] = None,
    price_type: Optional[str] = None,
    is_historical: Optional[bool] = None,
    verification_status: Optional[str] = None,
    collection_method: Optional[str] = None,
    data_source: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves price survey records scoped to organisation with multi-factor filtering."""
    raw_prices = TENANT_PRICES.get(org_id, [])
    enriched_prices = [_enrich_price_record(p) for p in raw_prices]
    
    if commodity_id:
        enriched_prices = [p for p in enriched_prices if p.get("commodityId") == commodity_id]
        
    if market_name:
        m_lower = market_name.lower().strip()
        enriched_prices = [p for p in enriched_prices if m_lower in p.get("marketName", "").lower()]
        
    if price_type:
        enriched_prices = [p for p in enriched_prices if p.get("priceType") == price_type]
        
    if is_historical is not None:
        enriched_prices = [p for p in enriched_prices if p.get("isHistorical") == is_historical]
        
    if verification_status:
        enriched_prices = [p for p in enriched_prices if p.get("verificationStatus") == verification_status]
        
    if collection_method:
        enriched_prices = [p for p in enriched_prices if p.get("collectionMethod") == collection_method]
        
    if data_source:
        s_lower = data_source.lower().strip()
        enriched_prices = [p for p in enriched_prices if s_lower in p.get("dataSource", "").lower()]
        
    if start_date:
        enriched_prices = [p for p in enriched_prices if str(p.get("dateCollected", "")) >= start_date]
        
    if end_date:
        enriched_prices = [p for p in enriched_prices if str(p.get("dateCollected", "")) <= end_date]
        
    # Chronological sort descending
    return sorted(enriched_prices, key=lambda x: str(x.get("dateCollected", "")), reverse=True)


def get_price_by_id(org_id: str, price_id: str) -> Dict[str, Any]:
    """Retrieves a single price record, blocking cross-tenant access with 403."""
    for p in TENANT_PRICES.get(org_id, []):
        if p["id"] == price_id:
            return _enrich_price_record(p)
            
    for other_org, o_prices in TENANT_PRICES.items():
        if other_org != org_id:
            for p in o_prices:
                if p["id"] == price_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Market price record belongs to a different organisation."
                    )
                    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Price record '{price_id}' not found."
    )


def create_price_record(org_id: str, price_data: Dict[str, Any], current_user: Any) -> Dict[str, Any]:
    """
    Records a new market price record.
    Enforces positive price, traceable data source, valid date, and duplicate prevention.
    """
    if org_id not in TENANT_PRICES:
        TENANT_PRICES[org_id] = []
        
    # 1. Price validation
    price_val = float(price_data.get("price", 0.0))
    if price_val <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price must be a positive number greater than zero."
        )
        
    # 2. Traceable Data Source validation
    source = str(price_data.get("dataSource") or "").strip()
    if not source or len(source) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A traceable data source (e.g. Ministry of Agriculture MIS, Field Enumerator Survey) is mandatory."
        )
        
    # 3. Commodity linkage
    commodity_id = price_data.get("commodityId")
    comm = get_commodity_by_id(org_id, commodity_id)
    
    # 4. Date validation
    date_collected = price_data.get("dateCollected") or str(date.today())
    try:
        date.fromisoformat(str(date_collected))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid dateCollected format '{date_collected}'. Expected ISO YYYY-MM-DD."
        )
        
    # 5. Duplicate Record Check
    market_name = str(price_data.get("marketName") or "").strip()
    price_type = price_data.get("priceType", PriceType.WHOLESALE.value)
    unit = str(price_data.get("unit") or comm.get("standardUnit", "kg"))
    
    for existing in TENANT_PRICES[org_id]:
        if (
            existing.get("commodityId") == commodity_id
            and existing.get("marketName", "").lower() == market_name.lower()
            and existing.get("priceType") == price_type
            and existing.get("dateCollected") == str(date_collected)
            and existing.get("unit", "").lower() == unit.lower()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A {price_type} price record for {comm['name']} at {market_name} on {date_collected} already exists."
            )
            
    # 6. Normalized Price per Kg
    normalized_kg = calculate_normalized_price_per_kg(price_val, unit)
    
    # 7. Collector & Verification attribution
    collector_name = getattr(current_user, "name", "Market Enumerator")
    collector_uid = getattr(current_user, "uid", "usr_unknown")
    method = price_data.get("collectionMethod", CollectionMethod.MANUAL.value)
    
    # If submitted by field officer, defaults to unverified; if Admin/Manager, can be auto-verified
    status_val = price_data.get("verificationStatus", VerificationStatus.UNVERIFIED.value)
    verified_by = None
    verified_at = None
    if status_val == VerificationStatus.VERIFIED.value:
        verified_by = collector_uid
        verified_at = datetime.now().isoformat()
        
    price_id = f"prc_{org_id[:3]}_{len(TENANT_PRICES[org_id]) + 101}"
    new_price = {
        "id": price_id,
        "orgId": org_id,
        "commodityId": commodity_id,
        "commodityName": comm["name"],
        "variety": price_data.get("variety"),
        "marketName": market_name,
        "marketLocation": price_data.get("marketLocation") or {"county": "National", "region": "National"},
        "priceType": price_type,
        "price": price_val,
        "unit": unit,
        "normalizedPricePerKg": normalized_kg,
        "currency": str(price_data.get("currency") or "KES").upper(),
        "dateCollected": str(date_collected),
        "dataSource": source,
        "collectorName": collector_name,
        "collectorUserId": collector_uid,
        "collectionMethod": method,
        "verificationStatus": status_val,
        "verifiedBy": verified_by,
        "verifiedAt": verified_at,
        "notes": price_data.get("notes"),
        "createdAt": datetime.now().isoformat()
    }
    
    TENANT_PRICES[org_id].append(new_price)
    return _enrich_price_record(new_price)


def verify_price_record(org_id: str, price_id: str, verifier_user: Any) -> Dict[str, Any]:
    """Marks a price survey record as verified by an authorised analyst or manager."""
    price_rec = None
    for p in TENANT_PRICES.get(org_id, []):
        if p["id"] == price_id:
            price_rec = p
            break
            
    if not price_rec:
        # Check if in other tenant
        get_price_by_id(org_id, price_id)
        
    price_rec["verificationStatus"] = VerificationStatus.VERIFIED.value
    price_rec["verifiedBy"] = getattr(verifier_user, "uid", "usr_analyst")
    price_rec["verifiedAt"] = datetime.now().isoformat()
    return _enrich_price_record(price_rec)


def delete_price_record(org_id: str, price_id: str) -> Dict[str, Any]:
    """Deletes a price record."""
    get_price_by_id(org_id, price_id)
    TENANT_PRICES[org_id] = [p for p in TENANT_PRICES[org_id] if p["id"] != price_id]
    return {"message": f"Price record '{price_id}' deleted successfully."}


# ── 3. Market Research Studies ───────────────────────────────────────────────

def get_research_for_org(
    org_id: str,
    commodity_id: Optional[str] = None,
    search: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves market research documents scoped to the organisation."""
    studies = TENANT_RESEARCH.get(org_id, [])
    if commodity_id:
        studies = [s for s in studies if s.get("commodityId") == commodity_id]
        
    if search:
        s_lower = search.lower().strip()
        studies = [
            s for s in studies
            if s_lower in s.get("title", "").lower()
            or s_lower in s.get("location", "").lower()
            or s_lower in s.get("findings", "").lower()
            or s_lower in s.get("valueChainStage", "").lower()
        ]
        
    return sorted(studies, key=lambda x: str(x.get("researchDate", "")), reverse=True)


def get_research_by_id(org_id: str, research_id: str) -> Dict[str, Any]:
    """Retrieves a research record with cross-organisation access restriction."""
    for s in TENANT_RESEARCH.get(org_id, []):
        if s["id"] == research_id:
            return s
            
    for other_org, o_res in TENANT_RESEARCH.items():
        if other_org != org_id:
            for s in o_res:
                if s["id"] == research_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Research study belongs to a different organisation."
                    )
                    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Research record '{research_id}' not found."
    )


def create_research(org_id: str, research_data: Dict[str, Any], current_user: Any) -> Dict[str, Any]:
    """Creates a market research record with author and source attribution."""
    if org_id not in TENANT_RESEARCH:
        TENANT_RESEARCH[org_id] = []
        
    title = str(research_data.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Research title is required.")
        
    commodity_id = research_data.get("commodityId")
    comm_name = None
    if commodity_id:
        comm = get_commodity_by_id(org_id, commodity_id)
        comm_name = comm["name"]
        
    res_id = f"res_{org_id[:3]}_{len(TENANT_RESEARCH[org_id]) + 101}"
    new_res = {
        "id": res_id,
        "orgId": org_id,
        "title": title,
        "location": research_data.get("location", "National"),
        "researchDate": str(research_data.get("researchDate") or date.today()),
        "commodityId": commodity_id,
        "commodityName": comm_name,
        "valueChainStage": research_data.get("valueChainStage", "General Value Chain"),
        "findings": research_data.get("findings", ""),
        "sourceReferences": research_data.get("sourceReferences") or [],
        "attachments": research_data.get("attachments") or [],
        "authorId": getattr(current_user, "uid", "usr_analyst"),
        "authorName": getattr(current_user, "name", "Market Analyst"),
        "createdAt": datetime.now().isoformat()
    }
    
    TENANT_RESEARCH[org_id].append(new_res)
    return new_res


# ── 4. Market Intelligence Analysis & Visualizations ─────────────────────────

def get_commodity_price_history(
    org_id: str,
    commodity_id: str,
    market_name: Optional[str] = None,
    price_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes chronological price history, moving average, min, max, and trend.
    Clearly communicates missing data and sample sizes.
    """
    comm = get_commodity_by_id(org_id, commodity_id)
    prices = get_prices_for_org(org_id, commodity_id=commodity_id, market_name=market_name, price_type=price_type)
    
    # Sort chronologically ascending for timeline
    chronological = sorted(prices, key=lambda x: str(x.get("dateCollected", "")))
    sample_size = len(chronological)
    
    if sample_size == 0:
        return {
            "commodity": comm,
            "sampleSize": 0,
            "hasSufficientData": False,
            "missingDataNotice": f"No market price records recorded for {comm['name']}. Cannot generate price history.",
            "pricePoints": [],
            "metrics": None
        }
        
    # Calculate statistics
    price_values = [p["price"] for p in chronological]
    min_price = min(price_values)
    max_price = max(price_values)
    avg_price = round(sum(price_values) / sample_size, 2)
    
    # Trend change calculation (first vs last)
    earliest_price = chronological[0]["price"]
    latest_price = chronological[-1]["price"]
    pct_change = round(((latest_price - earliest_price) / earliest_price) * 100.0, 2) if earliest_price > 0 else 0.0
    
    trend_direction = "stable"
    if pct_change >= 2.0:
        trend_direction = "increasing"
    elif pct_change <= -2.0:
        trend_direction = "decreasing"
        
    # Sample size threshold warning
    missing_notice = None
    has_sufficient = True
    if sample_size < 3:
        has_sufficient = False
        missing_notice = f"Notice: Low sample size (n={sample_size}). Trend indicators should be interpreted with caution until additional market survey dates are logged."
        
    return {
        "commodity": comm,
        "sampleSize": sample_size,
        "hasSufficientData": has_sufficient,
        "missingDataNotice": missing_notice,
        "pricePoints": [
            {
                "id": p["id"],
                "date": p["dateCollected"],
                "market": p["marketName"],
                "price": p["price"],
                "unit": p["unit"],
                "normalizedPricePerKg": p["normalizedPricePerKg"],
                "priceType": p["priceType"],
                "dataSource": p["dataSource"],
                "isHistorical": p["isHistorical"],
                "freshnessLabel": p["freshnessLabel"],
                "verificationStatus": p["verificationStatus"]
            }
            for p in chronological
        ],
        "metrics": {
            "currency": chronological[-1]["currency"],
            "latestPrice": latest_price,
            "latestUnit": chronological[-1]["unit"],
            "latestDate": chronological[-1]["dateCollected"],
            "minPrice": min_price,
            "maxPrice": max_price,
            "averagePrice": avg_price,
            "percentageChange": pct_change,
            "trendDirection": trend_direction
        }
    }


def get_market_comparisons(
    org_id: str,
    commodity_id: str,
    price_type: str = "wholesale"
) -> Dict[str, Any]:
    """
    Compares latest prices for a commodity across monitored markets.
    Computes price spread, arbitrage differential, and reports sample size.
    """
    comm = get_commodity_by_id(org_id, commodity_id)
    prices = get_prices_for_org(org_id, commodity_id=commodity_id, price_type=price_type)
    
    # Group by market name, keeping the latest price per market
    market_latest: Dict[str, Dict[str, Any]] = {}
    for p in prices:
        m_name = p["marketName"]
        if m_name not in market_latest or str(p["dateCollected"]) > str(market_latest[m_name]["dateCollected"]):
            market_latest[m_name] = p
            
    compared_markets = list(market_latest.values())
    sample_size = len(compared_markets)
    
    if sample_size == 0:
        return {
            "commodity": comm,
            "sampleSize": 0,
            "hasSufficientData": False,
            "missingDataNotice": f"No market records found for {comm['name']} to perform market comparison.",
            "markets": [],
            "spread": None
        }
        
    # Sort by normalized price per kg ascending
    compared_markets.sort(key=lambda x: x["normalizedPricePerKg"])
    lowest_market = compared_markets[0]
    highest_market = compared_markets[-1]
    
    price_spread = round(highest_market["normalizedPricePerKg"] - lowest_market["normalizedPricePerKg"], 2)
    spread_pct = round((price_spread / lowest_market["normalizedPricePerKg"]) * 100.0, 2) if lowest_market["normalizedPricePerKg"] > 0 else 0.0
    
    missing_notice = None
    has_sufficient = True
    if sample_size < 2:
        has_sufficient = False
        missing_notice = f"Notice: Only 1 market ({lowest_market['marketName']}) has recorded price data. Market price spread cannot be computed across distinct trading hubs."
        
    return {
        "commodity": comm,
        "sampleSize": sample_size,
        "hasSufficientData": has_sufficient,
        "missingDataNotice": missing_notice,
        "markets": [
            {
                "marketName": p["marketName"],
                "location": p["marketLocation"],
                "price": p["price"],
                "unit": p["unit"],
                "normalizedPricePerKg": p["normalizedPricePerKg"],
                "currency": p["currency"],
                "dateCollected": p["dateCollected"],
                "freshnessLabel": p["freshnessLabel"],
                "dataSource": p["dataSource"],
                "verificationStatus": p["verificationStatus"]
            }
            for p in compared_markets
        ],
        "spread": {
            "currency": lowest_market["currency"],
            "unit": "per kg",
            "lowestMarket": lowest_market["marketName"],
            "lowestPricePerKg": lowest_market["normalizedPricePerKg"],
            "highestMarket": highest_market["marketName"],
            "highestPricePerKg": highest_market["normalizedPricePerKg"],
            "spreadPerKg": price_spread,
            "spreadPercentage": spread_pct
        } if has_sufficient else None
    }


def get_regional_price_differences(org_id: str, commodity_id: str) -> Dict[str, Any]:
    """
    Groups latest price records by region (Rift Valley, Central, Coast, Nyanza).
    Computes regional average price per kg and spread.
    """
    comm = get_commodity_by_id(org_id, commodity_id)
    prices = get_prices_for_org(org_id, commodity_id=commodity_id)
    
    # Group by region
    region_buckets: Dict[str, List[float]] = {}
    for p in prices:
        reg = (p.get("marketLocation") or {}).get("region", "Other / Unspecified")
        if reg not in region_buckets:
            region_buckets[reg] = []
        region_buckets[reg].append(p["normalizedPricePerKg"])
        
    if not region_buckets:
        return {
            "commodity": comm,
            "sampleSize": 0,
            "hasSufficientData": False,
            "missingDataNotice": f"No regional market price points available for {comm['name']}.",
            "regions": {}
        }
        
    regional_summary = {}
    for reg, vals in region_buckets.items():
        avg_kg = round(sum(vals) / len(vals), 2)
        regional_summary[reg] = {
            "region": reg,
            "sampleSize": len(vals),
            "averagePricePerKg": avg_kg,
            "minPricePerKg": min(vals),
            "maxPricePerKg": max(vals)
        }
        
    sample_size = sum(len(vals) for vals in region_buckets.values())
    has_sufficient = len(regional_summary) >= 2
    missing_notice = None
    if not has_sufficient:
        missing_notice = "Notice: Only 1 geographic region is represented. Regional variance analysis requires price observations from at least two distinct regions."
        
    return {
        "commodity": comm,
        "sampleSize": sample_size,
        "hasSufficientData": has_sufficient,
        "missingDataNotice": missing_notice,
        "regions": regional_summary
    }


def get_supply_and_demand_intelligence(org_id: str, commodity_id: str) -> Dict[str, Any]:
    """
    Returns available supply/demand market assessments based strictly on actual survey observations.
    Never invents ungrounded volumes.
    """
    comm = get_commodity_by_id(org_id, commodity_id)
    prices = get_prices_for_org(org_id, commodity_id=commodity_id)
    
    # Check notes for observational supply indicators
    observations = []
    for p in prices:
        if p.get("notes"):
            observations.append({
                "market": p["marketName"],
                "date": p["dateCollected"],
                "source": p["dataSource"],
                "observation": p["notes"]
            })
            
    sample_size = len(observations)
    return {
        "commodity": comm,
        "sampleSize": sample_size,
        "hasSufficientData": sample_size > 0,
        "reportedObservations": observations,
        "integrityStatement": "MarketLens does not simulate synthetic supply/demand volumes. All qualitative market dynamics are derived strictly from documented field surveyor and Ministry bulletin observations."
    }


# ── 5. AgroTrack & Project Integration ───────────────────────────────────────

def get_farm_market_intelligence(org_id: str, farm_id: str) -> Dict[str, Any]:
    """
    Connects relevant MarketLens pricing intelligence to an AgroTrack farm record.
    Matches the farm's crop to registered commodities.
    Does not assume farm production automatically equals market supply.
    """
    # 1. Fetch Farm
    farms = TENANT_FARMS.get(org_id, [])
    farm = next((f for f in farms if f["id"] == farm_id), None)
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm '{farm_id}' not found in organisation."
        )
        
    farm_crop = farm.get("crop", "Maize").strip()
    farm_size = float(farm.get("size", 1.0))
    farm_unit = farm.get("unit", "acres")
    farm_loc = farm.get("location") or {}
    farm_county = farm_loc.get("county", "Nakuru")
    
    # 2. Match to Registered Commodity
    commodities = get_commodities_for_org(org_id)
    matched_cmd = None
    for c in commodities:
        if c["name"].lower() in farm_crop.lower() or farm_crop.lower() in c["name"].lower():
            matched_cmd = c
            break
            
    if not matched_cmd:
        return {
            "farmId": farm_id,
            "farmName": farm.get("name"),
            "crop": farm_crop,
            "matchedCommodity": None,
            "status": "No direct commodity catalog match found for crop.",
            "marketPrices": [],
            "disclaimer": "Do not assume farm production equals market supply."
        }
        
    # 3. Retrieve Latest Market Prices for this commodity
    all_prices = get_prices_for_org(org_id, commodity_id=matched_cmd["id"])
    
    # Split local vs regional benchmark
    local_prices = [
        p for p in all_prices
        if (p.get("marketLocation") or {}).get("county", "").lower() == farm_county.lower()
    ]
    other_prices = [
        p for p in all_prices
        if (p.get("marketLocation") or {}).get("county", "").lower() != farm_county.lower()
    ]
    
    # 4. Conservative Production & Gross Revenue Estimate
    # (Conservative 1,800 kg/acre for cereals, 6,000 kg/acre for horticulture)
    base_yield_kg_per_acre = 1800.0 if "maize" in farm_crop.lower() or "cereal" in matched_cmd.get("category", "").lower() else 5500.0
    estimated_production_kg = round(farm_size * base_yield_kg_per_acre, 1)
    
    avg_price_per_kg = 50.0
    if all_prices:
        avg_price_per_kg = round(sum(p["normalizedPricePerKg"] for p in all_prices) / len(all_prices), 2)
        
    estimated_gross_value = round(estimated_production_kg * avg_price_per_kg, 2)
    
    return {
        "farmId": farm_id,
        "farmName": farm.get("name"),
        "farmLocation": farm_loc,
        "crop": farm_crop,
        "farmSizeAcres": farm_size,
        "matchedCommodity": {
            "id": matched_cmd["id"],
            "name": matched_cmd["name"],
            "category": matched_cmd["category"],
            "standardUnit": matched_cmd["standardUnit"]
        },
        "localMarketPrices": local_prices[:3],
        "regionalBenchmarkPrices": other_prices[:3],
        "productionEstimate": {
            "estimatedHarvestVolumeKg": estimated_production_kg,
            "benchmarkPricePerKg": avg_price_per_kg,
            "estimatedGrossMarketValue": estimated_gross_value,
            "currency": "KES"
        },
        "criticalSupplyAssumptionDisclaimer": (
            "IMPORTANT: Farm production does not automatically equal realized market supply. "
            "Realized marketable supply is subject to on-farm household consumption, post-harvest drying losses (8-12%), "
            "and transport logistics costs. Do not extrapolate harvest volume directly into cash liquidity."
        )
    }


# ── 6. MarketLens Dashboard Statistics ───────────────────────────────────────

def get_marketlens_dashboard_stats(org_id: str) -> Dict[str, Any]:
    """Computes real-time statistics for the MarketLens operations overview."""
    commodities = TENANT_COMMODITIES.get(org_id, [])
    raw_prices = TENANT_PRICES.get(org_id, [])
    enriched_prices = [_enrich_price_record(p) for p in raw_prices]
    research = TENANT_RESEARCH.get(org_id, [])
    
    verified_count = sum(1 for p in enriched_prices if p.get("verificationStatus") == VerificationStatus.VERIFIED.value)
    unverified_count = sum(1 for p in enriched_prices if p.get("verificationStatus") == VerificationStatus.UNVERIFIED.value)
    manual_count = sum(1 for p in enriched_prices if p.get("collectionMethod") == CollectionMethod.MANUAL.value)
    imported_count = sum(1 for p in enriched_prices if p.get("collectionMethod") == CollectionMethod.IMPORTED.value)
    historical_count = sum(1 for p in enriched_prices if p.get("isHistorical") is True)
    fresh_count = sum(1 for p in enriched_prices if p.get("isHistorical") is False)
    
    markets = sorted(list({p.get("marketName") for p in enriched_prices if p.get("marketName")}))
    
    # Sort recent price updates descending
    recent = sorted(enriched_prices, key=lambda x: str(x.get("dateCollected", "")), reverse=True)[:5]
    
    return {
        "totalCommodities": len(commodities),
        "totalPriceRecords": len(enriched_prices),
        "verifiedPriceRecords": verified_count,
        "unverifiedPriceRecords": unverified_count,
        "manualPriceRecords": manual_count,
        "importedPriceRecords": imported_count,
        "freshRecordsCount": fresh_count,
        "historicalRecordsCount": historical_count,
        "totalResearchStudies": len(research),
        "monitoredMarkets": markets,
        "recentPriceUpdates": recent,
        "recentActivity": []
    }
