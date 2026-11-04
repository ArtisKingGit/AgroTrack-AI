# AgroTrack AI: Shared Data Model Architecture

**Platform Identity:** AgroTrack AI — Agricultural Intelligence and Development Management Platform  
**Document Version:** 1.0.0 (Phase 1 Foundation)  
**Database Technology:** Firebase Realtime Database (RTDB) / Pydantic v2 Core Schemas  
**Migration Strategy:** Non-Destructive Evolutionary Extension (Preserves existing AgroFast data)

---

## 1. Architectural Philosophy & Compatibility

AgroTrack AI expands the single-user, plot-level capabilities of AgroFast into an enterprise multi-tenant platform spanning four core modules:
1. **AgroTrack**: Farmer, farm, field, plot, and agricultural activity management.
2. **MarketLens**: Agricultural market research, commodity pricing, and value-chain intelligence.
3. **ImpactOS**: Project management, beneficiary tracking, targets, and impact reporting.
4. **AI Analyst**: An intelligence layer bridging farm data, market dynamics, and impact metrics.

### Non-Destructive Data Principles
1. **Backward Compatibility**: Existing AgroFast paths under `/users/{uid}/` (`farms`, `expenses`, `history`, `settings`) remain completely readable and functional.
2. **Organization Partitioning**: New enterprise entities are organized under an organization-scoped namespace (`/organisations/{orgId}/`) to ensure multi-tenant security and zero cross-tenant leakage.
3. **Dual-Read / Soft-Link Adapter**: Individual user farms can optionally reference an `orgId` and `farmerId` without requiring structural schema alteration of existing records.

---

## 2. Shared Data Model Specifications

```
                                  +---------------------+
                                  |     Organisation    |
                                  +----------+----------+
                                             |
                         +-------------------+-------------------+
                         | 1:N               | 1:N               | 1:N
                         v                   v                   v
              +--------------------+  +--------------+  +-----------------+
              |    Memberships     |  |   Projects   |  |     Farmers     |
              +----------+---------+  +-------+------+  +--------+--------+
                         |                    |                  |
                         | N:1                | 1:N              | 1:N
                         v                    v                  v
                  +--------------+     +-------------+    +---------------+
                  |    Users     |     |   Targets   |    | Farms / Plots |
                  +--------------+     +-------------+    +-------+-------+
                                                                  |
                                                        +---------+---------+
                                                        | 1:N               | 1:N
                                                        v                   v
                                                +---------------+   +---------------+
                                                |   Expenses    |   | Diagnostic    |
                                                |   & Budgets   |   | Scans         |
                                                +---------------+   +---------------+
```

---

## 3. Entity Definitions & Schema Details

### 3.1 Organisation (`/organisations/{orgId}`)
The top-level tenant entity representing an agricultural cooperative, NGO, agribusiness enterprise, or research institution.

```json
{
  "id": "org_gv_2026_01",
  "name": "GreenValley AgTech Cooperative",
  "code": "GV-AGTECH",
  "tier": "enterprise",
  "country": "Kenya",
  "currency": "KES",
  "contactEmail": "info@greenvalley.ag",
  "contactPhone": "+254712345678",
  "settings": {
    "defaultMeasurementUnit": "acres",
    "fiscalYearStartMonth": 1,
    "allowedModules": ["agrotrack", "marketlens", "impactos", "analyst"]
  },
  "createdAt": "2026-11-03T00:00:00Z",
  "updatedAt": "2026-11-03T12:00:00Z"
}
```

### 3.2 User (`/users/{uid}`)
A registered user profile linked to Firebase Authentication.

```json
{
  "uid": "fb_user_89123847",
  "email": "sarah.mwangi@greenvalley.ag",
  "name": "Sarah Mwangi",
  "photo": "https://ui-avatars.com/api/?name=Sarah+Mwangi&background=164e38&color=22c55e",
  "defaultOrgId": "org_gv_2026_01",
  "activeRole": "Organisation Administrator",
  "joinedAt": "2026-08-15T09:30:00Z",
  "lastLoginAt": "2026-11-03T14:20:00Z",
  "settings": {
    "lang": "en",
    "theme": "dark",
    "currency": "KES",
    "unit": "acres",
    "notifyScan": true,
    "notifyInventory": true
  }
}
```

### 3.3 Organisation Membership (`/memberships/{orgId}/{uid}`)
Maps users to organizations with explicit Role-Based Access Control (RBAC).

```json
{
  "orgId": "org_gv_2026_01",
  "userId": "fb_user_89123847",
  "role": "Organisation Administrator",
  "status": "active",
  "joinedAt": "2026-08-15T09:30:00Z",
  "permissions": [
    "org:admin",
    "projects:manage",
    "farmers:manage",
    "farms:manage",
    "reports:export",
    "analyst:query"
  ]
}
```

#### Standard Platform Roles:
| Role Name | Scope & Authority |
|---|---|
| **Organisation Administrator** | Complete control over organization metadata, memberships, billing, projects, and data export. |
| **Project Manager** | Full management of assigned projects, target indicators, budget allocations, and M&E reports. |
| **Field Officer** | Operations in the field: onboarding farmers, surveying farm plots, executing AI leaf scans, updating NPK. |
| **Analyst** | Quantitative research: MarketLens price analysis, ImpactOS indicator tracking, and AI Analyst querying. |
| **Viewer** | Read-only access to published executive dashboards, high-level project targets, and aggregated reports. |

### 3.4 Project (`/projects/{orgId}/{projectId}`)
Represents a development initiative, donor-funded grant, or commercial crop program under **ImpactOS**.

```json
{
  "id": "proj_climate_resilience_2026",
  "orgId": "org_gv_2026_01",
  "name": "Smallholder Maize Climate Resilience Initiative",
  "code": "SMCRI-2026",
  "description": "Improving drought-tolerant seed adoption and smart irrigation for 1,200 farmers.",
  "status": "active",
  "startDate": "2026-01-01",
  "endDate": "2026-12-31",
  "leadManagerId": "fb_user_89123847",
  "targetBeneficiaries": 1200,
  "enrolledFarmers": 840,
  "budget": 4500000,
  "currency": "KES",
  "indicators": {
    "hectaresUnderImprovement": { "target": 2500, "actual": 1820 },
    "scansCompleted": { "target": 5000, "actual": 3410 },
    "yieldImprovementPercent": { "target": 25, "actual": 18.5 }
  },
  "createdAt": "2026-01-01T08:00:00Z"
}
```

### 3.5 Farmer (`/farmers/{orgId}/{farmerId}`)
Beneficiary or commercial farmer profile managed under **AgroTrack** and tracked in **ImpactOS**.

```json
{
  "id": "frmr_982103",
  "orgId": "org_gv_2026_01",
  "nationalId": "24981023",
  "firstName": "Joseph",
  "lastName": "Kamau",
  "phone": "+254722998877",
  "gender": "male",
  "location": {
    "county": "Nakuru",
    "subCounty": "Rongai",
    "ward": "Solai",
    "latitude": -0.0245,
    "longitude": 36.1432
  },
  "assignedFieldOfficerId": "fb_user_38129381",
  "enrolledProjectIds": ["proj_climate_resilience_2026"],
  "totalAcreage": 4.5,
  "registeredAt": "2026-02-10T11:15:00Z"
}
```

### 3.6 Farm & Plot (`/farms/{orgId}/{farmId}` & `/users/{uid}/farms/{farmId}`)
Physical agricultural plots. Compatible with existing AgroFast attributes while supporting geospatial coordinates for future Leaflet polygon mapping.

```json
{
  "id": "farm_plot_40192",
  "orgId": "org_gv_2026_01",
  "farmerId": "frmr_982103",
  "ownerUserId": "fb_user_89123847",
  "name": "Solai North Maize Plot",
  "size": 3.5,
  "unit": "acres",
  "crop": "Maize",
  "soil": "Loamy",
  "irrigation": "Drip",
  "waterSource": "Borehole",
  "status": "Growing",
  "plantingDate": "2026-03-15",
  "budget": 75000,
  "soilNutrients": {
    "n": 48,
    "p": 32,
    "k": 28
  },
  "location": {
    "name": "Solai, Nakuru",
    "latitude": -0.0248,
    "longitude": 36.1435,
    "boundaryPolygon": [
      [-0.0240, 36.1428],
      [-0.0240, 36.1442],
      [-0.0255, 36.1442],
      [-0.0255, 36.1428]
    ]
  },
  "imageUrl": "images/smart_farm.png",
  "createdAt": "2026-03-15T07:30:00Z"
}
```

---

## 4. Referential Integrity Rules

1. **Cascade Prevention**: Deletion of a Farm must verify that associated expenses and diagnostic scans are flagged or archived rather than orphaned.
2. **Membership Enforcement**: A user cannot perform mutations within `/organisations/{orgId}/` unless an active membership record exists at `/memberships/{orgId}/{uid}` with required role permissions.
3. **Audit Log Trail**: All project-level modifications record `updatedBy` and `updatedAt` for donor accountability in ImpactOS.

---

## 5. Security & Isolation Rules (Firebase RTDB)

```json
{
  "rules": {
    "users": {
      "$uid": {
        ".read": "auth != null && (auth.uid === $uid || root.child('memberships/' + data.child('defaultOrgId').val() + '/' + auth.uid + '/role').val() === 'Organisation Administrator')",
        ".write": "auth != null && auth.uid === $uid"
      }
    },
    "organisations": {
      "$orgId": {
        ".read": "auth != null && root.child('memberships/' + $orgId + '/' + auth.uid).exists()",
        ".write": "auth != null && root.child('memberships/' + $orgId + '/' + auth.uid + '/role').val() === 'Organisation Administrator'"
      }
    },
    "memberships": {
      "$orgId": {
        ".read": "auth != null && root.child('memberships/' + $orgId + '/' + auth.uid).exists()",
        ".write": "auth != null && root.child('memberships/' + $orgId + '/' + auth.uid + '/role').val() === 'Organisation Administrator'"
      }
    },
    "projects": {
      "$orgId": {
        ".read": "auth != null && root.child('memberships/' + $orgId + '/' + auth.uid).exists()",
        ".write": "auth != null && (root.child('memberships/' + $orgId + '/' + auth.uid + '/role').val() === 'Organisation Administrator' || root.child('memberships/' + $orgId + '/' + auth.uid + '/role').val() === 'Project Manager')"
      }
    },
    "farmers": {
      "$orgId": {
        ".read": "auth != null && root.child('memberships/' + $orgId + '/' + auth.uid).exists()",
        ".write": "auth != null && root.child('memberships/' + $orgId + '/' + auth.uid + '/role').val() != 'Viewer'"
      }
    }
  }
}
```
