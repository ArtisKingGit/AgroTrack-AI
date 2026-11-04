"""
AgroTrack AI — ImpactOS API Router
Exposes endpoints for project management, beneficiary rosters, indicator tracking,
field activities, M&E dashboard statistics, and auditable donor report generation.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from backend.models import (
    Role,
    UserProfile,
    Project,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    Beneficiary,
    BeneficiaryCreateRequest,
    BeneficiaryUpdateRequest,
    Indicator,
    IndicatorCreateRequest,
    IndicatorUpdateRequest,
    IndicatorProgressRecordRequest,
    ImpactActivity,
    ImpactActivityCreateRequest,
    ImpactActivityUpdateRequest,
    ReportGenerateRequest,
    ImpactReport,
    ImpactOSDashboardStats,
)
from backend.security import get_current_user, require_roles
from backend.impactos import service

router = APIRouter(prefix="/api/v1/impactos", tags=["ImpactOS"])


# ── Projects Endpoints ───────────────────────────────────────────────────────

@router.get("/projects", response_model=List[Project])
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by status (active, planning, paused, completed, archived)"),
    search: Optional[str] = Query(None, description="Search across name, code, donor, and description"),
    include_archived: bool = Query(False, description="Whether to include archived projects"),
    current_user: UserProfile = Depends(get_current_user),
):
    """Lists all development projects belonging to the authenticated organisation."""
    return service.list_projects(
        org_id=current_user.defaultOrgId,
        status_filter=status,
        search=search,
        include_archived=include_archived,
    )


@router.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER])),
):
    """
    Creates a new development project.
    Allowed Roles: Organisation Administrator, Project Manager.
    Denied (403): Field Officer, Analyst, Viewer.
    """
    return service.create_project(
        org_id=current_user.defaultOrgId,
        req=request,
        user=current_user,
    )


@router.get("/projects/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    current_user: UserProfile = Depends(get_current_user),
):
    """Retrieves project details by ID."""
    return service.get_project(
        org_id=current_user.defaultOrgId,
        project_id=project_id,
    )


@router.put("/projects/{project_id}", response_model=Project)
async def update_project(
    project_id: str,
    request: ProjectUpdateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER])),
):
    """Updates an existing project record."""
    return service.update_project(
        org_id=current_user.defaultOrgId,
        project_id=project_id,
        req=request,
        user=current_user,
    )


@router.post("/projects/{project_id}/archive")
async def archive_project(
    project_id: str,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER])),
):
    """Soft archives a project without deleting historical beneficiary or activity logs."""
    return service.archive_project(
        org_id=current_user.defaultOrgId,
        project_id=project_id,
        user=current_user,
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER])),
):
    """Deletes a project from the registry."""
    return service.delete_project(
        org_id=current_user.defaultOrgId,
        project_id=project_id,
        user=current_user,
    )


# ── Beneficiaries Endpoints ──────────────────────────────────────────────────

@router.get("/beneficiaries", response_model=List[Beneficiary])
async def list_beneficiaries(
    projectId: Optional[str] = Query(None, description="Filter by enrolled project"),
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by name, code, or location"),
    current_user: UserProfile = Depends(get_current_user),
):
    """
    Lists beneficiaries scoped to the organisation.
    Enforces PII protection: Viewer role receives masked phone and national ID.
    """
    return service.list_beneficiaries(
        org_id=current_user.defaultOrgId,
        project_id=projectId,
        category=category,
        search=search,
        user_role=current_user.activeRole,
    )


@router.post("/beneficiaries", response_model=Beneficiary, status_code=status.HTTP_201_CREATED)
async def create_beneficiary(
    request: BeneficiaryCreateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER])),
):
    """
    Enrolls a new beneficiary.
    Allowed Roles: Organisation Administrator, Project Manager, Field Officer.
    Denied (403): Analyst, Viewer.
    """
    return service.create_beneficiary(
        org_id=current_user.defaultOrgId,
        req=request,
        user=current_user,
    )


@router.get("/beneficiaries/{beneficiary_id}", response_model=Beneficiary)
async def get_beneficiary(
    beneficiary_id: str,
    current_user: UserProfile = Depends(get_current_user),
):
    """Retrieves a single beneficiary with PII protection for viewers."""
    return service.get_beneficiary(
        org_id=current_user.defaultOrgId,
        beneficiary_id=beneficiary_id,
        user_role=current_user.activeRole,
    )


@router.put("/beneficiaries/{beneficiary_id}", response_model=Beneficiary)
async def update_beneficiary(
    beneficiary_id: str,
    request: BeneficiaryUpdateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER])),
):
    """Updates beneficiary demographics or status."""
    return service.update_beneficiary(
        org_id=current_user.defaultOrgId,
        beneficiary_id=beneficiary_id,
        req=request,
        user=current_user,
    )


@router.delete("/beneficiaries/{beneficiary_id}")
async def delete_beneficiary(
    beneficiary_id: str,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER])),
):
    """Removes a beneficiary from the organisation roster."""
    return service.delete_beneficiary(
        org_id=current_user.defaultOrgId,
        beneficiary_id=beneficiary_id,
        user=current_user,
    )


# ── Indicators Endpoints ─────────────────────────────────────────────────────

@router.get("/indicators", response_model=List[Indicator])
async def list_indicators(
    projectId: Optional[str] = Query(None, description="Filter by project ID"),
    category: Optional[str] = Query(None, description="Filter by category (output, outcome, impact)"),
    current_user: UserProfile = Depends(get_current_user),
):
    """Lists M&E performance indicators for the organisation."""
    return service.list_indicators(
        org_id=current_user.defaultOrgId,
        project_id=projectId,
        category=category,
    )


@router.post("/indicators", response_model=Indicator, status_code=status.HTTP_201_CREATED)
async def create_indicator(
    request: IndicatorCreateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER])),
):
    """
    Defines a new performance indicator with baseline and target.
    Allowed Roles: Organisation Administrator, Project Manager.
    Denied (403): Field Officer, Analyst, Viewer.
    """
    return service.create_indicator(
        org_id=current_user.defaultOrgId,
        req=request,
        user=current_user,
    )


@router.get("/indicators/{indicator_id}", response_model=Indicator)
async def get_indicator(
    indicator_id: str,
    current_user: UserProfile = Depends(get_current_user),
):
    """Retrieves indicator details by ID."""
    return service.get_indicator(
        org_id=current_user.defaultOrgId,
        indicator_id=indicator_id,
    )


@router.put("/indicators/{indicator_id}", response_model=Indicator)
async def update_indicator(
    indicator_id: str,
    request: IndicatorUpdateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER])),
):
    """Updates indicator target value or reporting frequency."""
    return service.update_indicator(
        org_id=current_user.defaultOrgId,
        indicator_id=indicator_id,
        req=request,
        user=current_user,
    )


@router.post("/indicators/{indicator_id}/progress")
async def record_indicator_progress(
    indicator_id: str,
    request: IndicatorProgressRecordRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER, Role.ANALYST])),
):
    """
    Records an auditable measurement update for an indicator.
    Allowed Roles: Organisation Administrator, Project Manager, Field Officer, Analyst.
    Denied (403): Viewer.
    """
    return service.record_indicator_progress(
        org_id=current_user.defaultOrgId,
        indicator_id=indicator_id,
        req=request,
        user=current_user,
    )


# ── Field Activities Endpoints ───────────────────────────────────────────────

@router.get("/activities", response_model=List[ImpactActivity])
async def list_activities(
    projectId: Optional[str] = Query(None, description="Filter by project ID"),
    activityType: Optional[str] = Query(None, description="Filter by activity type"),
    search: Optional[str] = Query(None, description="Search by title, location, or staff name"),
    current_user: UserProfile = Depends(get_current_user),
):
    """Lists field activities for the organisation."""
    return service.list_activities(
        org_id=current_user.defaultOrgId,
        project_id=projectId,
        activity_type=activityType,
        search=search,
    )


@router.post("/activities", response_model=ImpactActivity, status_code=status.HTTP_201_CREATED)
async def create_activity(
    request: ImpactActivityCreateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER])),
):
    """
    Logs a new field activity with attendance metrics and outputs.
    Allowed Roles: Organisation Administrator, Project Manager, Field Officer.
    Denied (403): Analyst, Viewer.
    """
    return service.create_activity(
        org_id=current_user.defaultOrgId,
        req=request,
        user=current_user,
    )


@router.get("/activities/{activity_id}", response_model=ImpactActivity)
async def get_activity(
    activity_id: str,
    current_user: UserProfile = Depends(get_current_user),
):
    """Retrieves activity details by ID."""
    return service.get_activity(
        org_id=current_user.defaultOrgId,
        activity_id=activity_id,
    )


@router.put("/activities/{activity_id}", response_model=ImpactActivity)
async def update_activity(
    activity_id: str,
    request: ImpactActivityUpdateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.FIELD_OFFICER])),
):
    """Updates an activity record."""
    return service.update_activity(
        org_id=current_user.defaultOrgId,
        activity_id=activity_id,
        req=request,
        user=current_user,
    )


@router.delete("/activities/{activity_id}")
async def delete_activity(
    activity_id: str,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER])),
):
    """Removes an activity record."""
    return service.delete_activity(
        org_id=current_user.defaultOrgId,
        activity_id=activity_id,
        user=current_user,
    )


# ── Dashboard Statistics Endpoint ────────────────────────────────────────────

@router.get("/dashboard/stats", response_model=ImpactOSDashboardStats)
async def get_dashboard_stats(
    current_user: UserProfile = Depends(get_current_user),
):
    """Delivers aggregated M&E dashboard metrics calculated strictly from actual records."""
    return service.get_impactos_dashboard_stats(current_user.defaultOrgId)


# ── Reports & Export Endpoints ───────────────────────────────────────────────

@router.post("/reports/generate", response_model=ImpactReport, status_code=status.HTTP_201_CREATED)
async def generate_impact_report(
    request: ReportGenerateRequest,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.ANALYST])),
):
    """
    Compiles an auditable, structured M&E project report.
    Allowed Roles: Organisation Administrator, Project Manager, Analyst.
    Denied (403): Field Officer, Viewer.
    """
    return service.generate_impact_report(
        org_id=current_user.defaultOrgId,
        req=request,
        user=current_user,
    )


@router.get("/reports/{report_id}", response_model=ImpactReport)
async def get_report(
    report_id: str,
    current_user: UserProfile = Depends(get_current_user),
):
    """Retrieves a previously generated M&E report."""
    return service.get_report(
        org_id=current_user.defaultOrgId,
        report_id=report_id,
    )


@router.get("/reports/{report_id}/export/csv")
async def export_report_csv(
    report_id: str,
    current_user: UserProfile = Depends(require_roles([Role.ORGANISATION_ADMIN, Role.PROJECT_MANAGER, Role.ANALYST])),
):
    """Exports structured M&E report as a downloadable CSV."""
    csv_data = service.export_report_csv(current_user.defaultOrgId, report_id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=impact_report_{report_id}.csv"},
    )


@router.get("/reports/{report_id}/export/html")
async def export_report_html(
    report_id: str,
    current_user: UserProfile = Depends(get_current_user),
):
    """Exports structured M&E report as a clean printable HTML document."""
    html_data = service.export_report_html(current_user.defaultOrgId, report_id)
    return Response(
        content=html_data,
        media_type="text/html",
    )
