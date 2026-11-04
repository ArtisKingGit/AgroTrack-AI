"""
AgroTrack API Router (v1)
Endpoints for crop diagnosis, image quality validation, farm health scoring,
environmental disease risk, irrigation advisory, fertilizer balancing,
crop calendar, profitability simulation, and organisation-scoped farm CRUD.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from pydantic import BaseModel, Field

from backend.models import (
    Role,
    UserProfile,
    FarmerCreateRequest,
    FarmerUpdateRequest,
    FieldActivityCreateRequest,
    OfflineActivitySyncItem,
    OfflineSyncBatchRequest,
    OfflineSyncResponse,
    AgroTrackDashboardStats,
)
from backend.security import get_current_user, require_roles
from backend.ai.classifier import predict_crop
from backend.ai.detector import detect_disease
from backend.agrotrack.quality import validate_image_quality, is_valid_image_header
from backend.agrotrack.service import (
    calculate_farm_health_score,
    predict_disease_risk,
    calculate_irrigation_advice,
    calculate_fertilizer_advice,
    calculate_crop_calendar,
    simulate_crop_profitability,
    get_farms_for_org,
    get_farm_by_id,
    create_farm,
    update_farm,
    delete_farm,
    get_expenses_for_org,
    create_expense,
    delete_expense,
    get_scans_for_org,
    get_farmers_for_org,
    get_farmer_by_id,
    get_farmer_profile,
    create_farmer,
    update_farmer,
    archive_farmer,
    restore_farmer,
    get_activities_for_org,
    get_activity_by_id,
    create_activity,
    sync_offline_activities,
    get_farm_history,
    get_field_officer_assignments,
    get_agrotrack_dashboard_stats,
)

router = APIRouter(prefix="/api/v1/agrotrack", tags=["AgroTrack Agricultural Intelligence"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


# ── Request / Response Schemas ────────────────────────────────────────────────

class DiseaseRiskRequest(BaseModel):
    crop: str = Field(..., json_schema_extra={"example": "Maize"})
    temperature: float = Field(..., json_schema_extra={"example": 22.5})
    humidity: float = Field(..., json_schema_extra={"example": 82.0})
    precipitation: float = Field(0.0, json_schema_extra={"example": 6.5})


class IrrigationAdviceRequest(BaseModel):
    crop: str = Field(..., json_schema_extra={"example": "Tomato"})
    soil_type: str = Field(..., json_schema_extra={"example": "Loamy"})
    temperature: float = Field(..., json_schema_extra={"example": 27.0})
    humidity: float = Field(..., json_schema_extra={"example": 55.0})
    precipitation_24h: float = Field(0.0, json_schema_extra={"example": 2.0})
    irrigation_type: str = Field("Drip", json_schema_extra={"example": "Drip"})


class FertilizerAdviceRequest(BaseModel):
    crop: str = Field(..., json_schema_extra={"example": "Maize"})
    n_percent: float = Field(..., ge=0, le=100, json_schema_extra={"example": 35.0})
    p_percent: float = Field(..., ge=0, le=100, json_schema_extra={"example": 25.0})
    k_percent: float = Field(..., ge=0, le=100, json_schema_extra={"example": 30.0})
    ph: float = Field(6.5, ge=3.0, le=10.0, json_schema_extra={"example": 6.2})


class CropCalendarRequest(BaseModel):
    crop: str = Field(..., json_schema_extra={"example": "Maize"})
    planting_date: str = Field(..., json_schema_extra={"example": "2026-03-15"})


class ProfitabilityRequest(BaseModel):
    crop: str = Field(..., json_schema_extra={"example": "Tomato"})
    acreage: float = Field(..., gt=0, json_schema_extra={"example": 2.0})
    expected_yield_multiplier: float = Field(1.0, gt=0, json_schema_extra={"example": 1.0})
    market_price_per_kg: Optional[float] = Field(None, json_schema_extra={"example": 60.0})
    currency: str = Field("KES", json_schema_extra={"example": "KES"})


class FarmCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, json_schema_extra={"example": "North Field"})
    farmerId: Optional[str] = Field(None, json_schema_extra={"example": "frmr_982103"})
    size: float = Field(..., gt=0, json_schema_extra={"example": 3.5})
    unit: str = Field("acres", json_schema_extra={"example": "acres"})
    crop: str = Field(..., json_schema_extra={"example": "Maize"})
    soil: str = Field("Loamy", json_schema_extra={"example": "Loamy"})
    irrigation: str = Field("Drip", json_schema_extra={"example": "Drip"})
    waterSource: str = Field("Borehole", json_schema_extra={"example": "Borehole"})
    status: str = Field("Growing", json_schema_extra={"example": "Growing"})
    budget: float = Field(50000.0, ge=0, json_schema_extra={"example": 75000.0})
    plantingDate: Optional[str] = None
    soilNutrients: Optional[Dict[str, float]] = Field(default_factory=lambda: {"n": 45.0, "p": 30.0, "k": 25.0})
    location: Optional[Dict[str, Any]] = None


class FarmUpdateRequest(BaseModel):
    name: Optional[str] = None
    crop: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[float] = None
    soilNutrients: Optional[Dict[str, float]] = None


class ExpenseCreateRequest(BaseModel):
    farmId: str = Field(..., json_schema_extra={"example": "farm_gv_101"})
    category: str = Field(..., json_schema_extra={"example": "Fertilizer"})
    amount: float = Field(..., gt=0, json_schema_extra={"example": 15000.0})
    date: Optional[str] = None
    note: Optional[str] = ""


# ── 1. Diagnostic Leaf & Quality Endpoints ─────────────────────────────────────

@router.post("/quality-check")
async def quality_check_endpoint(image: UploadFile = File(...)):
    """
    Evaluates image quality metrics (resolution, brightness, blurriness/sharpness).
    Can be called standalone before full diagnostic inference.
    """
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Please upload a JPEG, PNG, or WEBP image."
        )

    image_bytes = await image.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image is too large. Maximum size is 10MB."
        )

    return validate_image_quality(image_bytes)


@router.post("/diagnose")
async def diagnose_leaf_endpoint(
    image: UploadFile = File(...),
    farm_id: Optional[str] = Form(None),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Comprehensive diagnostic pipeline:
    1. Validates image quality & resolution.
    2. Runs MobileNetV2 CNN crop disease classification.
    3. Runs PlantCV spot localization and calculates disease severity percentage.
    4. Attaches treatments and soil balancing advice.
    """
    if image.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Please upload a JPEG, PNG, or WEBP image."
        )

    image_bytes = await image.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image is too large. Maximum size is 10MB."
        )

    # Step 1: Quality Check
    quality = validate_image_quality(image_bytes)
    if not quality["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image quality check failed: {', '.join(quality['warnings'])}"
        )

    try:
        # Step 2: Crop disease classification
        result = predict_crop(image_bytes)

        # Step 3: Spot localization & severity analysis
        detection = detect_disease(image_bytes, result)

        result["boxes"] = detection.get("boxes", [])
        result["severity_percentage"] = detection.get("severity_percentage", 0.0)
        result["severity_level"] = detection.get("severity_level", "None (Healthy)")
        result["quality_assessment"] = {
            "status": quality["quality_status"],
            "sharpness": quality["sharpness"],
            "brightness": quality["brightness"]
        }
        result["scanned_by"] = current_user.name
        result["organisation_id"] = current_user.defaultOrgId

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not complete crop diagnosis. Please try another clear leaf photograph."
        )


# ── 2. Agricultural Intelligence Endpoints ────────────────────────────────────

@router.post("/disease-risk")
async def disease_risk_endpoint(
    req: DiseaseRiskRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """Predicts environmental crop disease and pest pressure from weather parameters."""
    return predict_disease_risk(
        temperature=req.temperature,
        humidity=req.humidity,
        precipitation=req.precipitation,
        crop=req.crop
    )


@router.post("/irrigation-advice")
async def irrigation_advice_endpoint(
    req: IrrigationAdviceRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """Calculates smart irrigation necessity, volume, and time window."""
    return calculate_irrigation_advice(
        crop=req.crop,
        soil_type=req.soil_type,
        temperature=req.temperature,
        humidity=req.humidity,
        precipitation_24h=req.precipitation_24h,
        irrigation_type=req.irrigation_type
    )


@router.post("/fertilizer-advice")
async def fertilizer_advice_endpoint(
    req: FertilizerAdviceRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """Calculates soil nutrient deficits and prescribes exact fertilizer treatments."""
    return calculate_fertilizer_advice(
        crop=req.crop,
        n_percent=req.n_percent,
        p_percent=req.p_percent,
        k_percent=req.k_percent,
        ph=req.ph
    )


@router.post("/crop-calendar")
async def crop_calendar_endpoint(
    req: CropCalendarRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """Computes growth stages, days elapsed, days to harvest, and upcoming milestones."""
    return calculate_crop_calendar(
        crop=req.crop,
        planting_date_str=req.planting_date
    )


@router.post("/profitability-simulation")
async def profitability_simulation_endpoint(
    req: ProfitabilityRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """Simulates expected harvest yield, production costs, gross revenue, and net ROI."""
    return simulate_crop_profitability(
        crop=req.crop,
        acreage=req.acreage,
        expected_yield_multiplier=req.expected_yield_multiplier,
        market_price_per_kg=req.market_price_per_kg,
        currency=req.currency
    )


@router.get("/farms/{farm_id}/health")
async def farm_health_endpoint(
    farm_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Calculates overall 0-100 farm health score, grade, and action items.
    Enforces organisation isolation.
    """
    farm = get_farm_by_id(current_user.defaultOrgId, farm_id)
    recent_scans = get_scans_for_org(current_user.defaultOrgId, farm_id=farm_id)
    return calculate_farm_health_score(farm, recent_scans)


# ── 3. Organisation-Scoped Farm & Expense CRUD (Tenant Isolation) ─────────────

@router.get("/farms")
async def list_farms_endpoint(
    farmer_id: Optional[str] = Query(None),
    crop: Optional[str] = Query(None),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Lists farms belonging strictly to the authenticated user's organisation.
    Enforces tenant isolation with optional farmer_id and crop filtering.
    """
    return get_farms_for_org(current_user.defaultOrgId, farmer_id=farmer_id, crop=crop)


@router.post("/farms", status_code=status.HTTP_201_CREATED)
async def create_farm_endpoint(
    farm_data: FarmCreateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER]))
):
    """
    Creates a new farm in the authenticated user's organisation with GPS validation and farmer linkage.
    Restricted to Admin, PM, and Field Officer roles.
    """
    return create_farm(current_user.defaultOrgId, farm_data.model_dump())


@router.get("/farms/{farm_id}")
async def get_farm_endpoint(
    farm_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Gets farm details.
    Prevents cross-organisation access (returns 403 if belonging to another org).
    """
    return get_farm_by_id(current_user.defaultOrgId, farm_id)


@router.get("/farms/{farm_id}/history")
async def get_farm_history_endpoint(
    farm_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieves chronological history of field activities, AI leaf scans, and expenses.
    """
    return get_farm_history(current_user.defaultOrgId, farm_id)


@router.put("/farms/{farm_id}")
async def update_farm_endpoint(
    farm_id: str,
    updates: FarmUpdateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER]))
):
    """Updates farm details or soil nutrients with GPS boundary validation."""
    clean_updates = {k: v for k, v in updates.model_dump().items() if v is not None}
    return update_farm(current_user.defaultOrgId, farm_id, clean_updates)


@router.delete("/farms/{farm_id}")
async def delete_farm_endpoint(
    farm_id: str,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER]))
):
    """Deletes farm and cascades to associated expenses and activities to prevent orphans."""
    return delete_farm(current_user.defaultOrgId, farm_id)


# ── 4. Farmer Management Endpoints ───────────────────────────────────────────

@router.get("/farmers")
async def list_farmers_endpoint(
    search: Optional[str] = Query(None, description="Search by name, national ID, code, or contact"),
    project_id: Optional[str] = Query(None, description="Filter by enrolled project"),
    field_officer_id: Optional[str] = Query(None, description="Filter by assigned field officer"),
    status: str = Query("active", description="Status filter: 'active', 'archived', or 'all'"),
    crop: Optional[str] = Query(None, description="Filter by crop grown on any of their plots"),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Lists farmers belonging to the authenticated organisation with multi-factor search and filtering.
    """
    return get_farmers_for_org(
        current_user.defaultOrgId,
        search=search,
        project_id=project_id,
        field_officer_id=field_officer_id,
        status_filter=status,
        crop=crop
    )


@router.post("/farmers", status_code=status.HTTP_201_CREATED)
async def create_farmer_endpoint(
    farmer_data: FarmerCreateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER]))
):
    """
    Creates a new farmer record.
    Restricted to Admin, PM, and Field Officer roles.
    Enforces unique nationalId and validates GPS coordinates.
    """
    return create_farmer(current_user.defaultOrgId, farmer_data.model_dump(), current_user=current_user)


@router.get("/farmers/{farmer_id}")
async def get_farmer_endpoint(
    farmer_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieves a single farmer record.
    Prevents cross-organisation access with HTTP 403 Forbidden.
    """
    return get_farmer_by_id(current_user.defaultOrgId, farmer_id)


@router.get("/farmers/{farmer_id}/profile")
async def get_farmer_profile_endpoint(
    farmer_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieves complete farmer profile including owned plots, historical field activities,
    diagnostic leaf scans, and aggregated crop metrics.
    """
    return get_farmer_profile(current_user.defaultOrgId, farmer_id)


@router.put("/farmers/{farmer_id}")
async def update_farmer_endpoint(
    farmer_id: str,
    updates: FarmerUpdateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER]))
):
    """
    Updates farmer record with national ID duplicate checking and GPS validation.
    """
    clean_updates = {k: v for k, v in updates.model_dump().items() if v is not None}
    return update_farmer(current_user.defaultOrgId, farmer_id, clean_updates)


@router.post("/farmers/{farmer_id}/archive")
async def archive_farmer_endpoint(
    farmer_id: str,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER]))
):
    """
    Soft-archives a farmer record without permanently deleting historical data.
    """
    return archive_farmer(current_user.defaultOrgId, farmer_id)


@router.post("/farmers/{farmer_id}/restore")
async def restore_farmer_endpoint(
    farmer_id: str,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER]))
):
    """
    Restores an archived farmer record to active status.
    """
    return restore_farmer(current_user.defaultOrgId, farmer_id)


# ── 5. Field Activities Endpoints ────────────────────────────────────────────

@router.get("/activities")
async def list_activities_endpoint(
    farm_id: Optional[str] = Query(None),
    farmer_id: Optional[str] = Query(None),
    activity_type: Optional[str] = Query(None),
    responsible_user_id: Optional[str] = Query(None),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Lists field activities (farm visits, crop inspections, planting, harvest, irrigation, fertilizer)
    scoped to the user's organisation with optional filters.
    """
    return get_activities_for_org(
        current_user.defaultOrgId,
        farm_id=farm_id,
        farmer_id=farmer_id,
        activity_type=activity_type,
        responsible_user_id=responsible_user_id
    )


@router.post("/activities", status_code=status.HTTP_201_CREATED)
async def create_activity_endpoint(
    act_data: FieldActivityCreateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER]))
):
    """
    Logs a new field activity for a farm plot.
    Restricted to Admin, PM, and Field Officer roles.
    """
    return create_activity(current_user.defaultOrgId, act_data.model_dump(), current_user=current_user)


@router.get("/activities/{activity_id}")
async def get_activity_endpoint(
    activity_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieves details of a specific field activity with cross-organisation access restriction.
    """
    return get_activity_by_id(current_user.defaultOrgId, activity_id)


@router.post("/activities/sync", response_model=OfflineSyncResponse)
async def sync_activities_endpoint(
    request: OfflineSyncBatchRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER]))
):
    """
    Safely synchronizes an offline batch of field activities captured by field officers.
    Guarantees:
    - Idempotency via clientMutationId (never duplicate records upon network retry).
    - Conflict detection: flags if target farm plot does not exist or was deleted.
    - Preserves field officer offline timestamps (clientCreatedAt).
    - Prevents silent data loss or overwrites.
    """
    return sync_offline_activities(
        current_user.defaultOrgId,
        [item.model_dump() for item in request.batch],
        current_user=current_user
    )


# ── 6. Field Officer Workflows ───────────────────────────────────────────────

@router.get("/field-officer/assignments")
async def get_my_assignments_endpoint(current_user: UserProfile = Depends(get_current_user)):
    """
    Retrieves assigned farmers, farm plots, and managed acreage for the authenticated user.
    """
    return get_field_officer_assignments(current_user.defaultOrgId, current_user.uid)


# ── 7. AgroTrack Live Dashboard Statistics ────────────────────────────────────

@router.get("/dashboard/stats", response_model=AgroTrackDashboardStats)
async def get_dashboard_stats_endpoint(current_user: UserProfile = Depends(get_current_user)):
    """
    Computes real-time statistics across registered farmers, farms, activities, and crops
    strictly from live database records.
    """
    return get_agrotrack_dashboard_stats(current_user.defaultOrgId)


# ── 8. Expenses & Scans Archive ──────────────────────────────────────────────


@router.get("/expenses")
async def list_expenses_endpoint(
    farm_id: Optional[str] = None,
    current_user: UserProfile = Depends(get_current_user)
):
    """Lists expenses scoped to the user's organisation."""
    return get_expenses_for_org(current_user.defaultOrgId, farm_id=farm_id)


@router.post("/expenses", status_code=status.HTTP_201_CREATED)
async def create_expense_endpoint(
    exp_data: ExpenseCreateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER]))
):
    """Records an expense for a farm within the organisation."""
    return create_expense(current_user.defaultOrgId, exp_data.model_dump())


@router.delete("/expenses/{expense_id}")
async def delete_expense_endpoint(
    expense_id: str,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER]))
):
    """Deletes an expense record scoped to the organisation."""
    return delete_expense(current_user.defaultOrgId, expense_id)


@router.get("/scans")
async def list_scans_endpoint(
    farm_id: Optional[str] = None,
    current_user: UserProfile = Depends(get_current_user)
):
    """Retrieves diagnostic scan archive scoped to the organisation."""
    return get_scans_for_org(current_user.defaultOrgId, farm_id=farm_id)
