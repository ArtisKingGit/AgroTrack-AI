"""
AgroTrack AI — ImpactOS Domain Service
Implements project monitoring, beneficiary management with PII protection,
M&E indicator tracking, measurable progress calculation, activity tracking,
multi-tenant isolation, and auditable M&E reporting.
"""

from datetime import datetime, date
from typing import List, Dict, Any, Optional
from fastapi import HTTPException, status
import csv
import io

from backend.models import (
    Role,
    ProjectStatus,
    BeneficiaryCategory,
    ParticipationStatus,
    IndicatorCategory,
    ReportingFrequency,
    IndicatorStatus,
    ImpactActivityType,
    ImpactActivityStatus,
    ProjectCreateRequest,
    ProjectUpdateRequest,
    BeneficiaryCreateRequest,
    BeneficiaryUpdateRequest,
    IndicatorCreateRequest,
    IndicatorUpdateRequest,
    IndicatorProgressRecordRequest,
    ImpactActivityCreateRequest,
    ImpactActivityUpdateRequest,
    ReportGenerateRequest,
    UserProfile,
)


# ── PII Protection Helpers ───────────────────────────────────────────────────

def mask_phone(phone: Optional[str]) -> Optional[str]:
    """Masks phone number for unauthorised roles (e.g., Viewer)."""
    if not phone:
        return None
    cleaned = str(phone).strip()
    if len(cleaned) <= 5:
        return "****"
    return f"{cleaned[:5]} *** {cleaned[-2:]}"


def mask_national_id(nid: Optional[str]) -> Optional[str]:
    """Masks national ID for unauthorised roles (e.g., Viewer)."""
    if not nid:
        return None
    cleaned = str(nid).strip()
    if len(cleaned) <= 3:
        return "***"
    return f"{'*' * (len(cleaned) - 2)}{cleaned[-2:]}"


# ── Indicator Progress & Status Calculations ─────────────────────────────────

def calculate_indicator_progress(current: float, baseline: float, target: float) -> float:
    """
    Computes percentage progress towards a target value without inventing numbers.
    progress % = ((current - baseline) / (target - baseline)) * 100
    """
    if target <= baseline:
        return 100.0 if current >= target else 0.0
    progress = ((current - baseline) / (target - baseline)) * 100.0
    return round(min(100.0, max(0.0, progress)), 1)


def determine_indicator_status(progress_percent: float) -> str:
    """Maps progress percentage to standard M&E performance status."""
    if progress_percent >= 100.0:
        return IndicatorStatus.ACHIEVED.value
    if progress_percent >= 75.0:
        return IndicatorStatus.ON_TRACK.value
    if progress_percent >= 40.0:
        return IndicatorStatus.BEHIND.value
    return IndicatorStatus.CRITICAL.value


# ── In-Memory Tenant Stores ──────────────────────────────────────────────────

TENANT_PROJECTS: Dict[str, List[Dict[str, Any]]] = {
    "org_greenvalley_01": [
        {
            "id": "proj_smcri_2026",
            "orgId": "org_greenvalley_01",
            "name": "Smallholder Maize Climate Resilience Initiative",
            "code": "SMCRI-2026",
            "description": "Climate-smart agronomic interventions, conservation tillage, and drought-tolerant seed for vulnerable maize farmers.",
            "locations": [{"county": "Nakuru", "subCounty": "Rongai", "ward": "Solai"}],
            "projectManagerId": "usr_mgr_002",
            "projectManagerName": "David Kiprop",
            "startDate": "2026-01-15",
            "endDate": "2026-12-31",
            "status": ProjectStatus.ACTIVE.value,
            "budget": 4500000.0,
            "currency": "KES",
            "targetBeneficiaries": 1200,
            "enrolledBeneficiariesCount": 3,
            "objectives": [
                {"id": "obj_01", "title": "Promote conservation tillage and drought-tolerant certified seed varieties"},
                {"id": "obj_02", "title": "Establish 20 climate-smart farmer field demonstration plots"},
                {"id": "obj_03", "title": "Improve household maize yields by at least 30% over baseline"},
            ],
            "sectors": ["Climate Resilience", "Food Security", "Smallholder Agriculture"],
            "donor": "USAID Feed the Future",
            "isArchived": False,
            "createdAt": "2026-01-15T08:00:00Z",
            "updatedAt": None,
        },
        {
            "id": "proj_horticulture_export_2026",
            "orgId": "org_greenvalley_01",
            "name": "High-Value Avocado & Pepper Value Chain Grant",
            "code": "HV-AVO-26",
            "description": "Export market compliance, phytosanitary standards training, and seedling subsidization for horticultural farmers.",
            "locations": [{"county": "Nakuru", "subCounty": "Njoro", "ward": "Lare"}],
            "projectManagerId": "usr_mgr_002",
            "projectManagerName": "David Kiprop",
            "startDate": "2026-02-01",
            "endDate": "2026-11-30",
            "status": ProjectStatus.ACTIVE.value,
            "budget": 6200000.0,
            "currency": "KES",
            "targetBeneficiaries": 650,
            "enrolledBeneficiariesCount": 1,
            "objectives": [
                {"id": "obj_01", "title": "Distribute 15,000 certified Hass avocado grafted seedlings"},
                {"id": "obj_02", "title": "Train 500 smallholders on GlobalGAP compliance and spray records"},
            ],
            "sectors": ["Horticulture", "Market Linkage", "Export Development"],
            "donor": "AGRA Africa",
            "isArchived": False,
            "createdAt": "2026-02-01T09:00:00Z",
            "updatedAt": None,
        },
        {
            "id": "proj_soil_health_subcounty",
            "orgId": "org_greenvalley_01",
            "name": "Sub-County Soil Acidity & NPK Rehabilitation",
            "code": "SOIL-REHAB",
            "description": "Liming, organic bio-slurry promotion, and soil testing across acidified volcanic soil corridors.",
            "locations": [{"county": "Nakuru", "subCounty": "Rongai", "ward": "Visoi"}],
            "projectManagerId": "usr_mgr_002",
            "projectManagerName": "David Kiprop",
            "startDate": "2026-06-01",
            "endDate": "2027-05-31",
            "status": ProjectStatus.PLANNING.value,
            "budget": 2100000.0,
            "currency": "KES",
            "targetBeneficiaries": 400,
            "enrolledBeneficiariesCount": 0,
            "objectives": [
                {"id": "obj_01", "title": "Conduct 1,000 laboratory soil pH and NPK baseline tests"},
                {"id": "obj_02", "title": "Deliver agricultural lime subsidy vouchers to affected smallholders"},
            ],
            "sectors": ["Soil Health", "Regenerative Agriculture"],
            "donor": "County Government of Nakuru",
            "isArchived": False,
            "createdAt": "2026-05-10T10:00:00Z",
            "updatedAt": None,
        },
    ],
    "org_highland_02": [
        {
            "id": "proj_highland_tea_2026",
            "orgId": "org_highland_02",
            "name": "Highland Smallholder Tea Regenerative Pruning",
            "code": "TEA-REGEN-26",
            "description": "Soil moisture conservation and bush rejuvenation for smallholder tea growers in Kericho.",
            "locations": [{"county": "Kericho", "subCounty": "Bureti", "ward": "Cheborge"}],
            "projectManagerId": "usr_hl_pm",
            "projectManagerName": "Wilson Koech",
            "startDate": "2026-03-01",
            "endDate": "2026-12-31",
            "status": ProjectStatus.ACTIVE.value,
            "budget": 3500000.0,
            "currency": "KES",
            "targetBeneficiaries": 500,
            "enrolledBeneficiariesCount": 1,
            "objectives": [
                {"id": "obj_01", "title": "Pruning and fertilizer calibration across 500 smallholder tea blocks"}
            ],
            "sectors": ["Cash Crops", "Tea Value Chain"],
            "donor": "KTDA Foundation",
            "isArchived": False,
            "createdAt": "2026-03-01T11:00:00Z",
            "updatedAt": None,
        }
    ],
}

TENANT_BENEFICIARIES: Dict[str, List[Dict[str, Any]]] = {
    "org_greenvalley_01": [
        {
            "id": "ben_gv_01",
            "orgId": "org_greenvalley_01",
            "beneficiaryCode": "BEN-GV-0001",
            "firstName": "Mary",
            "lastName": "Wambui",
            "category": BeneficiaryCategory.SMALLHOLDER_FARMER.value,
            "gender": "female",
            "ageGroup": "youth_18_35",
            "location": {"county": "Nakuru", "subCounty": "Rongai", "ward": "Solai"},
            "linkedFarmerId": "fmr_001",
            "phone": "+254722123456",
            "nationalId": "29871120",
            "enrolledProjects": [
                {
                    "projectId": "proj_smcri_2026",
                    "projectName": "Smallholder Maize Climate Resilience Initiative",
                    "enrolmentDate": "2026-02-01",
                    "participationStatus": ParticipationStatus.ACTIVE.value,
                    "supportReceived": ["Drought-Tolerant Seeds", "GAP Training"],
                }
            ],
            "status": "active",
            "createdAt": "2026-02-01T09:30:00Z",
            "updatedAt": None,
        },
        {
            "id": "ben_gv_02",
            "orgId": "org_greenvalley_01",
            "beneficiaryCode": "BEN-GV-0002",
            "firstName": "John",
            "lastName": "Koech",
            "category": BeneficiaryCategory.SMALLHOLDER_FARMER.value,
            "gender": "male",
            "ageGroup": "adult_36_60",
            "location": {"county": "Nakuru", "subCounty": "Rongai", "ward": "Solai"},
            "linkedFarmerId": "fmr_002",
            "phone": "+254733445566",
            "nationalId": "18765432",
            "enrolledProjects": [
                {
                    "projectId": "proj_smcri_2026",
                    "projectName": "Smallholder Maize Climate Resilience Initiative",
                    "enrolmentDate": "2026-02-10",
                    "participationStatus": ParticipationStatus.ACTIVE.value,
                    "supportReceived": ["Certified Maize Seed", "Soil Testing Voucher"],
                }
            ],
            "status": "active",
            "createdAt": "2026-02-10T10:15:00Z",
            "updatedAt": None,
        },
        {
            "id": "ben_gv_03",
            "orgId": "org_greenvalley_01",
            "beneficiaryCode": "BEN-GV-0003",
            "firstName": "Faith",
            "lastName": "Chepkemoi",
            "category": BeneficiaryCategory.WOMEN_COOPERATIVE.value,
            "gender": "female",
            "ageGroup": "youth_18_35",
            "location": {"county": "Nakuru", "subCounty": "Njoro", "ward": "Lare"},
            "linkedFarmerId": None,
            "phone": "+254711889900",
            "nationalId": "31224455",
            "enrolledProjects": [
                {
                    "projectId": "proj_horticulture_export_2026",
                    "projectName": "High-Value Avocado & Pepper Value Chain Grant",
                    "enrolmentDate": "2026-02-15",
                    "participationStatus": ParticipationStatus.ACTIVE.value,
                    "supportReceived": ["Avocado Seedlings", "Export Standards Training"],
                }
            ],
            "status": "active",
            "createdAt": "2026-02-15T11:00:00Z",
            "updatedAt": None,
        },
        {
            "id": "ben_gv_04",
            "orgId": "org_greenvalley_01",
            "beneficiaryCode": "BEN-GV-0004",
            "firstName": "Samuel",
            "lastName": "Kiprono",
            "category": BeneficiaryCategory.YOUTH_AGRIPRENEUR.value,
            "gender": "male",
            "ageGroup": "youth_18_35",
            "location": {"county": "Nakuru", "subCounty": "Rongai", "ward": "Visoi"},
            "linkedFarmerId": None,
            "phone": "+254700112233",
            "nationalId": "34556677",
            "enrolledProjects": [
                {
                    "projectId": "proj_smcri_2026",
                    "projectName": "Smallholder Maize Climate Resilience Initiative",
                    "enrolmentDate": "2026-03-01",
                    "participationStatus": ParticipationStatus.ACTIVE.value,
                    "supportReceived": ["Sprayer Equipment", "Digital Advisory"],
                }
            ],
            "status": "active",
            "createdAt": "2026-03-01T12:00:00Z",
            "updatedAt": None,
        },
    ],
    "org_highland_02": [
        {
            "id": "ben_hl_01",
            "orgId": "org_highland_02",
            "beneficiaryCode": "BEN-HL-0001",
            "firstName": "James",
            "lastName": "Mutua",
            "category": BeneficiaryCategory.SMALLHOLDER_FARMER.value,
            "gender": "male",
            "ageGroup": "adult_36_60",
            "location": {"county": "Kericho", "subCounty": "Bureti", "ward": "Cheborge"},
            "linkedFarmerId": None,
            "phone": "+254712349988",
            "nationalId": "20998811",
            "enrolledProjects": [
                {
                    "projectId": "proj_highland_tea_2026",
                    "projectName": "Highland Smallholder Tea Regenerative Pruning",
                    "enrolmentDate": "2026-03-05",
                    "participationStatus": ParticipationStatus.ACTIVE.value,
                    "supportReceived": ["Tea Shears", "Fertilizer Schedule"],
                }
            ],
            "status": "active",
            "createdAt": "2026-03-05T08:00:00Z",
            "updatedAt": None,
        }
    ],
}

TENANT_INDICATORS: Dict[str, List[Dict[str, Any]]] = {
    "org_greenvalley_01": [
        {
            "id": "ind_smcri_01",
            "orgId": "org_greenvalley_01",
            "projectId": "proj_smcri_2026",
            "projectName": "Smallholder Maize Climate Resilience Initiative",
            "name": "Hectares under Climate-Smart Agriculture",
            "code": "IND-CSA-01",
            "description": "Total agricultural area adopting conservation tillage, mulching, and drought-tolerant seed varieties.",
            "category": IndicatorCategory.OUTPUT.value,
            "unit": "hectares",
            "baselineValue": 0.0,
            "targetValue": 500.0,
            "currentValue": 380.0,
            "progressPercent": 76.0,
            "reportingFrequency": ReportingFrequency.QUARTERLY.value,
            "status": IndicatorStatus.ON_TRACK.value,
            "isVerified": True,
            "verificationSource": "Mid-Term Independent Assessment by Egerton AgEcon Team",
            "lastReportedDate": "2026-09-30",
            "createdAt": "2026-01-20T08:00:00Z",
        },
        {
            "id": "ind_smcri_02",
            "orgId": "org_greenvalley_01",
            "projectId": "proj_smcri_2026",
            "projectName": "Smallholder Maize Climate Resilience Initiative",
            "name": "Average Smallholder Maize Yield Gain",
            "code": "IND-YLD-02",
            "description": "Percentage increase in average maize yield per acre over the baseline survey.",
            "category": IndicatorCategory.OUTCOME.value,
            "unit": "percent",
            "baselineValue": 0.0,
            "targetValue": 35.0,
            "currentValue": 28.0,
            "progressPercent": 80.0,
            "reportingFrequency": ReportingFrequency.SEMI_ANNUALLY.value,
            "status": IndicatorStatus.ON_TRACK.value,
            "isVerified": True,
            "verificationSource": "Post-Harvest Sample Threshing Audit across 40 Sentinel Farms",
            "lastReportedDate": "2026-10-15",
            "createdAt": "2026-01-20T08:00:00Z",
        },
        {
            "id": "ind_smcri_03",
            "orgId": "org_greenvalley_01",
            "projectId": "proj_smcri_2026",
            "projectName": "Smallholder Maize Climate Resilience Initiative",
            "name": "Smallholder Farmers Trained in GAP",
            "code": "IND-TRN-03",
            "description": "Number of smallholder farmers completing the 4-module Good Agricultural Practices curriculum.",
            "category": IndicatorCategory.OUTPUT.value,
            "unit": "farmers_trained",
            "baselineValue": 0.0,
            "targetValue": 1200.0,
            "currentValue": 840.0,
            "progressPercent": 70.0,
            "reportingFrequency": ReportingFrequency.MONTHLY.value,
            "status": IndicatorStatus.BEHIND.value,
            "isVerified": False,
            "verificationSource": None,
            "lastReportedDate": "2026-10-25",
            "createdAt": "2026-01-20T08:00:00Z",
        },
        {
            "id": "ind_hort_01",
            "orgId": "org_greenvalley_01",
            "projectId": "proj_horticulture_export_2026",
            "projectName": "High-Value Avocado & Pepper Value Chain Grant",
            "name": "Hass Avocado Trees Planted",
            "code": "IND-AVO-01",
            "description": "Number of certified grafted Hass avocado seedlings planted and GPS tagged.",
            "category": IndicatorCategory.OUTPUT.value,
            "unit": "trees_planted",
            "baselineValue": 0.0,
            "targetValue": 15000.0,
            "currentValue": 16200.0,
            "progressPercent": 100.0,
            "reportingFrequency": ReportingFrequency.QUARTERLY.value,
            "status": IndicatorStatus.ACHIEVED.value,
            "isVerified": True,
            "verificationSource": "Nursery Delivery Manifests & Nursery Inspection Certificates",
            "lastReportedDate": "2026-10-10",
            "createdAt": "2026-02-05T09:00:00Z",
        },
    ],
    "org_highland_02": [
        {
            "id": "ind_hl_01",
            "orgId": "org_highland_02",
            "projectId": "proj_highland_tea_2026",
            "projectName": "Highland Smallholder Tea Regenerative Pruning",
            "name": "Tea Yield Quality Index",
            "code": "IND-TEA-01",
            "description": "Percentage of plucked tea leaves meeting prime two-leaves-and-a-bud specification.",
            "category": IndicatorCategory.OUTCOME.value,
            "unit": "percent",
            "baselineValue": 65.0,
            "targetValue": 85.0,
            "currentValue": 78.0,
            "progressPercent": 65.0,
            "reportingFrequency": ReportingFrequency.MONTHLY.value,
            "status": IndicatorStatus.BEHIND.value,
            "isVerified": True,
            "verificationSource": "KTDA Factory Intake Receipts",
            "lastReportedDate": "2026-10-20",
            "createdAt": "2026-03-10T10:00:00Z",
        }
    ],
}

TENANT_ACTIVITIES: Dict[str, List[Dict[str, Any]]] = {
    "org_greenvalley_01": [
        {
            "id": "act_imp_01",
            "orgId": "org_greenvalley_01",
            "projectId": "proj_smcri_2026",
            "projectName": "Smallholder Maize Climate Resilience Initiative",
            "title": "Climate-Smart Soil Health & Seed Inoculation Workshop",
            "activityType": ImpactActivityType.TRAINING_WORKSHOP.value,
            "activityDate": "2026-09-14",
            "location": "Solai Community Center, Nakuru",
            "responsibleStaffId": "usr_field_003",
            "responsibleStaffName": "Amina Otieno",
            "targetAttendance": 60,
            "actualAttendance": 54,
            "femaleAttendance": 32,
            "maleAttendance": 22,
            "youthAttendance": 28,
            "outputs": [
                "54 farmers completed practical bio-fertilizer mixing",
                "Distributed 54 training handbooks and field measuring tapes",
            ],
            "supportingNotes": "Strong participation from women's self-help group members. Demonstrations covered minimum tillage and seed spacing.",
            "evidenceAttachments": ["https://images.unsplash.com/photo-1592417817098-8f3d6910985c"],
            "status": ImpactActivityStatus.COMPLETED.value,
            "isVerified": True,
            "createdAt": "2026-09-14T17:00:00Z",
        },
        {
            "id": "act_imp_02",
            "orgId": "org_greenvalley_01",
            "projectId": "proj_smcri_2026",
            "projectName": "Smallholder Maize Climate Resilience Initiative",
            "title": "Certified Drought-Tolerant Seed Distribution Drive",
            "activityType": ImpactActivityType.INPUT_DISTRIBUTION.value,
            "activityDate": "2026-10-05",
            "location": "Rongai Agricultural Depot, Nakuru",
            "responsibleStaffId": "usr_field_003",
            "responsibleStaffName": "Amina Otieno",
            "targetAttendance": 200,
            "actualAttendance": 185,
            "femaleAttendance": 110,
            "maleAttendance": 75,
            "youthAttendance": 65,
            "outputs": [
                "185 bags of certified drought-tolerant seed vouchers redeemed",
                "Inspected and validated KEPHIS seed lot germination certificates",
            ],
            "supportingNotes": "Logistics smooth; cooperative officials supervised queue management and verified farmer national IDs against roster.",
            "evidenceAttachments": ["https://images.unsplash.com/photo-1574943320219-553eb213f72d"],
            "status": ImpactActivityStatus.COMPLETED.value,
            "isVerified": True,
            "createdAt": "2026-10-05T18:00:00Z",
        },
        {
            "id": "act_imp_03",
            "orgId": "org_greenvalley_01",
            "projectId": "proj_horticulture_export_2026",
            "projectName": "High-Value Avocado & Pepper Value Chain Grant",
            "title": "Avocado Export Phytosanitary & Spray Protocol Session",
            "activityType": ImpactActivityType.FIELD_DEMONSTRATION.value,
            "activityDate": "2026-10-22",
            "location": "Njoro Demonstration Orchard, Nakuru",
            "responsibleStaffId": "usr_mgr_002",
            "responsibleStaffName": "David Kiprop",
            "targetAttendance": 45,
            "actualAttendance": 42,
            "femaleAttendance": 24,
            "maleAttendance": 18,
            "youthAttendance": 19,
            "outputs": [
                "Live pruning and copper spray demonstration conducted",
                "42 pheromone fruit fly pest traps deployed across demonstration plots",
            ],
            "supportingNotes": "Field officers noted high awareness of maximum residue limits (MRLs). Observations recorded manually.",
            "evidenceAttachments": [],
            "status": ImpactActivityStatus.COMPLETED.value,
            "isVerified": False,
            "createdAt": "2026-10-22T16:30:00Z",
        },
    ],
    "org_highland_02": [
        {
            "id": "act_hl_01",
            "orgId": "org_highland_02",
            "projectId": "proj_highland_tea_2026",
            "projectName": "Highland Smallholder Tea Regenerative Pruning",
            "title": "Tea Soil Acidity Sampling & Lime Advisory",
            "activityType": ImpactActivityType.FIELD_DEMONSTRATION.value,
            "activityDate": "2026-09-28",
            "location": "Cheborge Tea Collection Point, Kericho",
            "responsibleStaffId": "usr_hl_pm",
            "responsibleStaffName": "Wilson Koech",
            "targetAttendance": 30,
            "actualAttendance": 28,
            "femaleAttendance": 12,
            "maleAttendance": 16,
            "youthAttendance": 8,
            "outputs": ["28 soil pH tests conducted on-site"],
            "supportingNotes": "High acidity detected across blocks 4 and 5.",
            "evidenceAttachments": [],
            "status": ImpactActivityStatus.COMPLETED.value,
            "isVerified": True,
            "createdAt": "2026-09-28T14:00:00Z",
        }
    ],
}

TENANT_INDICATOR_LOGS: Dict[str, List[Dict[str, Any]]] = {
    "org_greenvalley_01": [
        {
            "id": "log_ind_01",
            "indicatorId": "ind_smcri_01",
            "period": "Q3-2026",
            "measuredValue": 380.0,
            "measurementDate": "2026-09-30",
            "source": "Mid-Term Independent Assessment by Egerton AgEcon Team",
            "notes": "Verified through satellite NDVI and field boundary perimeter walking.",
            "isVerified": True,
            "verificationSource": "Egerton University AgEcon Dept",
            "reportedBy": "David Kiprop",
            "recordedAt": "2026-09-30T16:00:00Z",
        },
        {
            "id": "log_ind_02",
            "indicatorId": "ind_smcri_02",
            "period": "Q3-2026",
            "measuredValue": 28.0,
            "measurementDate": "2026-10-15",
            "source": "Post-Harvest Sample Threshing Audit across 40 Sentinel Farms",
            "notes": "Yields weighed on calibrated spring balances.",
            "isVerified": True,
            "verificationSource": "Ministry of Agriculture Crop Inspectorate",
            "reportedBy": "David Kiprop",
            "recordedAt": "2026-10-15T12:00:00Z",
        },
        {
            "id": "log_ind_03",
            "indicatorId": "ind_smcri_03",
            "period": "October 2026",
            "measuredValue": 840.0,
            "measurementDate": "2026-10-25",
            "source": "Field Officer Daily Sign-In Attendance Registers",
            "notes": "Attendance sheets aggregated; pending independent donor audit.",
            "isVerified": False,
            "verificationSource": None,
            "reportedBy": "Amina Otieno",
            "recordedAt": "2026-10-25T17:00:00Z",
        },
    ],
    "org_highland_02": [],
}

TENANT_REPORTS: Dict[str, List[Dict[str, Any]]] = {
    "org_greenvalley_01": [],
    "org_highland_02": [],
}


# ── Projects Domain Operations ───────────────────────────────────────────────

def list_projects(
    org_id: str,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
    include_archived: bool = False,
) -> List[Dict[str, Any]]:
    """Lists projects belonging to the specified organisation with optional filtering."""
    projects = TENANT_PROJECTS.get(org_id, [])
    results = []

    for p in projects:
        if not include_archived and p.get("isArchived", False):
            continue
        if status_filter and p.get("status", "").lower() != status_filter.lower():
            continue
        if search:
            query = search.lower().strip()
            name_match = query in p.get("name", "").lower()
            code_match = query in p.get("code", "").lower()
            desc_match = query in p.get("description", "").lower()
            donor_match = query in (p.get("donor") or "").lower()
            if not (name_match or code_match or desc_match or donor_match):
                continue
        results.append(p)

    return sorted(results, key=lambda x: x.get("createdAt", ""), reverse=True)


def get_project(org_id: str, project_id: str) -> Dict[str, Any]:
    """Retrieves a single project by ID, scoped to organisation."""
    projects = TENANT_PROJECTS.get(org_id, [])
    for p in projects:
        if p["id"] == project_id:
            return p
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Project '{project_id}' not found in organisation '{org_id}'."
    )


def create_project(org_id: str, req: ProjectCreateRequest, user: UserProfile) -> Dict[str, Any]:
    """
    Creates a new project record after validating dates, code uniqueness, and budget.
    """
    if org_id not in TENANT_PROJECTS:
        TENANT_PROJECTS[org_id] = []

    # 1. Date chronological validation
    try:
        start_d = datetime.strptime(req.startDate, "%Y-%m-%d").date()
        end_d = datetime.strptime(req.endDate, "%Y-%m-%d").date()
        if end_d < start_d:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project end date ({req.endDate}) cannot be earlier than start date ({req.startDate})."
            )
    except ValueError as e:
        if "cannot be earlier" in str(e):
            raise
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {e}. Expected YYYY-MM-DD."
        )

    # 2. Unique Project Code check per organisation
    code_clean = req.code.strip().upper()
    for existing in TENANT_PROJECTS[org_id]:
        if existing.get("code", "").upper() == code_clean:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Project code '{req.code}' is already registered in this organisation."
            )

    proj_id = f"proj_{code_clean.lower().replace('-', '_')}_{int(datetime.utcnow().timestamp())}"
    now_iso = datetime.utcnow().isoformat() + "Z"

    new_project = {
        "id": proj_id,
        "orgId": org_id,
        "name": req.name.strip(),
        "code": code_clean,
        "description": req.description.strip(),
        "locations": req.locations or [{"county": "Nakuru"}],
        "projectManagerId": req.projectManagerId or user.uid,
        "projectManagerName": req.projectManagerName or user.name,
        "startDate": req.startDate,
        "endDate": req.endDate,
        "status": req.status.value if hasattr(req.status, "value") else str(req.status or "active"),
        "budget": round(float(req.budget), 2),
        "currency": req.currency or "KES",
        "targetBeneficiaries": int(req.targetBeneficiaries),
        "enrolledBeneficiariesCount": 0,
        "objectives": req.objectives or [],
        "sectors": req.sectors or ["Agriculture"],
        "donor": req.donor.strip() if req.donor else None,
        "isArchived": False,
        "createdAt": now_iso,
        "updatedAt": None,
    }

    TENANT_PROJECTS[org_id].append(new_project)
    return new_project


def update_project(org_id: str, project_id: str, req: ProjectUpdateRequest, user: UserProfile) -> Dict[str, Any]:
    """Updates an existing project with date validation."""
    project = get_project(org_id, project_id)

    # Validate dates if either or both are being updated
    new_start = req.startDate or project["startDate"]
    new_end = req.endDate or project["endDate"]
    if req.startDate or req.endDate:
        try:
            start_d = datetime.strptime(new_start, "%Y-%m-%d").date()
            end_d = datetime.strptime(new_end, "%Y-%m-%d").date()
            if end_d < start_d:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Project end date ({new_end}) cannot be earlier than start date ({new_start})."
                )
        except ValueError as e:
            if "cannot be earlier" in str(e):
                raise
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {e}. Expected YYYY-MM-DD."
            )

    if req.name is not None:
        project["name"] = req.name.strip()
    if req.description is not None:
        project["description"] = req.description.strip()
    if req.locations is not None:
        project["locations"] = req.locations
    if req.projectManagerId is not None:
        project["projectManagerId"] = req.projectManagerId
    if req.projectManagerName is not None:
        project["projectManagerName"] = req.projectManagerName
    if req.startDate is not None:
        project["startDate"] = req.startDate
    if req.endDate is not None:
        project["endDate"] = req.endDate
    if req.status is not None:
        project["status"] = req.status.value if hasattr(req.status, "value") else str(req.status)
        if project["status"] == ProjectStatus.ARCHIVED.value:
            project["isArchived"] = True
    if req.budget is not None:
        project["budget"] = round(float(req.budget), 2)
    if req.targetBeneficiaries is not None:
        project["targetBeneficiaries"] = int(req.targetBeneficiaries)
    if req.objectives is not None:
        project["objectives"] = req.objectives
    if req.sectors is not None:
        project["sectors"] = req.sectors
    if req.donor is not None:
        project["donor"] = req.donor.strip()
    if req.isArchived is not None:
        project["isArchived"] = bool(req.isArchived)
        if project["isArchived"]:
            project["status"] = ProjectStatus.ARCHIVED.value

    project["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    return project


def archive_project(org_id: str, project_id: str, user: UserProfile) -> Dict[str, Any]:
    """Soft archives a project without deleting historical records."""
    project = get_project(org_id, project_id)
    project["isArchived"] = True
    project["status"] = ProjectStatus.ARCHIVED.value
    project["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    return {
        "message": f"Project '{project['name']}' ({project['code']}) has been successfully archived.",
        "project": project,
    }


def delete_project(org_id: str, project_id: str, user: UserProfile) -> Dict[str, Any]:
    """Deletes or soft archives a project."""
    project = get_project(org_id, project_id)
    TENANT_PROJECTS[org_id] = [p for p in TENANT_PROJECTS[org_id] if p["id"] != project_id]
    return {
        "message": f"Project '{project['name']}' ({project['code']}) removed from registry.",
        "projectId": project_id,
    }


# ── Beneficiary Domain Operations ────────────────────────────────────────────

def list_beneficiaries(
    org_id: str,
    project_id: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    user_role: Optional[Role] = None,
) -> List[Dict[str, Any]]:
    """
    Lists beneficiaries scoped to the organisation.
    Protects sensitive PII: If user role is VIEWER, phone and nationalId are masked.
    """
    beneficiaries = TENANT_BENEFICIARIES.get(org_id, [])
    results = []

    for b in beneficiaries:
        if project_id:
            # Check if enrolled in this project
            enrolled = any(ep.get("projectId") == project_id for ep in b.get("enrolledProjects", []))
            if not enrolled:
                continue
        if category and b.get("category") != category:
            continue
        if search:
            query = search.lower().strip()
            name_match = query in f"{b.get('firstName', '')} {b.get('lastName', '')}".lower()
            code_match = query in b.get("beneficiaryCode", "").lower()
            loc_match = query in str(b.get("location", {})).lower()
            if not (name_match or code_match or loc_match):
                continue

        # Sensitive PII masking for read-only / unauthorized roles
        item = dict(b)
        if user_role == Role.VIEWER:
            item["phone"] = mask_phone(item.get("phone"))
            item["nationalId"] = mask_national_id(item.get("nationalId"))
        results.append(item)

    return sorted(results, key=lambda x: x.get("createdAt", ""), reverse=True)


def get_beneficiary(org_id: str, beneficiary_id: str, user_role: Optional[Role] = None) -> Dict[str, Any]:
    """Retrieves a single beneficiary by ID with PII protection for viewers."""
    beneficiaries = TENANT_BENEFICIARIES.get(org_id, [])
    for b in beneficiaries:
        if b["id"] == beneficiary_id:
            item = dict(b)
            if user_role == Role.VIEWER:
                item["phone"] = mask_phone(item.get("phone"))
                item["nationalId"] = mask_national_id(item.get("nationalId"))
            return item
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Beneficiary '{beneficiary_id}' not found in organisation '{org_id}'."
    )


def create_beneficiary(org_id: str, req: BeneficiaryCreateRequest, user: UserProfile) -> Dict[str, Any]:
    """
    Creates a new beneficiary record. Minimises personal data collection.
    Automatically assigns unique beneficiary code and links to project if provided.
    """
    if org_id not in TENANT_BENEFICIARIES:
        TENANT_BENEFICIARIES[org_id] = []

    # Count existing to form sequential code
    seq = len(TENANT_BENEFICIARIES[org_id]) + 1
    code = f"BEN-{org_id.split('_')[1].upper()[:2]}-{seq:04d}"
    ben_id = f"ben_{seq:03d}_{int(datetime.utcnow().timestamp())}"
    now_iso = datetime.utcnow().isoformat() + "Z"

    enrolled_projects = []
    if req.projectId:
        # Validate that project exists in this organisation
        proj = get_project(org_id, req.projectId)
        enrolled_projects.append({
            "projectId": proj["id"],
            "projectName": proj["name"],
            "enrolmentDate": req.enrolmentDate or str(date.today()),
            "participationStatus": req.participationStatus.value if hasattr(req.participationStatus, "value") else str(req.participationStatus or "enrolled"),
            "supportReceived": req.supportReceived or [],
        })
        # Increment project enrolled count
        proj["enrolledBeneficiariesCount"] = proj.get("enrolledBeneficiariesCount", 0) + 1

    new_beneficiary = {
        "id": ben_id,
        "orgId": org_id,
        "beneficiaryCode": code,
        "firstName": req.firstName.strip(),
        "lastName": req.lastName.strip(),
        "category": req.category.value if hasattr(req.category, "value") else str(req.category),
        "gender": (req.gender or "unspecified").lower(),
        "ageGroup": req.ageGroup or "youth_18_35",
        "location": req.location or {"county": "Nakuru"},
        "linkedFarmerId": req.linkedFarmerId,
        "phone": req.phone.strip() if req.phone else None,
        "nationalId": req.nationalId.strip() if req.nationalId else None,
        "enrolledProjects": enrolled_projects,
        "status": "active",
        "createdAt": now_iso,
        "updatedAt": None,
    }

    TENANT_BENEFICIARIES[org_id].append(new_beneficiary)
    return new_beneficiary


def update_beneficiary(org_id: str, beneficiary_id: str, req: BeneficiaryUpdateRequest, user: UserProfile) -> Dict[str, Any]:
    """Updates beneficiary demographics or status."""
    beneficiary = get_beneficiary(org_id, beneficiary_id)

    if req.firstName is not None:
        beneficiary["firstName"] = req.firstName.strip()
    if req.lastName is not None:
        beneficiary["lastName"] = req.lastName.strip()
    if req.category is not None:
        beneficiary["category"] = req.category.value if hasattr(req.category, "value") else str(req.category)
    if req.gender is not None:
        beneficiary["gender"] = req.gender.lower()
    if req.ageGroup is not None:
        beneficiary["ageGroup"] = req.ageGroup
    if req.location is not None:
        beneficiary["location"] = req.location
    if req.phone is not None:
        beneficiary["phone"] = req.phone.strip()
    if req.nationalId is not None:
        beneficiary["nationalId"] = req.nationalId.strip()
    if req.status is not None:
        beneficiary["status"] = req.status

    beneficiary["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    return beneficiary


def enroll_beneficiary_in_project(
    org_id: str,
    beneficiary_id: str,
    project_id: str,
    participation_status: str = "active",
    support_received: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Enrolls an existing beneficiary into an additional project."""
    beneficiary = get_beneficiary(org_id, beneficiary_id)
    project = get_project(org_id, project_id)

    # Check if already enrolled
    for ep in beneficiary.get("enrolledProjects", []):
        if ep["projectId"] == project_id:
            ep["participationStatus"] = participation_status
            if support_received:
                ep["supportReceived"] = list(set(ep.get("supportReceived", []) + support_received))
            return beneficiary

    # Add new project enrollment
    beneficiary.setdefault("enrolledProjects", []).append({
        "projectId": project["id"],
        "projectName": project["name"],
        "enrolmentDate": str(date.today()),
        "participationStatus": participation_status,
        "supportReceived": support_received or [],
    })
    project["enrolledBeneficiariesCount"] = project.get("enrolledBeneficiariesCount", 0) + 1
    return beneficiary


def delete_beneficiary(org_id: str, beneficiary_id: str, user: UserProfile) -> Dict[str, Any]:
    """Deletes or soft archives a beneficiary."""
    beneficiary = get_beneficiary(org_id, beneficiary_id)
    TENANT_BENEFICIARIES[org_id] = [b for b in TENANT_BENEFICIARIES[org_id] if b["id"] != beneficiary_id]
    return {
        "message": f"Beneficiary '{beneficiary['firstName']} {beneficiary['lastName']}' removed.",
        "beneficiaryId": beneficiary_id,
    }


# ── Indicators Domain Operations ─────────────────────────────────────────────

def list_indicators(
    org_id: str,
    project_id: Optional[str] = None,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lists M&E indicators for an organisation."""
    indicators = TENANT_INDICATORS.get(org_id, [])
    results = []

    for ind in indicators:
        if project_id and ind.get("projectId") != project_id:
            continue
        if category and ind.get("category") != category:
            continue
        results.append(ind)

    return sorted(results, key=lambda x: x.get("createdAt", ""), reverse=True)


def get_indicator(org_id: str, indicator_id: str) -> Dict[str, Any]:
    """Retrieves an indicator by ID."""
    indicators = TENANT_INDICATORS.get(org_id, [])
    for ind in indicators:
        if ind["id"] == indicator_id:
            return ind
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Indicator '{indicator_id}' not found in organisation '{org_id}'."
    )


def create_indicator(org_id: str, req: IndicatorCreateRequest, user: UserProfile) -> Dict[str, Any]:
    """
    Creates a new performance indicator with defined baseline, target, and measurement unit.
    """
    if org_id not in TENANT_INDICATORS:
        TENANT_INDICATORS[org_id] = []

    # Verify project exists
    project = get_project(org_id, req.projectId)

    if req.targetValue <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Indicator target value must be strictly greater than 0."
        )

    ind_id = f"ind_{req.code.lower().replace('-', '_')}_{int(datetime.utcnow().timestamp())}"
    now_iso = datetime.utcnow().isoformat() + "Z"

    curr = req.currentValue or 0.0
    progress = calculate_indicator_progress(curr, req.baselineValue, req.targetValue)
    status_val = determine_indicator_status(progress)

    new_indicator = {
        "id": ind_id,
        "orgId": org_id,
        "projectId": project["id"],
        "projectName": project["name"],
        "name": req.name.strip(),
        "code": req.code.strip().upper(),
        "description": req.description.strip(),
        "category": req.category.value if hasattr(req.category, "value") else str(req.category),
        "unit": req.unit.strip(),
        "baselineValue": round(float(req.baselineValue), 2),
        "targetValue": round(float(req.targetValue), 2),
        "currentValue": round(float(curr), 2),
        "progressPercent": progress,
        "reportingFrequency": req.reportingFrequency.value if hasattr(req.reportingFrequency, "value") else str(req.reportingFrequency),
        "status": status_val,
        "isVerified": False,
        "verificationSource": None,
        "lastReportedDate": None,
        "createdAt": now_iso,
    }

    TENANT_INDICATORS[org_id].append(new_indicator)
    return new_indicator


def update_indicator(org_id: str, indicator_id: str, req: IndicatorUpdateRequest, user: UserProfile) -> Dict[str, Any]:
    """Updates indicator metadata and recalculates progress if target is changed."""
    indicator = get_indicator(org_id, indicator_id)

    if req.name is not None:
        indicator["name"] = req.name.strip()
    if req.description is not None:
        indicator["description"] = req.description.strip()
    if req.unit is not None:
        indicator["unit"] = req.unit.strip()
    if req.reportingFrequency is not None:
        indicator["reportingFrequency"] = req.reportingFrequency.value if hasattr(req.reportingFrequency, "value") else str(req.reportingFrequency)
    if req.targetValue is not None:
        if req.targetValue <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Indicator target value must be strictly greater than 0."
            )
        indicator["targetValue"] = round(float(req.targetValue), 2)
        # Recalculate progress
        progress = calculate_indicator_progress(indicator["currentValue"], indicator["baselineValue"], indicator["targetValue"])
        indicator["progressPercent"] = progress
        indicator["status"] = determine_indicator_status(progress)

    return indicator


def record_indicator_progress(
    org_id: str,
    indicator_id: str,
    req: IndicatorProgressRecordRequest,
    user: UserProfile,
) -> Dict[str, Any]:
    """
    Records an auditable measurement update for an indicator.
    Updates currentValue, recalculates progress %, and appends to audit logs.
    """
    indicator = get_indicator(org_id, indicator_id)

    if org_id not in TENANT_INDICATOR_LOGS:
        TENANT_INDICATOR_LOGS[org_id] = []

    m_date = req.measurementDate or str(date.today())
    new_val = round(float(req.measuredValue), 2)
    progress = calculate_indicator_progress(new_val, indicator["baselineValue"], indicator["targetValue"])
    stat = determine_indicator_status(progress)

    # Update indicator state
    indicator["currentValue"] = new_val
    indicator["progressPercent"] = progress
    indicator["status"] = stat
    indicator["isVerified"] = req.isVerified
    indicator["verificationSource"] = req.verificationSource if req.isVerified else None
    indicator["lastReportedDate"] = m_date

    # Add audit log
    log_entry = {
        "id": f"log_{int(datetime.utcnow().timestamp())}_{len(TENANT_INDICATOR_LOGS[org_id]) + 1}",
        "indicatorId": indicator["id"],
        "indicatorName": indicator["name"],
        "period": req.period,
        "measuredValue": new_val,
        "measurementDate": m_date,
        "source": req.source.strip(),
        "notes": req.notes.strip() if req.notes else None,
        "isVerified": req.isVerified,
        "verificationSource": req.verificationSource if req.isVerified else None,
        "reportedBy": user.name,
        "recordedAt": datetime.utcnow().isoformat() + "Z",
    }
    TENANT_INDICATOR_LOGS[org_id].append(log_entry)

    return {
        "indicator": indicator,
        "auditLog": log_entry,
    }


# ── Activity Domain Operations ───────────────────────────────────────────────

def list_activities(
    org_id: str,
    project_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lists project field activities for the organisation."""
    activities = TENANT_ACTIVITIES.get(org_id, [])
    results = []

    for a in activities:
        if project_id and a.get("projectId") != project_id:
            continue
        if activity_type and a.get("activityType") != activity_type:
            continue
        if search:
            query = search.lower().strip()
            title_match = query in a.get("title", "").lower()
            loc_match = query in a.get("location", "").lower()
            staff_match = query in a.get("responsibleStaffName", "").lower()
            if not (title_match or loc_match or staff_match):
                continue
        results.append(a)

    return sorted(results, key=lambda x: x.get("activityDate", ""), reverse=True)


def get_activity(org_id: str, activity_id: str) -> Dict[str, Any]:
    """Retrieves an activity by ID."""
    activities = TENANT_ACTIVITIES.get(org_id, [])
    for a in activities:
        if a["id"] == activity_id:
            return a
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Activity '{activity_id}' not found in organisation '{org_id}'."
    )


def create_activity(org_id: str, req: ImpactActivityCreateRequest, user: UserProfile) -> Dict[str, Any]:
    """Logs a programme activity with attendance metrics, outputs, and supporting evidence."""
    if org_id not in TENANT_ACTIVITIES:
        TENANT_ACTIVITIES[org_id] = []

    project = get_project(org_id, req.projectId)
    act_id = f"act_{int(datetime.utcnow().timestamp())}_{len(TENANT_ACTIVITIES[org_id]) + 1}"
    now_iso = datetime.utcnow().isoformat() + "Z"

    new_activity = {
        "id": act_id,
        "orgId": org_id,
        "projectId": project["id"],
        "projectName": project["name"],
        "title": req.title.strip(),
        "activityType": req.activityType.value if hasattr(req.activityType, "value") else str(req.activityType),
        "activityDate": req.activityDate or str(date.today()),
        "location": req.location.strip(),
        "responsibleStaffId": req.responsibleStaffId or user.uid,
        "responsibleStaffName": req.responsibleStaffName or user.name,
        "targetAttendance": int(req.targetAttendance),
        "actualAttendance": int(req.actualAttendance),
        "femaleAttendance": int(req.femaleAttendance),
        "maleAttendance": int(req.maleAttendance),
        "youthAttendance": int(req.youthAttendance),
        "outputs": req.outputs or [],
        "supportingNotes": req.supportingNotes.strip() if req.supportingNotes else None,
        "evidenceAttachments": req.evidenceAttachments or [],
        "status": req.status.value if hasattr(req.status, "value") else str(req.status or "completed"),
        "isVerified": req.isVerified,
        "createdAt": now_iso,
    }

    TENANT_ACTIVITIES[org_id].append(new_activity)
    return new_activity


def update_activity(org_id: str, activity_id: str, req: ImpactActivityUpdateRequest, user: UserProfile) -> Dict[str, Any]:
    """Updates an existing activity record."""
    activity = get_activity(org_id, activity_id)

    if req.title is not None:
        activity["title"] = req.title.strip()
    if req.activityType is not None:
        activity["activityType"] = req.activityType.value if hasattr(req.activityType, "value") else str(req.activityType)
    if req.activityDate is not None:
        activity["activityDate"] = req.activityDate
    if req.location is not None:
        activity["location"] = req.location.strip()
    if req.targetAttendance is not None:
        activity["targetAttendance"] = int(req.targetAttendance)
    if req.actualAttendance is not None:
        activity["actualAttendance"] = int(req.actualAttendance)
    if req.femaleAttendance is not None:
        activity["femaleAttendance"] = int(req.femaleAttendance)
    if req.maleAttendance is not None:
        activity["maleAttendance"] = int(req.maleAttendance)
    if req.youthAttendance is not None:
        activity["youthAttendance"] = int(req.youthAttendance)
    if req.outputs is not None:
        activity["outputs"] = req.outputs
    if req.supportingNotes is not None:
        activity["supportingNotes"] = req.supportingNotes.strip()
    if req.status is not None:
        activity["status"] = req.status.value if hasattr(req.status, "value") else str(req.status)
    if req.isVerified is not None:
        activity["isVerified"] = bool(req.isVerified)

    return activity


def delete_activity(org_id: str, activity_id: str, user: UserProfile) -> Dict[str, Any]:
    """Deletes an activity record."""
    activity = get_activity(org_id, activity_id)
    TENANT_ACTIVITIES[org_id] = [a for a in TENANT_ACTIVITIES[org_id] if a["id"] != activity_id]
    return {
        "message": f"Activity '{activity['title']}' removed from registry.",
        "activityId": activity_id,
    }


# ── Dashboard Statistics ─────────────────────────────────────────────────────

def get_impactos_dashboard_stats(org_id: str) -> Dict[str, Any]:
    """
    Calculates operational M&E metrics strictly from actual records.
    Never invents statistics.
    """
    projects = TENANT_PROJECTS.get(org_id, [])
    beneficiaries = TENANT_BENEFICIARIES.get(org_id, [])
    indicators = TENANT_INDICATORS.get(org_id, [])
    activities = TENANT_ACTIVITIES.get(org_id, [])

    active_projects = [p for p in projects if p.get("status") == ProjectStatus.ACTIVE.value and not p.get("isArchived")]
    completed_projects = [p for p in projects if p.get("status") in [ProjectStatus.COMPLETED.value, ProjectStatus.ARCHIVED.value] or p.get("isArchived")]

    total_beneficiaries = len(beneficiaries)
    female_count = len([b for b in beneficiaries if b.get("gender") == "female"])
    youth_count = len([b for b in beneficiaries if b.get("ageGroup") == "youth_18_35"])

    female_pct = round((female_count / total_beneficiaries * 100.0), 1) if total_beneficiaries > 0 else 0.0
    youth_pct = round((youth_count / total_beneficiaries * 100.0), 1) if total_beneficiaries > 0 else 0.0

    total_indicators = len(indicators)
    overall_progress = round(sum(ind.get("progressPercent", 0.0) for ind in indicators) / total_indicators, 1) if total_indicators > 0 else 0.0

    breakdown = {
        "on_track": len([i for i in indicators if i.get("status") == IndicatorStatus.ON_TRACK.value]),
        "achieved": len([i for i in indicators if i.get("status") == IndicatorStatus.ACHIEVED.value]),
        "behind": len([i for i in indicators if i.get("status") == IndicatorStatus.BEHIND.value]),
        "critical": len([i for i in indicators if i.get("status") == IndicatorStatus.CRITICAL.value]),
    }

    completed_acts = len([a for a in activities if a.get("status") == ImpactActivityStatus.COMPLETED.value])
    total_budget = round(sum(p.get("budget", 0.0) for p in active_projects), 2)

    recent_acts = sorted(activities, key=lambda x: x.get("activityDate", ""), reverse=True)[:5]

    return {
        "activeProjectsCount": len(active_projects),
        "completedProjectsCount": len(completed_projects),
        "totalBeneficiariesCount": total_beneficiaries,
        "femaleBeneficiariesPercent": female_pct,
        "youthBeneficiariesPercent": youth_pct,
        "totalIndicatorsCount": total_indicators,
        "overallTargetProgressPercent": overall_progress,
        "completedActivitiesCount": completed_acts,
        "indicatorPerformanceBreakdown": breakdown,
        "totalBudget": total_budget,
        "currency": "KES",
        "recentActivities": recent_acts,
    }


# ── Reports Generation & Export ──────────────────────────────────────────────

def generate_impact_report(org_id: str, req: ReportGenerateRequest, user: UserProfile) -> Dict[str, Any]:
    """
    Compiles an auditable, structured M&E project report.
    Explicitly distinguishes verified results (M&E audited) from field observations.
    """
    if org_id not in TENANT_REPORTS:
        TENANT_REPORTS[org_id] = []

    # 1. Project Context
    project_obj = None
    project_name = "All Active Programmes Portfolio"
    if req.projectId:
        project_obj = get_project(org_id, req.projectId)
        project_name = project_obj["name"]
        indicators = [i for i in TENANT_INDICATORS.get(org_id, []) if i.get("projectId") == req.projectId]
        activities = [a for a in TENANT_ACTIVITIES.get(org_id, []) if a.get("projectId") == req.projectId]
        beneficiaries = [
            b for b in TENANT_BENEFICIARIES.get(org_id, [])
            if any(ep.get("projectId") == req.projectId for ep in b.get("enrolledProjects", []))
        ]
    else:
        indicators = TENANT_INDICATORS.get(org_id, [])
        activities = TENANT_ACTIVITIES.get(org_id, [])
        beneficiaries = TENANT_BENEFICIARIES.get(org_id, [])

    # 2. Beneficiary Demographic Statistics
    total_bens = len(beneficiaries)
    females = len([b for b in beneficiaries if b.get("gender") == "female"])
    males = len([b for b in beneficiaries if b.get("gender") == "male"])
    youth = len([b for b in beneficiaries if b.get("ageGroup") == "youth_18_35"])

    cat_breakdown: Dict[str, int] = {}
    for b in beneficiaries:
        cat = b.get("category", "other")
        cat_breakdown[cat] = cat_breakdown.get(cat, 0) + 1

    status_breakdown: Dict[str, int] = {}
    for b in beneficiaries:
        for ep in b.get("enrolledProjects", []):
            if not req.projectId or ep.get("projectId") == req.projectId:
                st = ep.get("participationStatus", "enrolled")
                status_breakdown[st] = status_breakdown.get(st, 0) + 1

    # 3. Segregation: Verified Results vs Field Observations
    verified_results = []
    field_observations = []

    # Process indicators
    for ind in indicators:
        item = {
            "type": "indicator_metric",
            "code": ind["code"],
            "title": ind["name"],
            "category": ind["category"],
            "baseline": ind["baselineValue"],
            "target": ind["targetValue"],
            "current": ind["currentValue"],
            "unit": ind["unit"],
            "progressPercent": ind["progressPercent"],
            "status": ind["status"],
            "isVerified": ind.get("isVerified", False),
            "verificationSource": ind.get("verificationSource") or "Audited field verification protocol",
            "lastReported": ind.get("lastReportedDate"),
        }
        if ind.get("isVerified", False):
            verified_results.append(item)
        else:
            field_observations.append(item)

    # Process activities
    for act in activities:
        act_item = {
            "type": "field_activity",
            "title": act["title"],
            "activityType": act["activityType"],
            "date": act["activityDate"],
            "location": act["location"],
            "attendance": act["actualAttendance"],
            "femaleAttendance": act["femaleAttendance"],
            "youthAttendance": act["youthAttendance"],
            "outputs": act.get("outputs", []),
            "notes": act.get("supportingNotes"),
            "isVerified": act.get("isVerified", False),
            "staff": act.get("responsibleStaffName"),
        }
        if act.get("isVerified", False):
            verified_results.append(act_item)
        else:
            field_observations.append(act_item)

    # 4. Activities Summary
    total_acts = len(activities)
    completed_acts = len([a for a in activities if a.get("status") == ImpactActivityStatus.COMPLETED.value])
    total_attendance = sum(a.get("actualAttendance", 0) for a in activities)

    # 5. Build Report Record
    report_id = f"rep_imp_{req.reportingPeriod.lower().replace('-', '_')}_{int(datetime.utcnow().timestamp())}"
    now_iso = datetime.utcnow().isoformat() + "Z"

    challenges = req.challenges or [
        {
            "challenge": "Seasonal rainfall onset delay affected planting schedule in Solai ward",
            "impact": "Delayed initial germinating period by approximately 18 days",
            "mitigation": "Recommended short-cycle drought-tolerant seed varieties and soil moisture retention mulching",
            "status": "Managed"
        }
    ]

    report = {
        "reportId": report_id,
        "orgId": org_id,
        "projectId": req.projectId,
        "projectName": project_name,
        "reportingPeriod": req.reportingPeriod,
        "generatedAt": now_iso,
        "generatedBy": f"{user.name} ({user.activeRole.value})",
        "projectOverview": project_obj or {
            "title": "Consolidated M&E Portfolio",
            "description": "Multi-project development impact review across all active initiatives in this organisation.",
            "totalProjects": len(TENANT_PROJECTS.get(org_id, [])),
        },
        "objectives": project_obj.get("objectives", []) if project_obj else [],
        "beneficiaryStats": {
            "totalBeneficiaries": total_bens,
            "femaleCount": females,
            "femalePercent": round(females / total_bens * 100.0, 1) if total_bens > 0 else 0.0,
            "maleCount": males,
            "malePercent": round(males / total_bens * 100.0, 1) if total_bens > 0 else 0.0,
            "youthCount": youth,
            "youthPercent": round(youth / total_bens * 100.0, 1) if total_bens > 0 else 0.0,
            "byCategory": cat_breakdown,
            "byParticipationStatus": status_breakdown,
        },
        "indicatorPerformance": indicators,
        "verifiedResults": verified_results,
        "fieldObservations": field_observations if req.includeUnverified else [],
        "activitiesSummary": {
            "totalActivities": total_acts,
            "completedActivities": completed_acts,
            "totalAttendance": total_attendance,
        },
        "challengesAndMitigations": challenges,
        "executiveSummary": (
            f"During reporting period {req.reportingPeriod}, {project_name} tracked {total_bens} beneficiaries "
            f"({females} female, {youth} youth) with an overall indicator progress of "
            f"{round(sum(i.get('progressPercent', 0) for i in indicators) / len(indicators), 1) if indicators else 0.0}%. "
            f"A total of {len(verified_results)} verified M&E results were audited alongside {len(field_observations)} field observations."
        ),
    }

    TENANT_REPORTS[org_id].append(report)
    return report


def get_report(org_id: str, report_id: str) -> Dict[str, Any]:
    """Retrieves a previously generated M&E report."""
    reports = TENANT_REPORTS.get(org_id, [])
    for r in reports:
        if r["reportId"] == report_id:
            return r
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Report '{report_id}' not found in organisation '{org_id}'."
    )


def export_report_csv(org_id: str, report_id: str) -> str:
    """Exports structured M&E report indicators and beneficiaries as a clean CSV."""
    report = get_report(org_id, report_id)
    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Header Information
    writer.writerow(["AGROTRACK AI — IMPACTOS MONITORING & EVALUATION REPORT"])
    writer.writerow(["Project", report["projectName"]])
    writer.writerow(["Reporting Period", report["reportingPeriod"]])
    writer.writerow(["Generated At", report["generatedAt"]])
    writer.writerow(["Generated By", report["generatedBy"]])
    writer.writerow([])

    # 2. Indicators Table
    writer.writerow(["M&E INDICATORS PERFORMANCE"])
    writer.writerow(["Code", "Indicator Name", "Category", "Baseline", "Target", "Current", "Unit", "Progress %", "Status", "Verified?", "Verification Source"])
    for ind in report.get("indicatorPerformance", []):
        writer.writerow([
            ind.get("code"),
            ind.get("name"),
            ind.get("category"),
            ind.get("baselineValue"),
            ind.get("targetValue"),
            ind.get("currentValue"),
            ind.get("unit"),
            ind.get("progressPercent"),
            ind.get("status"),
            "YES" if ind.get("isVerified") else "NO",
            ind.get("verificationSource") or "Pending Audit",
        ])
    writer.writerow([])

    # 3. Beneficiary Summary
    bs = report.get("beneficiaryStats", {})
    writer.writerow(["BENEFICIARY REACH & DEMOGRAPHICS"])
    writer.writerow(["Total Beneficiaries", bs.get("totalBeneficiaries", 0)])
    writer.writerow(["Female Beneficiaries", f"{bs.get('femaleCount', 0)} ({bs.get('femalePercent', 0)}%)"])
    writer.writerow(["Youth Beneficiaries (18-35)", f"{bs.get('youthCount', 0)} ({bs.get('youthPercent', 0)}%)"])
    writer.writerow([])

    # 4. Verified Results Section
    writer.writerow(["AUDITED & VERIFIED RESULTS"])
    writer.writerow(["Type", "Title / Code", "Metric / Output", "Source / Evidence"])
    for vr in report.get("verifiedResults", []):
        if vr.get("type") == "indicator_metric":
            writer.writerow(["Indicator", f"{vr.get('code')} - {vr.get('title')}", f"{vr.get('current')} {vr.get('unit')} ({vr.get('progressPercent')}%)", vr.get("verificationSource")])
        else:
            writer.writerow(["Field Activity", vr.get("title"), f"Attendance: {vr.get('attendance')} farmers", vr.get("staff")])
    writer.writerow([])

    return output.getvalue()


def export_report_html(org_id: str, report_id: str) -> str:
    """Exports structured M&E report as a clean printable HTML document."""
    report = get_report(org_id, report_id)
    bs = report.get("beneficiaryStats", {})
    indicators = report.get("indicatorPerformance", [])
    verified_results = report.get("verifiedResults", [])
    field_obs = report.get("fieldObservations", [])

    indicator_rows = "".join([
        f"""
        <tr>
          <td><strong>{i.get('code')}</strong></td>
          <td>{i.get('name')}</td>
          <td><span style="font-size: 0.75rem; text-transform: uppercase; background: #e2e8f0; padding: 2px 6px; border-radius: 4px;">{i.get('category')}</span></td>
          <td style="text-align: right;">{i.get('baselineValue')}</td>
          <td style="text-align: right;"><strong>{i.get('targetValue')}</strong></td>
          <td style="text-align: right; color: #047857; font-weight: 700;">{i.get('currentValue')}</td>
          <td>{i.get('unit')}</td>
          <td style="text-align: right;"><strong>{i.get('progressPercent')}%</strong></td>
          <td><span style="padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.75rem; background: {'#dcfce7; color: #15803d;' if i.get('status') in ['on_track', 'achieved'] else '#fee2e2; color: #b91c1c;'}">{i.get('status')}</span></td>
          <td>{'<span style="color: #047857;">&#10004; Verified</span>' if i.get('isVerified') else '<span style="color: #d97706;">&#9888; Field Obs</span>'}</td>
        </tr>
        """
        for i in indicators
    ])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>M&E Report — {report['projectName']} ({report['reportingPeriod']})</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #1e293b; margin: 40px; line-height: 1.5; }}
    .header {{ border-bottom: 3px solid #0f392b; padding-bottom: 20px; margin-bottom: 30px; display: flex; justify-content: space-between; align-items: flex-start; }}
    .title {{ font-size: 1.6rem; font-weight: 800; color: #0f392b; margin: 0 0 5px 0; }}
    .subtitle {{ color: #64748b; font-size: 0.95rem; margin: 0; }}
    .meta-box {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 25px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; font-size: 0.85rem; }}
    .meta-item strong {{ display: block; color: #64748b; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 3px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 15px 0 30px 0; font-size: 0.85rem; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; }}
    th {{ background: #f1f5f9; color: #334155; font-weight: 700; }}
    .summary-card {{ background: #f0fdf4; border-left: 4px solid #16a34a; padding: 15px; border-radius: 4px; margin-bottom: 25px; }}
    .badge-verified {{ color: #059669; font-weight: 700; background: #d1fae5; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; }}
    .badge-obs {{ color: #d97706; font-weight: 700; background: #fef3c7; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; }}
    @media print {{ body {{ margin: 15mm; }} button {{ display: none; }} }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1 class="title">AgroTrack AI — ImpactOS Monitoring & Evaluation Report</h1>
      <p class="subtitle">{report['projectName']} | Reporting Period: <strong>{report['reportingPeriod']}</strong></p>
    </div>
    <div style="text-align: right;">
      <button onclick="window.print()" style="padding: 8px 16px; background: #0f392b; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">Print / Save as PDF</button>
    </div>
  </div>

  <div class="meta-box">
    <div class="meta-item"><strong>Programme</strong> {report['projectName']}</div>
    <div class="meta-item"><strong>Reporting Period</strong> {report['reportingPeriod']}</div>
    <div class="meta-item"><strong>Compiled By</strong> {report['generatedBy']}</div>
    <div class="meta-item"><strong>Audited Date</strong> {report['generatedAt'][:10]}</div>
  </div>

  <div class="summary-card">
    <h3 style="margin: 0 0 8px 0; color: #166534; font-size: 1rem;">Executive Performance Summary</h3>
    <p style="margin: 0; font-size: 0.9rem; color: #14532d;">{report['executiveSummary']}</p>
  </div>

  <h3 style="color: #0f392b; margin-top: 30px; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px;">1. Performance Indicators & Target Progress</h3>
  <table>
    <thead>
      <tr>
        <th>Code</th>
        <th>Indicator Title</th>
        <th>Category</th>
        <th style="text-align: right;">Baseline</th>
        <th style="text-align: right;">Target</th>
        <th style="text-align: right;">Current</th>
        <th>Unit</th>
        <th style="text-align: right;">Progress</th>
        <th>Status</th>
        <th>Verification</th>
      </tr>
    </thead>
    <tbody>
      {indicator_rows}
    </tbody>
  </table>

  <h3 style="color: #0f392b; margin-top: 30px; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px;">2. Beneficiary Demographics</h3>
  <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 25px;">
    <div style="background: #f8fafc; padding: 15px; border-radius: 6px; border: 1px solid #e2e8f0; text-align: center;">
      <div style="font-size: 1.8rem; font-weight: 800; color: #0f392b;">{bs.get('totalBeneficiaries', 0)}</div>
      <div style="font-size: 0.8rem; color: #64748b; text-transform: uppercase;">Total Reached</div>
    </div>
    <div style="background: #f8fafc; padding: 15px; border-radius: 6px; border: 1px solid #e2e8f0; text-align: center;">
      <div style="font-size: 1.8rem; font-weight: 800; color: #0284c7;">{bs.get('femalePercent', 0)}%</div>
      <div style="font-size: 0.8rem; color: #64748b; text-transform: uppercase;">Female Participation ({bs.get('femaleCount', 0)})</div>
    </div>
    <div style="background: #f8fafc; padding: 15px; border-radius: 6px; border: 1px solid #e2e8f0; text-align: center;">
      <div style="font-size: 1.8rem; font-weight: 800; color: #7c3aed;">{bs.get('youthPercent', 0)}%</div>
      <div style="font-size: 0.8rem; color: #64748b; text-transform: uppercase;">Youth Agripreneurs ({bs.get('youthCount', 0)})</div>
    </div>
  </div>

  <h3 style="color: #0f392b; margin-top: 30px; border-bottom: 1px solid #cbd5e1; padding-bottom: 6px;">3. Audit Distinction: Verified Results vs Field Observations</h3>
  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 15px;">
      <h4 style="margin: 0 0 10px 0; color: #166534;"><span class="badge-verified">Audited</span> Verified Results ({len(verified_results)})</h4>
      <ul style="margin: 0; padding-left: 20px; font-size: 0.85rem; color: #15803d;">
        {"".join([f"<li><strong>{v.get('title') or v.get('code')}:</strong> {v.get('current', '')} {v.get('unit', '')} — <em>{v.get('verificationSource', 'Audited')}</em></li>" for v in verified_results]) or "<li>No verified results in period</li>"}
      </ul>
    </div>
    <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 15px;">
      <h4 style="margin: 0 0 10px 0; color: #92400e;"><span class="badge-obs">Unverified</span> Field Observations ({len(field_obs)})</h4>
      <ul style="margin: 0; padding-left: 20px; font-size: 0.85rem; color: #b45309;">
        {"".join([f"<li><strong>{o.get('title') or o.get('code')}:</strong> {o.get('attendance') or o.get('current', '')} — <em>Field staff notes</em></li>" for o in field_obs]) or "<li>No unverified observations</li>"}
      </ul>
    </div>
  </div>

  <div style="margin-top: 40px; border-top: 1px solid #cbd5e1; padding-top: 15px; font-size: 0.75rem; color: #94a3b8; text-align: center;">
    AgroTrack AI Platform — ImpactOS Accountability & Donor Reporting Engine &bull; Confidential &bull; Generated {report['generatedAt']}
  </div>
</body>
</html>"""
