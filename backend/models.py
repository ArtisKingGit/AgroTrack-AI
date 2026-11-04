"""
AgroTrack AI Core Domain Models & Schemas
Defines platform roles, permissions, user profiles, organisation entities, and dashboard schemas.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class Role(str, Enum):
    ORGANISATION_ADMIN = "Organisation Administrator"
    PROJECT_MANAGER = "Project Manager"
    FIELD_OFFICER = "Field Officer"
    ANALYST = "Analyst"
    VIEWER = "Viewer"


class Permission(str, Enum):
    ORG_MANAGE = "org:manage"
    MEMBERS_MANAGE = "members:manage"
    PROJECTS_MANAGE = "projects:manage"
    PROJECTS_VIEW = "projects:view"
    FARMERS_MANAGE = "farmers:manage"
    FARMS_WRITE = "farms:write"
    FARMS_READ = "farms:read"
    SCANS_EXECUTE = "scans:execute"
    SCANS_READ = "scans:read"
    MARKET_READ = "market:read"
    MARKET_WRITE = "market:write"
    IMPACT_READ = "impact:read"
    IMPACT_WRITE = "impact:write"
    ANALYST_QUERY = "analyst:query"


# Explicit Role-to-Permissions Mapping
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.ORGANISATION_ADMIN: [
        Permission.ORG_MANAGE,
        Permission.MEMBERS_MANAGE,
        Permission.PROJECTS_MANAGE,
        Permission.PROJECTS_VIEW,
        Permission.FARMERS_MANAGE,
        Permission.FARMS_WRITE,
        Permission.FARMS_READ,
        Permission.SCANS_EXECUTE,
        Permission.SCANS_READ,
        Permission.MARKET_READ,
        Permission.MARKET_WRITE,
        Permission.IMPACT_READ,
        Permission.IMPACT_WRITE,
        Permission.ANALYST_QUERY,
    ],
    Role.PROJECT_MANAGER: [
        Permission.PROJECTS_MANAGE,
        Permission.PROJECTS_VIEW,
        Permission.FARMERS_MANAGE,
        Permission.FARMS_WRITE,
        Permission.FARMS_READ,
        Permission.SCANS_EXECUTE,
        Permission.SCANS_READ,
        Permission.MARKET_READ,
        Permission.MARKET_WRITE,
        Permission.IMPACT_READ,
        Permission.IMPACT_WRITE,
        Permission.ANALYST_QUERY,
    ],
    Role.FIELD_OFFICER: [
        Permission.PROJECTS_VIEW,
        Permission.FARMERS_MANAGE,
        Permission.FARMS_WRITE,
        Permission.FARMS_READ,
        Permission.SCANS_EXECUTE,
        Permission.SCANS_READ,
        Permission.MARKET_READ,
        Permission.MARKET_WRITE,
        Permission.IMPACT_READ,
        Permission.ANALYST_QUERY,
    ],
    Role.ANALYST: [
        Permission.PROJECTS_VIEW,
        Permission.FARMS_READ,
        Permission.SCANS_READ,
        Permission.MARKET_READ,
        Permission.MARKET_WRITE,
        Permission.IMPACT_READ,
        Permission.ANALYST_QUERY,
    ],
    Role.VIEWER: [
        Permission.PROJECTS_VIEW,
        Permission.FARMS_READ,
        Permission.SCANS_READ,
        Permission.MARKET_READ,
        Permission.IMPACT_READ,
    ],
}


class UserProfile(BaseModel):
    uid: str
    email: str
    name: str
    activeRole: Role
    defaultOrgId: str
    permissions: List[str] = Field(default_factory=list)
    photo: Optional[str] = None


class ActivityType(str, Enum):
    FARM_VISIT = "farm_visit"
    CROP_INSPECTION = "crop_inspection"
    PLANTING = "planting"
    HARVEST = "harvest"
    IRRIGATION = "irrigation"
    FERTILIZER_APPLICATION = "fertilizer_application"
    OTHER = "other"


class FarmerLocation(BaseModel):
    county: str = "Nakuru"
    subCounty: Optional[str] = "Rongai"
    ward: Optional[str] = "Solai"
    village: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)


class Farmer(BaseModel):
    id: str
    orgId: str
    farmerCode: str
    nationalId: Optional[str] = None
    firstName: str
    lastName: str
    phone: Optional[str] = None
    gender: str = "unspecified"
    location: FarmerLocation = Field(default_factory=FarmerLocation)
    assignedFieldOfficerId: Optional[str] = None
    assignedFieldOfficerName: Optional[str] = None
    enrolledProjectIds: List[str] = Field(default_factory=list)
    totalAcreage: float = 0.0
    status: str = "active"  # "active" or "archived"
    consentGiven: bool = True
    registeredAt: str
    updatedAt: Optional[str] = None


class FarmerCreateRequest(BaseModel):
    firstName: str = Field(..., min_length=2, json_schema_extra={"example": "Joseph"})
    lastName: str = Field(..., min_length=2, json_schema_extra={"example": "Kamau"})
    farmerCode: Optional[str] = Field(None, json_schema_extra={"example": "FM-2026-001"})
    nationalId: Optional[str] = Field(None, json_schema_extra={"example": "24981023"})
    phone: Optional[str] = Field(None, json_schema_extra={"example": "+254722998877"})
    gender: str = Field("unspecified", json_schema_extra={"example": "male"})
    location: Optional[Dict[str, Any]] = None
    assignedFieldOfficerId: Optional[str] = None
    enrolledProjectIds: List[str] = Field(default_factory=list)
    totalAcreage: float = Field(0.0, ge=0.0)
    consentGiven: bool = True


class FarmerUpdateRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    assignedFieldOfficerId: Optional[str] = None
    enrolledProjectIds: Optional[List[str]] = None
    totalAcreage: Optional[float] = None
    status: Optional[str] = None
    consentGiven: Optional[bool] = None


class FieldActivity(BaseModel):
    id: str
    orgId: str
    farmId: str
    farmerId: Optional[str] = None
    farmName: Optional[str] = None
    farmerName: Optional[str] = None
    activityType: ActivityType
    activityDate: str
    responsibleUserId: str
    responsibleUserName: str
    notes: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    observations: List[str] = Field(default_factory=list)
    createdAt: str

    @field_validator("activityType", mode="before")
    @classmethod
    def normalize_activity_type(cls, v):
        if isinstance(v, ActivityType):
            return v
        if not v:
            return ActivityType.OTHER
        s = str(v).lower().replace(" ", "_").replace("-", "_")
        for member in ActivityType:
            if member.value == s:
                return member
        return ActivityType.OTHER


class FieldActivityCreateRequest(BaseModel):
    farmId: str = Field(..., json_schema_extra={"example": "farm_gv_101"})
    farmerId: Optional[str] = None
    activityType: ActivityType = Field(ActivityType.FARM_VISIT, json_schema_extra={"example": "farm_visit"})
    activityDate: Optional[str] = None
    notes: str = Field(..., min_length=3, json_schema_extra={"example": "Conducted routine leaf canopy inspection and checked drip pressure."})
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    observations: Optional[List[str]] = Field(default_factory=list)

    @field_validator("activityType", mode="before")
    @classmethod
    def normalize_activity_type(cls, v):
        if isinstance(v, ActivityType):
            return v
        if not v:
            return ActivityType.OTHER
        s = str(v).lower().replace(" ", "_").replace("-", "_")
        for member in ActivityType:
            if member.value == s:
                return member
        return ActivityType.OTHER


class OfflineActivitySyncItem(BaseModel):
    clientMutationId: str = Field(..., min_length=4, json_schema_extra={"example": "mut_offline_1730712345_a1b2"})
    farmId: str = Field(..., json_schema_extra={"example": "farm_gv_101"})
    farmerId: Optional[str] = None
    activityType: ActivityType = Field(ActivityType.FARM_VISIT, json_schema_extra={"example": "farm_visit"})
    activityDate: Optional[str] = None
    notes: str = Field(..., min_length=1, json_schema_extra={"example": "Recorded offline: Crop inspection confirmed healthy vegetative stage."})
    metrics: Optional[Dict[str, Any]] = Field(default_factory=dict)
    observations: Optional[List[str]] = Field(default_factory=list)
    clientCreatedAt: Optional[str] = None
    lastKnownServerUpdatedAt: Optional[str] = None

    @field_validator("activityType", mode="before")
    @classmethod
    def normalize_activity_type(cls, v):
        if isinstance(v, ActivityType):
            return v
        if not v:
            return ActivityType.OTHER
        s = str(v).lower().replace(" ", "_").replace("-", "_")
        for member in ActivityType:
            if member.value == s:
                return member
        return ActivityType.OTHER


class OfflineSyncBatchRequest(BaseModel):
    batch: List[OfflineActivitySyncItem] = Field(..., min_length=1)


class OfflineSyncResponse(BaseModel):
    totalReceived: int
    syncedCount: int
    conflictCount: int
    duplicateCount: int
    synced: List[Dict[str, Any]]
    conflicts: List[Dict[str, Any]]
    duplicates: List[Dict[str, Any]]
    timestamp: str


class AgroTrackDashboardStats(BaseModel):
    totalFarmers: int
    activeFarmers: int
    archivedFarmers: int
    totalFarms: int
    totalAcreage: float
    totalActivities: int
    totalVisits: int
    activeCropsCount: Dict[str, int]
    recentActivities: List[Dict[str, Any]]


class Organisation(BaseModel):
    id: str
    name: str
    code: str
    tier: str = "enterprise"
    country: str = "Kenya"
    currency: str = "KES"
    createdAt: str


class OrganisationMember(BaseModel):
    userId: str
    name: str
    email: str
    role: Role
    status: str = "active"
    joinedAt: str


class ProjectSummary(BaseModel):
    id: str
    name: str
    code: str
    status: str
    targetBeneficiaries: int
    enrolledFarmers: int
    budget: float
    currency: str = "KES"


class PlatformMetrics(BaseModel):
    activeFarms: int = 0
    monitoredAcreage: float = 0.0
    registeredFarmers: int = 0
    diagnosticScans: int = 0
    activeProjects: int = 0


class ModuleStatus(BaseModel):
    id: str
    name: str
    description: str
    status: str  # "active", "development", "planned"
    phase: str
    icon: str
    route: str


class PlatformOverview(BaseModel):
    organisation: Organisation
    user: UserProfile
    metrics: PlatformMetrics
    modules: List[ModuleStatus]
    projects: List[ProjectSummary]
    recentActivity: List[Dict[str, Any]] = Field(default_factory=list)


# ── MarketLens Domain Schemas (Phase 4) ───────────────────────────────────────

class CommodityCategory(str, Enum):
    CEREALS_GRAINS = "Cereals & Grains"
    LEGUMES_PULSES = "Legumes & Pulses"
    HORTICULTURE_VEGETABLES = "Horticulture & Vegetables"
    FRUITS = "Fruits"
    ROOTS_TUBERS = "Roots & Tubers"
    CASH_CROPS = "Cash Crops / Industrial"
    OTHER = "Other"

    @classmethod
    def _missing_(cls, value):
        s = str(value).strip().lower()
        if "cash" in s or "export" in s or "industrial" in s:
            return cls.CASH_CROPS
        return None


class PriceType(str, Enum):
    WHOLESALE = "wholesale"
    RETAIL = "retail"
    FARMGATE = "farmgate"


class CollectionMethod(str, Enum):
    MANUAL = "manual"
    IMPORTED = "imported"

    @classmethod
    def _missing_(cls, value):
        s = str(value).lower()
        if "import" in s:
            return cls.IMPORTED
        if "manual" in s:
            return cls.MANUAL
        return None


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"


class Commodity(BaseModel):
    id: str
    orgId: str
    name: str
    code: str
    category: CommodityCategory
    standardUnit: str = "kg"
    supportedUnits: List[str] = Field(default_factory=lambda: ["kg"])
    varieties: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    isActive: bool = True
    createdAt: str


class CommodityCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, json_schema_extra={"example": "White Maize"})
    code: Optional[str] = Field(None, json_schema_extra={"example": "CMD-MZ-01"})
    category: CommodityCategory = Field(CommodityCategory.CEREALS_GRAINS, json_schema_extra={"example": "Cereals & Grains"})
    standardUnit: str = Field("90kg bag", json_schema_extra={"example": "90kg bag"})
    supportedUnits: Optional[List[str]] = Field(default_factory=lambda: ["90kg bag", "50kg bag", "kg"])
    varieties: Optional[List[str]] = Field(default_factory=list, json_schema_extra={"example": ["H614D", "Duma 43"]})
    description: Optional[str] = None


class CommodityUpdateRequest(BaseModel):
    name: Optional[str] = None
    category: Optional[CommodityCategory] = None
    standardUnit: Optional[str] = None
    supportedUnits: Optional[List[str]] = None
    varieties: Optional[List[str]] = None
    description: Optional[str] = None
    isActive: Optional[bool] = None


class MarketPriceRecord(BaseModel):
    id: str
    orgId: str
    commodityId: str
    commodityName: str
    variety: Optional[str] = None
    marketName: str
    marketLocation: Dict[str, Any] = Field(default_factory=dict)
    priceType: PriceType
    price: float
    unit: str
    normalizedPricePerKg: float
    currency: str = "KES"
    dateCollected: str
    dataSource: str
    collectorName: str
    collectorUserId: Optional[str] = None
    collectionMethod: CollectionMethod = CollectionMethod.MANUAL
    verificationStatus: VerificationStatus = VerificationStatus.UNVERIFIED
    verifiedBy: Optional[str] = None
    verifiedAt: Optional[str] = None
    notes: Optional[str] = None
    isHistorical: bool = False
    recordAgeDays: int = 0
    freshnessLabel: str = "Current"
    createdAt: str


class MarketPriceCreateRequest(BaseModel):
    commodityId: str = Field(..., json_schema_extra={"example": "cmd_maize"})
    variety: Optional[str] = Field(None, json_schema_extra={"example": "White Maize (H614D)"})
    marketName: str = Field(..., min_length=2, json_schema_extra={"example": "Wakulima Wholesale Market"})
    marketLocation: Optional[Dict[str, Any]] = Field(default_factory=lambda: {"county": "Nairobi", "region": "Central"})
    priceType: PriceType = Field(PriceType.WHOLESALE, json_schema_extra={"example": "wholesale"})
    price: float = Field(..., gt=0.0, json_schema_extra={"example": 4500.0})
    unit: str = Field("90kg bag", json_schema_extra={"example": "90kg bag"})
    currency: str = Field("KES", json_schema_extra={"example": "KES"})
    dateCollected: Optional[str] = Field(None, json_schema_extra={"example": "2026-11-04"})
    dataSource: str = Field(..., min_length=2, json_schema_extra={"example": "Ministry of Agriculture Market Information System"})
    notes: Optional[str] = None
    collectionMethod: CollectionMethod = Field(CollectionMethod.MANUAL, json_schema_extra={"example": "manual"})
    verificationStatus: VerificationStatus = Field(VerificationStatus.UNVERIFIED, json_schema_extra={"example": "unverified"})


class MarketResearch(BaseModel):
    id: str
    orgId: str
    title: str
    location: str
    researchDate: str
    commodityId: Optional[str] = None
    commodityName: Optional[str] = None
    valueChainStage: str
    findings: str
    sourceReferences: List[str] = Field(default_factory=list)
    attachments: List[str] = Field(default_factory=list)
    authorId: str
    authorName: str
    createdAt: str


class MarketResearchCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, json_schema_extra={"example": "Post-Harvest Maize Spatial Arbitrage"})
    location: str = Field(..., min_length=2, json_schema_extra={"example": "Uasin Gishu & Trans Nzoia"})
    researchDate: Optional[str] = Field(None, json_schema_extra={"example": "2026-10-15"})
    commodityId: Optional[str] = None
    valueChainStage: str = Field("Farmgate to Wholesale", json_schema_extra={"example": "Farmgate to Wholesale"})
    findings: str = Field(..., min_length=10, json_schema_extra={"example": "High transportation costs from North Rift to Nairobi create an 18% wholesale spread."})
    sourceReferences: List[str] = Field(default_factory=list, json_schema_extra={"example": ["KNBS Economic Survey", "MoA Field Survey"]})
    attachments: Optional[List[str]] = Field(default_factory=list)


class MarketLensDashboardStats(BaseModel):
    totalCommodities: int
    totalPriceRecords: int
    verifiedPriceRecords: int
    unverifiedPriceRecords: int
    manualPriceRecords: int
    importedPriceRecords: int
    freshRecordsCount: int
    historicalRecordsCount: int
    totalResearchStudies: int
    monitoredMarkets: List[str]
    recentPriceUpdates: List[Dict[str, Any]]
    recentActivity: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


# ── ImpactOS Enums & Models ──────────────────────────────────────────────────

class ProjectStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class BeneficiaryCategory(str, Enum):
    SMALLHOLDER_FARMER = "smallholder_farmer"
    PASTORALIST = "pastoralist"
    WOMEN_COOPERATIVE = "women_cooperative"
    YOUTH_AGRIPRENEUR = "youth_agripreneur"
    INPUT_DEALER = "input_dealer"
    VULNERABLE_HOUSEHOLD = "vulnerable_household"
    OTHER = "other"


class ParticipationStatus(str, Enum):
    ENROLLED = "enrolled"
    ACTIVE = "active"
    GRADUATED = "graduated"
    DROPPED = "dropped"
    COMPLETED = "completed"


class IndicatorCategory(str, Enum):
    OUTPUT = "output"
    OUTCOME = "outcome"
    IMPACT = "impact"


class ReportingFrequency(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"


class IndicatorStatus(str, Enum):
    ON_TRACK = "on_track"
    BEHIND = "behind"
    ACHIEVED = "achieved"
    CRITICAL = "critical"


class ImpactActivityType(str, Enum):
    TRAINING_WORKSHOP = "training_workshop"
    INPUT_DISTRIBUTION = "input_distribution"
    FIELD_DEMONSTRATION = "field_demonstration"
    COOPERATIVE_MEETING = "cooperative_meeting"
    POST_HARVEST_ASSESSMENT = "post_harvest_assessment"
    MONITORING_VISIT = "monitoring_visit"
    OTHER = "other"


class ImpactActivityStatus(str, Enum):
    PLANNED = "planned"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ── Project Schemas ──────────────────────────────────────────────────────────

class Project(BaseModel):
    id: str
    orgId: str
    name: str
    code: str
    description: str
    locations: List[Dict[str, Any]] = Field(default_factory=list)
    projectManagerId: Optional[str] = None
    projectManagerName: Optional[str] = None
    startDate: str
    endDate: str
    status: ProjectStatus = ProjectStatus.ACTIVE
    budget: float = 0.0
    currency: str = "KES"
    targetBeneficiaries: int = 0
    enrolledBeneficiariesCount: int = 0
    objectives: List[Dict[str, Any]] = Field(default_factory=list)
    sectors: List[str] = Field(default_factory=list)
    donor: Optional[str] = None
    isArchived: bool = False
    createdAt: str
    updatedAt: Optional[str] = None


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, json_schema_extra={"example": "Smallholder Maize Climate Resilience Initiative"})
    code: str = Field(..., min_length=2, json_schema_extra={"example": "SMCRI-2026"})
    description: str = Field(..., min_length=5, json_schema_extra={"example": "Climate-smart agronomic interventions for vulnerable maize smallholders."})
    locations: Optional[List[Dict[str, Any]]] = Field(default_factory=list, json_schema_extra={"example": [{"county": "Nakuru", "subCounty": "Rongai"}]})
    projectManagerId: Optional[str] = Field(None, json_schema_extra={"example": "usr_mgr_002"})
    projectManagerName: Optional[str] = Field(None, json_schema_extra={"example": "David Kiprop"})
    startDate: str = Field(..., json_schema_extra={"example": "2026-01-15"})
    endDate: str = Field(..., json_schema_extra={"example": "2026-12-31"})
    status: Optional[ProjectStatus] = Field(ProjectStatus.ACTIVE, json_schema_extra={"example": "active"})
    budget: float = Field(0.0, ge=0.0, json_schema_extra={"example": 4500000.0})
    currency: str = Field("KES", json_schema_extra={"example": "KES"})
    targetBeneficiaries: int = Field(..., ge=1, json_schema_extra={"example": 1200})
    objectives: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    sectors: Optional[List[str]] = Field(default_factory=list, json_schema_extra={"example": ["Climate Resilience", "Food Security"]})
    donor: Optional[str] = Field(None, json_schema_extra={"example": "USAID Feed the Future"})


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    locations: Optional[List[Dict[str, Any]]] = None
    projectManagerId: Optional[str] = None
    projectManagerName: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    status: Optional[ProjectStatus] = None
    budget: Optional[float] = None
    targetBeneficiaries: Optional[int] = None
    objectives: Optional[List[Dict[str, Any]]] = None
    sectors: Optional[List[str]] = None
    donor: Optional[str] = None
    isArchived: Optional[bool] = None


# ── Beneficiary Schemas ──────────────────────────────────────────────────────

class Beneficiary(BaseModel):
    id: str
    orgId: str
    beneficiaryCode: str
    firstName: str
    lastName: str
    category: BeneficiaryCategory
    gender: str = "unspecified"
    ageGroup: Optional[str] = None
    location: Dict[str, Any] = Field(default_factory=dict)
    linkedFarmerId: Optional[str] = None
    phone: Optional[str] = None
    nationalId: Optional[str] = None
    enrolledProjects: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = "active"
    createdAt: str
    updatedAt: Optional[str] = None


class BeneficiaryCreateRequest(BaseModel):
    firstName: str = Field(..., min_length=2, json_schema_extra={"example": "Mary"})
    lastName: str = Field(..., min_length=2, json_schema_extra={"example": "Wambui"})
    category: BeneficiaryCategory = Field(BeneficiaryCategory.SMALLHOLDER_FARMER, json_schema_extra={"example": "smallholder_farmer"})
    gender: str = Field("female", json_schema_extra={"example": "female"})
    ageGroup: Optional[str] = Field("youth_18_35", json_schema_extra={"example": "youth_18_35"})
    location: Optional[Dict[str, Any]] = Field(default_factory=lambda: {"county": "Nakuru", "subCounty": "Rongai", "ward": "Solai"})
    linkedFarmerId: Optional[str] = None
    phone: Optional[str] = Field(None, json_schema_extra={"example": "+254722123456"})
    nationalId: Optional[str] = Field(None, json_schema_extra={"example": "29871120"})
    projectId: Optional[str] = Field(None, json_schema_extra={"example": "proj_smcri_2026"})
    enrolmentDate: Optional[str] = Field(None, json_schema_extra={"example": "2026-02-01"})
    participationStatus: Optional[ParticipationStatus] = Field(ParticipationStatus.ENROLLED, json_schema_extra={"example": "enrolled"})
    supportReceived: Optional[List[str]] = Field(default_factory=list, json_schema_extra={"example": ["Drought-Tolerant Seeds", "GAP Training"]})


class BeneficiaryUpdateRequest(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    category: Optional[BeneficiaryCategory] = None
    gender: Optional[str] = None
    ageGroup: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    phone: Optional[str] = None
    nationalId: Optional[str] = None
    status: Optional[str] = None


# ── Indicator Schemas ────────────────────────────────────────────────────────

class Indicator(BaseModel):
    id: str
    orgId: str
    projectId: str
    projectName: str
    name: str
    code: str
    description: str
    category: IndicatorCategory
    unit: str
    baselineValue: float = 0.0
    targetValue: float
    currentValue: float = 0.0
    progressPercent: float = 0.0
    reportingFrequency: ReportingFrequency = ReportingFrequency.QUARTERLY
    status: IndicatorStatus = IndicatorStatus.ON_TRACK
    isVerified: bool = False
    verificationSource: Optional[str] = None
    lastReportedDate: Optional[str] = None
    createdAt: str


class IndicatorCreateRequest(BaseModel):
    projectId: str = Field(..., json_schema_extra={"example": "proj_smcri_2026"})
    name: str = Field(..., min_length=3, json_schema_extra={"example": "Hectares under Climate-Smart Agriculture"})
    code: str = Field(..., min_length=2, json_schema_extra={"example": "IND-CSA-01"})
    description: str = Field(..., min_length=5, json_schema_extra={"example": "Total agricultural area adopting conservation tillage and certified seed."})
    category: IndicatorCategory = Field(IndicatorCategory.OUTPUT, json_schema_extra={"example": "output"})
    unit: str = Field("hectares", json_schema_extra={"example": "hectares"})
    baselineValue: float = Field(0.0, ge=0.0, json_schema_extra={"example": 0.0})
    targetValue: float = Field(..., gt=0.0, json_schema_extra={"example": 500.0})
    currentValue: Optional[float] = Field(0.0, ge=0.0, json_schema_extra={"example": 0.0})
    reportingFrequency: ReportingFrequency = Field(ReportingFrequency.QUARTERLY, json_schema_extra={"example": "quarterly"})


class IndicatorUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    targetValue: Optional[float] = None
    unit: Optional[str] = None
    reportingFrequency: Optional[ReportingFrequency] = None


class IndicatorProgressRecordRequest(BaseModel):
    period: str = Field(..., min_length=2, json_schema_extra={"example": "Q3-2026"})
    measuredValue: float = Field(..., ge=0.0, json_schema_extra={"example": 380.0})
    measurementDate: Optional[str] = Field(None, json_schema_extra={"example": "2026-09-30"})
    source: str = Field(..., min_length=3, json_schema_extra={"example": "Field Officer M&E Bi-Weekly Plot Audit"})
    notes: Optional[str] = Field(None, json_schema_extra={"example": "Significant expansion observed across Solai ward."})
    isVerified: bool = Field(False, json_schema_extra={"example": True})
    verificationSource: Optional[str] = Field(None, json_schema_extra={"example": "Independent Mid-Term Evaluation Team"})


# ── Activity Schemas ─────────────────────────────────────────────────────────

class ImpactActivity(BaseModel):
    id: str
    orgId: str
    projectId: str
    projectName: str
    title: str
    activityType: ImpactActivityType
    activityDate: str
    location: str
    responsibleStaffId: str
    responsibleStaffName: str
    targetAttendance: int = 0
    actualAttendance: int = 0
    femaleAttendance: int = 0
    maleAttendance: int = 0
    youthAttendance: int = 0
    outputs: List[str] = Field(default_factory=list)
    supportingNotes: Optional[str] = None
    evidenceAttachments: List[str] = Field(default_factory=list)
    status: ImpactActivityStatus = ImpactActivityStatus.COMPLETED
    isVerified: bool = False
    createdAt: str


class ImpactActivityCreateRequest(BaseModel):
    projectId: str = Field(..., json_schema_extra={"example": "proj_smcri_2026"})
    title: str = Field(..., min_length=3, json_schema_extra={"example": "GAP & Soil Sampling Demonstration Workshop"})
    activityType: ImpactActivityType = Field(ImpactActivityType.FIELD_DEMONSTRATION, json_schema_extra={"example": "field_demonstration"})
    activityDate: Optional[str] = Field(None, json_schema_extra={"example": "2026-10-18"})
    location: str = Field(..., min_length=2, json_schema_extra={"example": "Solai Farmers Cooperative Hall"})
    responsibleStaffId: Optional[str] = None
    responsibleStaffName: Optional[str] = None
    targetAttendance: int = Field(0, ge=0, json_schema_extra={"example": 60})
    actualAttendance: int = Field(0, ge=0, json_schema_extra={"example": 54})
    femaleAttendance: int = Field(0, ge=0, json_schema_extra={"example": 32})
    maleAttendance: int = Field(0, ge=0, json_schema_extra={"example": 22})
    youthAttendance: int = Field(0, ge=0, json_schema_extra={"example": 26})
    outputs: List[str] = Field(default_factory=list, json_schema_extra={"example": ["54 farmers trained in soil sampling", "20 demo soil test kits deployed"]})
    supportingNotes: Optional[str] = None
    evidenceAttachments: Optional[List[str]] = Field(default_factory=list)
    status: ImpactActivityStatus = Field(ImpactActivityStatus.COMPLETED, json_schema_extra={"example": "completed"})
    isVerified: bool = Field(False, json_schema_extra={"example": False})


class ImpactActivityUpdateRequest(BaseModel):
    title: Optional[str] = None
    activityType: Optional[ImpactActivityType] = None
    activityDate: Optional[str] = None
    location: Optional[str] = None
    targetAttendance: Optional[int] = None
    actualAttendance: Optional[int] = None
    femaleAttendance: Optional[int] = None
    maleAttendance: Optional[int] = None
    youthAttendance: Optional[int] = None
    outputs: Optional[List[str]] = None
    supportingNotes: Optional[str] = None
    status: Optional[ImpactActivityStatus] = None
    isVerified: Optional[bool] = None


# ── Report & Dashboard Schemas ───────────────────────────────────────────────

class ReportGenerateRequest(BaseModel):
    projectId: Optional[str] = Field(None, json_schema_extra={"example": "proj_smcri_2026"})
    reportingPeriod: str = Field(..., min_length=2, json_schema_extra={"example": "Q3-2026"})
    includeUnverified: bool = Field(True, json_schema_extra={"example": True})
    challenges: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


class ImpactReport(BaseModel):
    reportId: str
    orgId: str
    projectId: Optional[str] = None
    projectName: str
    reportingPeriod: str
    generatedAt: str
    generatedBy: str
    projectOverview: Dict[str, Any]
    objectives: List[Dict[str, Any]]
    beneficiaryStats: Dict[str, Any]
    indicatorPerformance: List[Dict[str, Any]]
    verifiedResults: List[Dict[str, Any]]
    fieldObservations: List[Dict[str, Any]]
    activitiesSummary: Dict[str, Any]
    challengesAndMitigations: List[Dict[str, Any]]
    executiveSummary: str


class ImpactOSDashboardStats(BaseModel):
    activeProjectsCount: int
    completedProjectsCount: int
    totalBeneficiariesCount: int
    femaleBeneficiariesPercent: float
    youthBeneficiariesPercent: float
    totalIndicatorsCount: int
    overallTargetProgressPercent: float
    completedActivitiesCount: int
    indicatorPerformanceBreakdown: Dict[str, int]
    totalBudget: float
    currency: str = "KES"
    recentActivities: List[Dict[str, Any]] = Field(default_factory=list)


# ── AI Analyst Schemas ───────────────────────────────────────────────────────

class AnalystMessage(BaseModel):
    role: str = Field(..., json_schema_extra={"example": "user"})
    content: str = Field(..., json_schema_extra={"example": "Which projects are falling behind their targets?"})


class AnalystSource(BaseModel):
    type: str
    id: str
    title: str
    date: Optional[str] = None
    snippet: Optional[str] = None
    module: str


class AnalystQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, json_schema_extra={"example": "Which projects are falling behind their targets?"})
    history: Optional[List[AnalystMessage]] = Field(default_factory=list)
    scope: Optional[List[str]] = Field(default_factory=list, json_schema_extra={"example": ["agrotrack", "marketlens", "impactos"]})
    projectId: Optional[str] = None
    farmId: Optional[str] = None


class AnalystQueryResponse(BaseModel):
    query: str
    answer: str
    facts: List[str] = Field(default_factory=list)
    estimates: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    sources: List[AnalystSource] = Field(default_factory=list)
    dataGrounded: bool = True
    missingDataNotice: Optional[str] = None
    suggestedFollowUps: List[str] = Field(default_factory=list)
    timestamp: str


class AnalystCapability(BaseModel):
    id: str
    category: str
    title: str
    description: str
    exampleQuestions: List[str]
