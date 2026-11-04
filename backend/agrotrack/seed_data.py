"""
AgroTrack AI — Baseline Seed Data for AgroTrack Domain
"""

DEFAULT_FARMERS = {
    "org_greenvalley_01": [
        {
            "id": "frmr_982103",
            "orgId": "org_greenvalley_01",
            "farmerCode": "FM-GV-001",
            "nationalId": "24981023",
            "firstName": "Joseph",
            "lastName": "Kamau",
            "phone": "+254722998877",
            "gender": "male",
            "location": {
                "county": "Nakuru",
                "subCounty": "Rongai",
                "ward": "Solai",
                "village": "Milmet",
                "latitude": -0.0245,
                "longitude": 36.1432
            },
            "assignedFieldOfficerId": "usr_field_003",
            "assignedFieldOfficerName": "Amina Otieno",
            "enrolledProjectIds": ["proj_climate_resilience_2026"],
            "totalAcreage": 3.5,
            "status": "active",
            "consentGiven": True,
            "registeredAt": "2026-02-10T11:15:00Z"
        },
        {
            "id": "frmr_982104",
            "orgId": "org_greenvalley_01",
            "farmerCode": "FM-GV-002",
            "nationalId": "28491024",
            "firstName": "Mary",
            "lastName": "Wambui",
            "phone": "+254733112233",
            "gender": "female",
            "location": {
                "county": "Nakuru",
                "subCounty": "Rongai",
                "ward": "Rongai Central",
                "village": "Kampi ya Moto",
                "latitude": -0.0152,
                "longitude": 36.0825
            },
            "assignedFieldOfficerId": "usr_field_003",
            "assignedFieldOfficerName": "Amina Otieno",
            "enrolledProjectIds": ["proj_climate_resilience_2026"],
            "totalAcreage": 1.2,
            "status": "active",
            "consentGiven": True,
            "registeredAt": "2026-03-01T08:30:00Z"
        }
    ],
    "org_highland_02": [
        {
            "id": "frmr_hl_771",
            "orgId": "org_highland_02",
            "farmerCode": "FM-HL-001",
            "nationalId": "19823456",
            "firstName": "Kiprono",
            "lastName": "Langat",
            "phone": "+254710445566",
            "gender": "male",
            "location": {
                "county": "Kericho",
                "subCounty": "Ainamoi",
                "ward": "Kipchimchim",
                "village": "Chagaik",
                "latitude": -0.3689,
                "longitude": 35.2863
            },
            "assignedFieldOfficerId": "usr_hl_10",
            "assignedFieldOfficerName": "Highland Field Team",
            "enrolledProjectIds": [],
            "totalAcreage": 12.0,
            "status": "active",
            "consentGiven": True,
            "registeredAt": "2026-01-10T09:00:00Z"
        }
    ]
}

DEFAULT_FARMS = {
    "org_greenvalley_01": [
        {
            "id": "farm_gv_101",
            "orgId": "org_greenvalley_01",
            "farmerId": "frmr_982103",
            "name": "Solai North Maize Plot",
            "size": 3.5,
            "unit": "acres",
            "crop": "Maize",
            "soil": "Loamy",
            "irrigation": "Drip",
            "waterSource": "Borehole",
            "status": "Growing",
            "plantingDate": "2026-03-15",
            "budget": 75000.0,
            "soilNutrients": {"n": 48.0, "p": 32.0, "k": 28.0},
            "location": {"name": "Solai, Nakuru", "latitude": -0.0248, "longitude": 36.1435}
        },
        {
            "id": "farm_gv_102",
            "orgId": "org_greenvalley_01",
            "farmerId": "frmr_982104",
            "name": "Rongai Tomato Greenhouse",
            "size": 1.2,
            "unit": "acres",
            "crop": "Tomato",
            "soil": "Clay Loam",
            "irrigation": "Drip",
            "waterSource": "River",
            "status": "Growing",
            "plantingDate": "2026-04-01",
            "budget": 120000.0,
            "soilNutrients": {"n": 42.0, "p": 45.0, "k": 50.0},
            "location": {"name": "Rongai, Nakuru", "latitude": -0.0150, "longitude": 36.0820}
        }
    ],
    "org_highland_02": [
        {
            "id": "farm_hl_201",
            "orgId": "org_highland_02",
            "farmerId": "frmr_hl_771",
            "name": "Kericho Highland Tea Estate",
            "size": 12.0,
            "unit": "acres",
            "crop": "Tea",
            "soil": "Volcanic Red",
            "irrigation": "Rain-fed",
            "waterSource": "Rain",
            "status": "Growing",
            "plantingDate": "2026-01-10",
            "budget": 350000.0,
            "soilNutrients": {"n": 55.0, "p": 40.0, "k": 35.0},
            "location": {"name": "Kericho", "latitude": -0.3689, "longitude": 35.2863}
        }
    ]
}

DEFAULT_ACTIVITIES = {
    "org_greenvalley_01": [
        {
            "id": "act_gv_001",
            "orgId": "org_greenvalley_01",
            "farmId": "farm_gv_101",
            "farmerId": "frmr_982103",
            "farmName": "Solai North Maize Plot",
            "farmerName": "Joseph Kamau",
            "activityType": "farm_visit",
            "activityDate": "2026-10-25",
            "responsibleUserId": "usr_field_003",
            "responsibleUserName": "Amina Otieno",
            "notes": "Initial seasonal monitoring visit. Verified drip line pressure and uniform emergence.",
            "metrics": {"soilMoisture": "Adequate", "canopyHealth": "Good"},
            "observations": ["Leaves looking vibrant", "No stem borer damage detected"],
            "createdAt": "2026-10-25T10:00:00Z"
        },
        {
            "id": "act_gv_002",
            "orgId": "org_greenvalley_01",
            "farmId": "farm_gv_101",
            "farmerId": "frmr_982103",
            "farmName": "Solai North Maize Plot",
            "farmerName": "Joseph Kamau",
            "activityType": "crop_inspection",
            "activityDate": "2026-10-28",
            "responsibleUserId": "usr_field_003",
            "responsibleUserName": "Amina Otieno",
            "notes": "Scouted lower leaves after morning fog. Detected early Common Rust pustules on 3 stalks.",
            "metrics": {"scannedStalks": 50, "infectedStalks": 3},
            "observations": ["Prescribed protective copper fungicide spray"],
            "createdAt": "2026-10-28T09:45:00Z"
        },
        {
            "id": "act_gv_003",
            "orgId": "org_greenvalley_01",
            "farmId": "farm_gv_102",
            "farmerId": "frmr_982104",
            "farmName": "Rongai Tomato Greenhouse",
            "farmerName": "Mary Wambui",
            "activityType": "fertilizer_application",
            "activityDate": "2026-11-01",
            "responsibleUserId": "usr_field_003",
            "responsibleUserName": "Amina Otieno",
            "notes": "Supervised foliar calcium & potassium application to prevent blossom end rot.",
            "metrics": {"product": "EasyGro Calcium", "volumeLitres": 20},
            "observations": ["Pruning and staking completed"],
            "createdAt": "2026-11-01T14:30:00Z"
        }
    ],
    "org_highland_02": [
        {
            "id": "act_hl_001",
            "orgId": "org_highland_02",
            "farmId": "farm_hl_201",
            "farmerId": "frmr_hl_771",
            "farmName": "Kericho Highland Tea Estate",
            "farmerName": "Kiprono Langat",
            "activityType": "harvest",
            "activityDate": "2026-10-15",
            "responsibleUserId": "usr_hl_10",
            "responsibleUserName": "Highland Field Team",
            "notes": "Routine two-leaves-and-a-bud plucking cycle completed.",
            "metrics": {"pluckedWeightKg": 1420.0, "qualityGrade": "A"},
            "observations": ["Flushing rate optimal"],
            "createdAt": "2026-10-15T12:00:00Z"
        }
    ]
}

DEFAULT_EXPENSES = {
    "org_greenvalley_01": [
        {
            "id": "exp_gv_01",
            "orgId": "org_greenvalley_01",
            "farmId": "farm_gv_101",
            "category": "Seeds",
            "amount": 12500.0,
            "date": "2026-03-12",
            "note": "Certified hybrid maize seed (SC 627)"
        },
        {
            "id": "exp_gv_02",
            "orgId": "org_greenvalley_01",
            "farmId": "farm_gv_101",
            "category": "Fertilizer",
            "amount": 18000.0,
            "date": "2026-03-15",
            "note": "Basal planting DAP 18:46:0"
        }
    ],
    "org_highland_02": [
        {
            "id": "exp_hl_01",
            "orgId": "org_highland_02",
            "farmId": "farm_hl_201",
            "category": "Labor",
            "amount": 45000.0,
            "date": "2026-02-15",
            "note": "Quarterly tea pruning labor"
        }
    ]
}

DEFAULT_SCANS = {
    "org_greenvalley_01": [
        {
            "id": "scan_gv_01",
            "orgId": "org_greenvalley_01",
            "farmId": "farm_gv_101",
            "crop": "Maize",
            "disease": "Common Rust",
            "confidence": "92.4%",
            "severity_percentage": 4.5,
            "severity_level": "Mild (Early Stage)",
            "time": "2026-10-28T09:30:00Z"
        },
        {
            "id": "scan_gv_02",
            "orgId": "org_greenvalley_01",
            "farmId": "farm_gv_102",
            "crop": "Tomato",
            "disease": "Tomato Early Blight",
            "confidence": "94.8%",
            "severity_percentage": 8.2,
            "severity_level": "Moderate",
            "time": "2026-11-01T11:15:00Z"
        }
    ],
    "org_highland_02": [
        {
            "id": "scan_hl_01",
            "orgId": "org_highland_02",
            "farmId": "farm_hl_201",
            "crop": "Tea",
            "disease": "Healthy",
            "confidence": "98.1%",
            "severity_percentage": 0.0,
            "severity_level": "None (Healthy)",
            "time": "2026-10-15T08:00:00Z"
        }
    ]
}
