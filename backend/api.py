"""
AgroTrack AI Core API Routes (v1)
Provides platform overview, organisation management, membership, role validation, and module status.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from datetime import datetime
from .models import (
    Role,
    Permission,
    ROLE_PERMISSIONS,
    UserProfile,
    Organisation,
    OrganisationMember,
    ProjectSummary,
    PlatformMetrics,
    ModuleStatus,
    PlatformOverview
)
from .security import get_current_user, require_roles, require_permission, ENVIRONMENT, ALLOW_DEV_MOCK_AUTH
from backend.db.database import get_record, list_records, save_record, init_db, seed_default_data

init_db()
seed_default_data()

router = APIRouter(prefix="/api/v1", tags=["AgroTrack AI Platform"])

@router.get("/config")
async def get_client_config():
    """Returns client runtime configuration and security mode flags."""
    return {
        "environment": ENVIRONMENT,
        "allowDevMockAuth": ALLOW_DEV_MOCK_AUTH,
        "version": "1.0.0",
        "platform": "AgroFast"
    }

# ── In-Memory Default Data (Non-destructive, demo/default organisation) ───────
CURRENT_ORG = Organisation(
    id="org_greenvalley_01",
    name="GreenValley AgTech Cooperative",
    code="GV-AGTECH",
    tier="enterprise",
    country="Kenya",
    currency="KES",
    createdAt="2026-01-15T08:00:00Z"
)

DEFAULT_MEMBERS: List[OrganisationMember] = [
    OrganisationMember(
        userId="usr_admin_001",
        name="Sarah Mwangi",
        email="sarah.mwangi@agrotrack.ai",
        role=Role.ORGANISATION_ADMIN,
        status="active",
        joinedAt="2026-01-15T08:00:00Z"
    ),
    OrganisationMember(
        userId="usr_mgr_002",
        name="David Kiprop",
        email="david.kiprop@agrotrack.ai",
        role=Role.PROJECT_MANAGER,
        status="active",
        joinedAt="2026-02-01T09:30:00Z"
    ),
    OrganisationMember(
        userId="usr_field_003",
        name="Amina Otieno",
        email="amina.otieno@agrotrack.ai",
        role=Role.FIELD_OFFICER,
        status="active",
        joinedAt="2026-02-15T10:00:00Z"
    ),
    OrganisationMember(
        userId="usr_analyst_004",
        name="Brian Njoroge",
        email="brian.njoroge@agrotrack.ai",
        role=Role.ANALYST,
        status="active",
        joinedAt="2026-03-01T11:15:00Z"
    ),
    OrganisationMember(
        userId="usr_viewer_005",
        name="Grace Wanjiku",
        email="grace.wanjiku@agrotrack.ai",
        role=Role.VIEWER,
        status="active",
        joinedAt="2026-04-10T14:00:00Z"
    )
]

DEFAULT_PROJECTS: List[ProjectSummary] = [
    ProjectSummary(
        id="proj_smcri_2026",
        name="Smallholder Maize Climate Resilience Initiative",
        code="SMCRI-2026",
        status="Active",
        targetBeneficiaries=1200,
        enrolledFarmers=840,
        budget=4500000.0,
        currency="KES"
    ),
    ProjectSummary(
        id="proj_horticulture_export_2026",
        name="High-Value Avocado & Pepper Value Chain Grant",
        code="HV-AVO-26",
        status="Active",
        targetBeneficiaries=650,
        enrolledFarmers=512,
        budget=6200000.0,
        currency="KES"
    ),
    ProjectSummary(
        id="proj_soil_health_subcounty",
        name="Sub-County Soil Acidity & NPK Rehabilitation",
        code="SOIL-REHAB",
        status="Planning",
        targetBeneficiaries=400,
        enrolledFarmers=120,
        budget=2100000.0,
        currency="KES"
    )
]

MODULE_REGISTRY: List[ModuleStatus] = [
    ModuleStatus(
        id="agrotrack",
        name="AgroTrack",
        description="Farmer, farm, field, plot, soil nutrient, and AI crop disease scanner.",
        status="active",
        phase="Phase 1-2 (Active Foundation)",
        icon="fa-seedling",
        route="track.html"
    ),
    ModuleStatus(
        id="marketlens",
        name="MarketLens",
        description="Agricultural market research, commodity pricing trends, and value-chain intelligence.",
        status="operational",
        phase="Phase 4 (Operational)",
        icon="fa-chart-line",
        route="marketlens.html"
    ),
    ModuleStatus(
        id="impactos",
        name="ImpactOS",
        description="Project management, donor indicator tracking, beneficiaries, and impact reporting.",
        status="operational",
        phase="Phase 5 (Operational)",
        icon="fa-hands-holding-circle",
        route="impactos.html"
    ),
    ModuleStatus(
        id="analyst",
        name="AI Analyst",
        description="Cross-platform agronomic intelligence layer bridging farm plots, market trends, and impact.",
        status="operational",
        phase="Phase 6 (Operational)",
        icon="fa-brain",
        route="analyst.html"
    )
]

RECENT_ACTIVITY: List[Dict[str, Any]] = [
    {
        "id": "act_01",
        "title": "Maize Diagnostic Scan Complete",
        "detail": "Field Officer Amina scanned plot 'Solai North Plot 2' (Early Blight detected, 94.2% confidence).",
        "timestamp": "25 mins ago",
        "icon": "fa-camera",
        "type": "agrotrack"
    },
    {
        "id": "act_02",
        "title": "New Farmer Enrolled",
        "detail": "Joseph Kamau enrolled into Smallholder Maize Initiative (3.5 acres, Nakuru).",
        "timestamp": "2 hours ago",
        "icon": "fa-user-plus",
        "type": "impactos"
    },
    {
        "id": "act_03",
        "title": "NPK Nutrient Update",
        "detail": "Soil NPK updated for 'Njoro Commercial Farm' (N: 48%, P: 32%, K: 28%).",
        "timestamp": "4 hours ago",
        "icon": "fa-flask-vial",
        "type": "agrotrack"
    },
    {
        "id": "act_04",
        "title": "Commodity Alert: Maize KES 4,500/bag",
        "detail": "Nairobi Wholesale Grain Market prices increased by 4.2% week-on-week.",
        "timestamp": "6 hours ago",
        "icon": "fa-arrow-trend-up",
        "type": "marketlens"
    }
]


# ── Auth & Identity Endpoints ──────────────────────────────────────────────────

@router.get("/auth/me", response_model=UserProfile)
async def get_my_profile(current_user: UserProfile = Depends(get_current_user)):
    """Returns the authenticated user's profile, role, and granted permissions."""
    return current_user


@router.get("/auth/roles")
async def list_roles():
    """Lists all available platform roles and their corresponding permissions."""
    return {
        "roles": [
            {
                "role": r.value,
                "permissions": [p.value for p in perms]
            }
            for r, perms in ROLE_PERMISSIONS.items()
        ]
    }


# ── Organisation & Memberships ────────────────────────────────────────────────

@router.get("/organisations/current", response_model=Organisation)
async def get_current_organisation(current_user: UserProfile = Depends(get_current_user)):
    """Returns current active organisation details from persistent store."""
    org_doc = get_record("organisations", current_user.defaultOrgId)
    if org_doc:
        return Organisation(
            id=org_doc["id"],
            name=org_doc.get("name", "Organisation"),
            code=org_doc.get("code", "ORG"),
            tier=org_doc.get("tier", "enterprise"),
            country=org_doc.get("country", "Kenya"),
            currency=org_doc.get("currency", "KES"),
            createdAt=org_doc.get("createdAt", "2026-01-15T08:00:00Z")
        )
    return CURRENT_ORG


@router.get("/organisations/members", response_model=List[OrganisationMember])
async def list_organisation_members(
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER]))
):
    """
    Lists members of the current organisation from persistent store.
    Enforces Role Check: Organisation Administrator or Project Manager only.
    """
    members = list_records("organisation_members", org_id=current_user.defaultOrgId)
    if members:
        return [
            OrganisationMember(
                userId=m.get("userId", m.get("id")),
                name=m.get("name", "Member"),
                email=m.get("email", ""),
                role=m.get("role", "Viewer"),
                status=m.get("status", "active"),
                joinedAt=m.get("joinedAt", m.get("createdAt", ""))
            )
            for m in members
        ]
    return DEFAULT_MEMBERS


class AddMemberRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    role: Role


@router.post("/organisations/members", response_model=OrganisationMember, status_code=status.HTTP_201_CREATED)
async def add_organisation_member(
    request: AddMemberRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN]))
):
    """
    Invites/adds a member to the organisation and persists to SQLite.
    Enforces Strict Role Check: Organisation Administrator ONLY.
    """
    existing = list_records("organisation_members", org_id=current_user.defaultOrgId)
    uid = f"usr_new_{len(existing) + 1:03d}"
    joined_now = datetime.utcnow().isoformat() + "Z"
    
    role_str = request.role.value if hasattr(request.role, "value") else str(request.role)
    doc = {
        "id": uid,
        "orgId": current_user.defaultOrgId,
        "userId": uid,
        "name": request.name,
        "email": request.email,
        "role": role_str,
        "status": "active",
        "joinedAt": joined_now,
        "createdAt": joined_now
    }
    save_record("organisation_members", doc, org_id=current_user.defaultOrgId)

    new_member = OrganisationMember(
        userId=uid,
        name=request.name,
        email=request.email,
        role=request.role,
        status="active",
        joinedAt=joined_now
    )
    DEFAULT_MEMBERS.append(new_member)
    return new_member


# ── Platform Overview & Dashboard ─────────────────────────────────────────────

@router.get("/platform/overview", response_model=PlatformOverview)
async def get_platform_overview(current_user: UserProfile = Depends(get_current_user)):
    """
    Delivers executive overview metrics, module status, projects, and recent activity.
    Accessible to all authenticated roles.
    """
    try:
        from backend.agrotrack.service import get_agrotrack_dashboard_stats, get_scans_for_org
        from backend.impactos.service import TENANT_PROJECTS
        stats = get_agrotrack_dashboard_stats(current_user.defaultOrgId)
        scans = get_scans_for_org(current_user.defaultOrgId)
        impact_projects = TENANT_PROJECTS.get(current_user.defaultOrgId, [])
        active_proj_count = len([p for p in impact_projects if p.get("status") in ["active", "Active"] and not p.get("isArchived", False)]) or len(DEFAULT_PROJECTS)
        metrics = PlatformMetrics(
            activeFarms=stats["totalFarms"] if stats["totalFarms"] > 0 else 48,
            monitoredAcreage=stats["totalAcreage"] if stats["totalAcreage"] > 0 else 326.5,
            registeredFarmers=stats["activeFarmers"] if stats["activeFarmers"] > 0 else 1472,
            diagnosticScans=len(scans) if len(scans) > 0 else 894,
            activeProjects=active_proj_count
        )
    except Exception:
        metrics = PlatformMetrics(
            activeFarms=48,
            monitoredAcreage=326.5,
            registeredFarmers=1472,
            diagnosticScans=894,
            activeProjects=len(DEFAULT_PROJECTS)
        )

    return PlatformOverview(
        organisation=CURRENT_ORG,
        user=current_user,
        metrics=metrics,
        modules=MODULE_REGISTRY,
        projects=DEFAULT_PROJECTS,
        recentActivity=RECENT_ACTIVITY
    )


@router.get("/modules/status", response_model=List[ModuleStatus])
async def get_modules_status(current_user: UserProfile = Depends(get_current_user)):
    """Returns the operational status of the 4 platform modules."""
    return MODULE_REGISTRY


# ── Protected Operation Endpoints (Role Enforcement Testing) ──────────────────

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=3)
    code: str = Field(..., min_length=2)
    targetBeneficiaries: int = Field(..., ge=1)
    budget: float = Field(..., ge=0)


@router.post("/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    request: CreateProjectRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER]))
):
    """
    Creates a new development project.
    Allowed Roles: Organisation Administrator, Project Manager.
    Denied (403): Field Officer, Analyst, Viewer.
    """
    project = ProjectSummary(
        id=f"proj_{request.code.lower()}_{len(DEFAULT_PROJECTS) + 1}",
        name=request.name,
        code=request.code,
        status="Active",
        targetBeneficiaries=request.targetBeneficiaries,
        enrolledFarmers=0,
        budget=request.budget,
        currency="KES"
    )
    DEFAULT_PROJECTS.append(project)
    return {"message": "Project created successfully", "project": project}


class CreateFarmerRequest(BaseModel):
    firstName: str
    lastName: str
    phone: str
    county: str
    acreage: float


@router.post("/farmers", status_code=status.HTTP_201_CREATED)
async def register_farmer(
    request: CreateFarmerRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER]))
):
    """
    Registers a farmer in the field.
    Allowed Roles: Organisation Administrator, Project Manager, Field Officer.
    Denied (403): Analyst, Viewer.
    """
    return {
        "message": "Farmer registered successfully",
        "farmerId": f"frmr_{len(DEFAULT_PROJECTS) * 100 + 42}",
        "registeredBy": current_user.name,
        "assignedRole": current_user.activeRole.value
    }


@router.get("/reports/export")
async def export_impact_report(
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.ANALYST]))
):
    """
    Exports quantitative impact report.
    Allowed Roles: Organisation Administrator, Project Manager, Analyst.
    Denied (403): Field Officer, Viewer.
    """
    return {
        "reportId": "rep_mne_q3_2026",
        "generatedBy": current_user.email,
        "generatedRole": current_user.activeRole.value,
        "summary": "Impact and M&E metrics successfully compiled for donor reporting."
    }
