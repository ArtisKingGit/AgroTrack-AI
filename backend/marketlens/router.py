"""
AgroTrack AI — MarketLens API Router
Exposes endpoints for commodities, market prices, verification, research, analytics, and farm integration.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.models import (
    Role,
    UserProfile,
    Commodity,
    CommodityCreateRequest,
    CommodityUpdateRequest,
    MarketPriceRecord,
    MarketPriceCreateRequest,
    MarketResearch,
    MarketResearchCreateRequest,
    MarketLensDashboardStats,
)
from backend.security import get_current_user, require_roles
from backend.marketlens.service import (
    get_commodities_for_org,
    get_commodity_by_id,
    create_commodity,
    update_commodity,
    delete_commodity,
    get_prices_for_org,
    get_price_by_id,
    create_price_record,
    verify_price_record,
    delete_price_record,
    get_research_for_org,
    get_research_by_id,
    create_research,
    get_commodity_price_history,
    get_market_comparisons,
    get_regional_price_differences,
    get_supply_and_demand_intelligence,
    get_farm_market_intelligence,
    get_marketlens_dashboard_stats,
)

router = APIRouter(prefix="/api/v1/marketlens", tags=["MarketLens Agricultural Intelligence"])


# ── 1. Dashboard Statistics ──────────────────────────────────────────────────

@router.get("/dashboard/stats", response_model=MarketLensDashboardStats)
async def get_dashboard_stats_endpoint(
    current_user: UserProfile = Depends(get_current_user)
):
    """Retrieves live real-time statistics from actual MarketLens database queries."""
    return get_marketlens_dashboard_stats(current_user.defaultOrgId)


# ── 2. Commodity Registry Endpoints ──────────────────────────────────────────

@router.get("/commodities", response_model=List[Commodity])
async def list_commodities_endpoint(
    search: Optional[str] = Query(None, description="Search commodity name, code, or variety"),
    category: Optional[str] = Query(None, description="Filter by category (e.g. Cereals & Grains)"),
    active_only: bool = Query(True, description="Filter to active commodities only"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Lists registered commodities for the organisation with search and category filtering."""
    return get_commodities_for_org(
        current_user.defaultOrgId,
        search=search,
        category=category,
        active_only=active_only
    )


@router.post("/commodities", response_model=Commodity, status_code=status.HTTP_201_CREATED)
async def create_commodity_endpoint(
    request: CommodityCreateRequest,
    current_user: UserProfile = Depends(require_roles([
        Role.ORGANISATION_ADMIN,
        Role.PROJECT_MANAGER,
        Role.ANALYST
    ]))
):
    """Registers a new agricultural commodity in the organisation catalog."""
    return create_commodity(current_user.defaultOrgId, request.model_dump())


@router.get("/commodities/{commodity_id}", response_model=Commodity)
async def get_commodity_endpoint(
    commodity_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """Retrieves details of a specific commodity, blocking cross-tenant access."""
    return get_commodity_by_id(current_user.defaultOrgId, commodity_id)


@router.put("/commodities/{commodity_id}", response_model=Commodity)
async def update_commodity_endpoint(
    commodity_id: str,
    request: CommodityUpdateRequest,
    current_user: UserProfile = Depends(require_roles([
        Role.ORGANISATION_ADMIN,
        Role.PROJECT_MANAGER,
        Role.ANALYST
    ]))
):
    """Updates commodity parameters and supported units."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    return update_commodity(current_user.defaultOrgId, commodity_id, updates)


@router.delete("/commodities/{commodity_id}")
async def delete_commodity_endpoint(
    commodity_id: str,
    current_user: UserProfile = Depends(require_roles([
        Role.ORGANISATION_ADMIN,
        Role.PROJECT_MANAGER
    ]))
):
    """Deletes or deactivates a commodity record."""
    return delete_commodity(current_user.defaultOrgId, commodity_id)


# ── 3. Market Price Records Endpoints ─────────────────────────────────────────

@router.get("/prices", response_model=List[MarketPriceRecord])
async def list_prices_endpoint(
    commodity_id: Optional[str] = Query(None, description="Filter by commodity ID"),
    market_name: Optional[str] = Query(None, description="Filter by market name"),
    price_type: Optional[str] = Query(None, description="wholesale, retail, or farmgate"),
    is_historical: Optional[bool] = Query(None, description="Filter current vs historical records"),
    verification_status: Optional[str] = Query(None, description="verified vs unverified"),
    collection_method: Optional[str] = Query(None, description="manual vs imported"),
    data_source: Optional[str] = Query(None, description="Filter by data source string"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Lists market price survey records with traceable source attribution.
    Distinguishes verified vs unverified, and fresh vs historical records.
    """
    return get_prices_for_org(
        current_user.defaultOrgId,
        commodity_id=commodity_id,
        market_name=market_name,
        price_type=price_type,
        is_historical=is_historical,
        verification_status=verification_status,
        collection_method=collection_method,
        data_source=data_source,
        start_date=start_date,
        end_date=end_date
    )


@router.post("/prices", response_model=MarketPriceRecord, status_code=status.HTTP_201_CREATED)
async def create_price_endpoint(
    request: MarketPriceCreateRequest,
    current_user: UserProfile = Depends(require_roles([
        Role.ORGANISATION_ADMIN,
        Role.PROJECT_MANAGER,
        Role.FIELD_OFFICER,
        Role.ANALYST
    ]))
):
    """Records a new market price survey observation with mandatory traceable source."""
    return create_price_record(current_user.defaultOrgId, request.model_dump(), current_user)


@router.get("/prices/{price_id}", response_model=MarketPriceRecord)
async def get_price_endpoint(
    price_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """Retrieves an individual price survey record."""
    return get_price_by_id(current_user.defaultOrgId, price_id)


@router.post("/prices/{price_id}/verify", response_model=MarketPriceRecord)
async def verify_price_endpoint(
    price_id: str,
    current_user: UserProfile = Depends(require_roles([
        Role.ORGANISATION_ADMIN,
        Role.PROJECT_MANAGER,
        Role.ANALYST
    ]))
):
    """Verifies a price record after quality inspection."""
    return verify_price_record(current_user.defaultOrgId, price_id, current_user)


@router.delete("/prices/{price_id}")
async def delete_price_endpoint(
    price_id: str,
    current_user: UserProfile = Depends(require_roles([
        Role.ORGANISATION_ADMIN,
        Role.PROJECT_MANAGER
    ]))
):
    """Deletes an erroneous price record."""
    return delete_price_record(current_user.defaultOrgId, price_id)


# ── 4. Market Research Studies Endpoints ─────────────────────────────────────

@router.get("/research", response_model=List[MarketResearch])
async def list_research_endpoint(
    commodity_id: Optional[str] = Query(None, description="Filter by commodity ID"),
    search: Optional[str] = Query(None, description="Search title, findings, or location"),
    current_user: UserProfile = Depends(get_current_user)
):
    """Lists market research and value-chain study records."""
    return get_research_for_org(current_user.defaultOrgId, commodity_id=commodity_id, search=search)


@router.post("/research", response_model=MarketResearch, status_code=status.HTTP_201_CREATED)
async def create_research_endpoint(
    request: MarketResearchCreateRequest,
    current_user: UserProfile = Depends(require_roles([
        Role.ORGANISATION_ADMIN,
        Role.PROJECT_MANAGER,
        Role.ANALYST
    ]))
):
    """Submits a new market research study with source references and author attribution."""
    return create_research(current_user.defaultOrgId, request.model_dump(), current_user)


@router.get("/research/{research_id}", response_model=MarketResearch)
async def get_research_endpoint(
    research_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """Retrieves an individual research study."""
    return get_research_by_id(current_user.defaultOrgId, research_id)


# ── 5. Market Intelligence Analysis Endpoints ────────────────────────────────

@router.get("/analysis/price-history")
async def get_price_history_endpoint(
    commodity_id: str = Query(..., description="Target commodity ID"),
    market_name: Optional[str] = Query(None, description="Filter to a specific market"),
    price_type: Optional[str] = Query(None, description="wholesale, retail, or farmgate"),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Computes chronological price history with moving average, min/max, and trend direction.
    Explicitly reports sample sizes and data completeness warnings.
    """
    return get_commodity_price_history(
        current_user.defaultOrgId,
        commodity_id,
        market_name=market_name,
        price_type=price_type
    )


@router.get("/analysis/market-comparison")
async def get_market_comparison_endpoint(
    commodity_id: str = Query(..., description="Target commodity ID"),
    price_type: str = Query("wholesale", description="wholesale, retail, or farmgate"),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Compares latest prices across primary trading hubs for a commodity.
    Calculates spatial price spread and arbitrage differentials.
    """
    return get_market_comparisons(
        current_user.defaultOrgId,
        commodity_id,
        price_type=price_type
    )


@router.get("/analysis/regional-differences")
async def get_regional_differences_endpoint(
    commodity_id: str = Query(..., description="Target commodity ID"),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Groups commodity prices by geographic region and computes regional variance.
    """
    return get_regional_price_differences(
        current_user.defaultOrgId,
        commodity_id
    )


@router.get("/analysis/supply-demand")
async def get_supply_demand_endpoint(
    commodity_id: str = Query(..., description="Target commodity ID"),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieves grounded qualitative supply and demand observations.
    Never synthesizes ungrounded volume numbers.
    """
    return get_supply_and_demand_intelligence(
        current_user.defaultOrgId,
        commodity_id
    )


# ── 6. AgroTrack Farm Integration ────────────────────────────────────────────

@router.get("/farms/{farm_id}/market-intelligence")
async def get_farm_market_intel_endpoint(
    farm_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Connects relevant MarketLens price intelligence to an AgroTrack farm record.
    Explicitly communicates that farm production does not automatically equal market supply.
    """
    return get_farm_market_intelligence(current_user.defaultOrgId, farm_id)
