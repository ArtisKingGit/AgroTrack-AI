"""
AgroTrack Business Logic & Agricultural Intelligence Service
Provides core agronomic calculations, farm health scoring, environmental risk prediction,
irrigation advisory, fertilizer balancing, crop calendar, profitability simulation,
and multi-tenant organisation-isolated data storage.
"""

from datetime import datetime, date
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status

from backend.ai.treatments import CROP_SOIL_REQUIREMENTS, get_treatment


# ── Crop Agronomic Profiles ──────────────────────────────────────────────────
CROP_PROFILES: Dict[str, Dict[str, Any]] = {
    "maize": {
        "name": "Maize",
        "cycle_days": 110,
        "base_yield_kg_acre": 2500,
        "base_price_kg": 45.0,
        "cost_per_acre": 35000.0,
        "ideal_npk": {"n": 50, "p": 35, "k": 30},
        "water_needs": "Medium",
        "favorable_temp": (18.0, 30.0),
        "favorable_hum": (50.0, 75.0),
        "stages": [
            {"name": "Germination & Emergence", "days": (0, 14), "milestone": "Scout for cutworms; ensure uniform soil moisture."},
            {"name": "Early Vegetative (V3-V6)", "days": (15, 35), "milestone": "First weeding and top-dress nitrogen (CAN/Urea)."},
            {"name": "Rapid Stem Elongation (V7-V12)", "days": (36, 55), "milestone": "Second weeding; scout for Fall Armyworm."},
            {"name": "Tasseling & Silking (R1)", "days": (56, 75), "milestone": "Critical moisture period; do not let soil dry out."},
            {"name": "Grain Filling & Milk Stage (R2-R4)", "days": (76, 95), "milestone": "Monitor for Common Rust and Gray Leaf Spot."},
            {"name": "Maturity & Harvest (R6)", "days": (96, 130), "milestone": "Harvest when moisture drops to 13.5%; dry on clean tarpaulins."}
        ]
    },
    "beans": {
        "name": "Beans",
        "cycle_days": 70,
        "base_yield_kg_acre": 1000,
        "base_price_kg": 110.0,
        "cost_per_acre": 28000.0,
        "ideal_npk": {"n": 30, "p": 45, "k": 35},
        "water_needs": "Low",
        "favorable_temp": (18.0, 26.0),
        "favorable_hum": (55.0, 80.0),
        "stages": [
            {"name": "Emergence", "days": (0, 10), "milestone": "Ensure good soil drainage; avoid seed rot."},
            {"name": "Vegetative & Branching", "days": (11, 28), "milestone": "Foliar fertilizer and early weeding."},
            {"name": "Flowering", "days": (29, 45), "milestone": "Avoid overhead watering; spray organic pest repellent."},
            {"name": "Pod Formation & Fill", "days": (46, 60), "milestone": "Monitor for anthracnose and bean fly."},
            {"name": "Ripening & Harvest", "days": (61, 80), "milestone": "Harvest when pods turn golden brown and rattle."}
        ]
    },
    "potato": {
        "name": "Potato",
        "cycle_days": 90,
        "base_yield_kg_acre": 8000,
        "base_price_kg": 50.0,
        "cost_per_acre": 65000.0,
        "ideal_npk": {"n": 45, "p": 45, "k": 55},
        "water_needs": "Medium",
        "favorable_temp": (15.0, 24.0),
        "favorable_hum": (60.0, 85.0),
        "stages": [
            {"name": "Sprouting & Emergence", "days": (0, 15), "milestone": "Check seed tuber emergence and soil temperature."},
            {"name": "Vegetative Growth", "days": (16, 35), "milestone": "First hilling (earthing up) and preventive fungicide."},
            {"name": "Tuber Initiation & Flowering", "days": (36, 55), "milestone": "Second hilling; maintain steady moisture."},
            {"name": "Tuber Bulking", "days": (56, 75), "milestone": "Monitor rigorously for Late Blight lesions."},
            {"name": "Maturation & Skin Setting", "days": (76, 105), "milestone": "De-haulm (cut foliage) 10-14 days before harvest."}
        ]
    },
    "tomato": {
        "name": "Tomato",
        "cycle_days": 85,
        "base_yield_kg_acre": 12000,
        "base_price_kg": 60.0,
        "cost_per_acre": 85000.0,
        "ideal_npk": {"n": 45, "p": 40, "k": 50},
        "water_needs": "High",
        "favorable_temp": (20.0, 28.0),
        "favorable_hum": (50.0, 75.0),
        "stages": [
            {"name": "Transplanting Recovery", "days": (0, 14), "milestone": "Stake plants and apply starter phosphorus fertilizer."},
            {"name": "Vegetative & Side Shooting", "days": (15, 30), "milestone": "Prune suckers (side shoots) and mulch root beds."},
            {"name": "Flowering & Fruit Set", "days": (31, 50), "milestone": "Apply calcium foliar to prevent Blossom End Rot."},
            {"name": "Fruit Bulking & Color Break", "days": (51, 70), "milestone": "Preventive copper spray for Early/Late Blight."},
            {"name": "Harvest Window", "days": (71, 100), "milestone": "Pick at breaker/pink stage for maximum transport shelf life."}
        ]
    },
    "wheat": {
        "name": "Wheat",
        "cycle_days": 120,
        "base_yield_kg_acre": 2200,
        "base_price_kg": 55.0,
        "cost_per_acre": 32000.0,
        "ideal_npk": {"n": 48, "p": 38, "k": 30},
        "water_needs": "Medium",
        "favorable_temp": (14.0, 22.0),
        "favorable_hum": (45.0, 70.0),
        "stages": [
            {"name": "Germination & Tillering", "days": (0, 30), "milestone": "Early weed control and basal fertilizer."},
            {"name": "Stem Elongation", "days": (31, 60), "milestone": "Top-dress nitrogen; monitor for Septoria."},
            {"name": "Booting & Heading", "days": (61, 85), "milestone": "Fungicide scout for Yellow Rust and Brown Rust."},
            {"name": "Grain Filling", "days": (86, 105), "milestone": "Monitor kernel development and moisture stress."},
            {"name": "Ripening & Harvest", "days": (106, 135), "milestone": "Combine harvest at grain moisture < 14%."}
        ]
    }
}


def _get_crop_profile(crop_name: str) -> Dict[str, Any]:
    """Resolves crop profile by case-insensitive substring match."""
    key = crop_name.lower().strip()
    for k, prof in CROP_PROFILES.items():
        if k in key or key in k:
            return prof
    return CROP_PROFILES["maize"]


# ── 1. Farm Health Scoring ────────────────────────────────────────────────────

def calculate_farm_health_score(farm: Dict[str, Any], recent_scans: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Computes an integrated 0-100 farm health score based on:
    - Diagnostic scan disease frequency & severity (40 pts)
    - Soil NPK balance (35 pts)
    - Irrigation adequacy & plot size management (25 pts)
    """
    recent_scans = recent_scans or []
    
    # A. Disease Score (Max 40 points)
    if not recent_scans:
        disease_score = 36.0  # Clean baseline with no reported disease
        disease_status = "No recent disease incidents recorded."
    else:
        diseased_count = sum(1 for s in recent_scans if not s.get("disease", "Healthy").lower().startswith("healthy"))
        total_scans = len(recent_scans)
        disease_rate = diseased_count / total_scans
        disease_score = max(5.0, 40.0 - (disease_rate * 32.0))
        disease_status = f"{diseased_count} of {total_scans} recent scans flagged pathogen presence."

    # B. Soil NPK Score (Max 35 points)
    soil_nutrients = farm.get("soilNutrients") or farm.get("soil") or {}
    if isinstance(soil_nutrients, dict):
        n = float(soil_nutrients.get("n", 45))
        p = float(soil_nutrients.get("p", 30))
        k = float(soil_nutrients.get("k", 25))
    else:
        n, p, k = 45.0, 30.0, 25.0

    # Distance from ideal balanced ratios (N: 45-55, P: 30-40, K: 25-35)
    n_dev = abs(n - 50)
    p_dev = abs(p - 35)
    k_dev = abs(k - 30)
    soil_penalty = (n_dev * 0.4 + p_dev * 0.4 + k_dev * 0.3)
    soil_score = max(10.0, 35.0 - soil_penalty)

    # C. Management & Irrigation Score (Max 25 points)
    irrigation = str(farm.get("irrigation", "Rain-fed")).lower()
    if "drip" in irrigation:
        mgt_score = 25.0
    elif "sprinkler" in irrigation:
        mgt_score = 22.0
    else:
        mgt_score = 18.0

    total_score = round(disease_score + soil_score + mgt_score, 1)

    # Grade allocation
    if total_score >= 85.0:
        grade = "A"
        grade_label = "Optimal Productivity (Grade A)"
    elif total_score >= 70.0:
        grade = "B"
        grade_label = "Good Health (Grade B)"
    elif total_score >= 50.0:
        grade = "C"
        grade_label = "Moderate Stress (Grade C)"
    else:
        grade = "D"
        grade_label = "Critical Intervention Needed (Grade D)"

    action_items = []
    if disease_score < 25.0:
        action_items.append("Immediate crop disease containment recommended; verify latest leaf scan prescriptions.")
    if n < 35:
        action_items.append("Nitrogen deficiency detected; apply targeted CAN or Urea top-dressing.")
    if p < 25:
        action_items.append("Phosphorus deficit; apply DAP or rock phosphate at root zone.")
    if "rain-fed" in irrigation:
        action_items.append("Rain-fed plot vulnerability; consider installing low-cost drip lines for dry spells.")

    if not action_items:
        action_items.append("Maintain current agronomic schedule and continue periodic scouting.")

    return {
        "farm_id": farm.get("id", "plot_unknown"),
        "farm_name": farm.get("name", "Unnamed Farm"),
        "health_score": total_score,
        "health_grade": grade,
        "grade_label": grade_label,
        "breakdown": {
            "disease_health": round(disease_score, 1),
            "soil_fertility": round(soil_score, 1),
            "irrigation_management": round(mgt_score, 1)
        },
        "disease_status": disease_status,
        "action_items": action_items
    }


# ── 2. Environmental Disease Risk Prediction ──────────────────────────────────

def predict_disease_risk(temperature: float, humidity: float, precipitation: float, crop: str) -> Dict[str, Any]:
    """
    Evaluates epidemiological risk of plant pathogens based on meteorological parameters.
    """
    threats = []
    risk_score = 15  # baseline ambient risk

    # A. Late Blight & Fungal Leaf Spot Risk
    if 16.0 <= temperature <= 26.0 and (humidity >= 75.0 or precipitation >= 5.0):
        threats.append({
            "disease": "Late Blight / Fungal Leaf Spot",
            "risk_level": "High",
            "trigger": f"High humidity ({humidity}%) and warm-cool temperatures ({temperature}°C) facilitate fungal spore germination."
        })
        risk_score += 45
    elif 14.0 <= temperature <= 28.0 and humidity >= 65.0:
        threats.append({
            "disease": "Early Blight / Septoria",
            "risk_level": "Moderate",
            "trigger": f"Moderate humidity ({humidity}%) and temperature ({temperature}°C)."
        })
        risk_score += 25

    # B. Rust Disease Risk
    if 15.0 <= temperature <= 24.0 and humidity >= 70.0:
        threats.append({
            "disease": "Common / Stripe Rust",
            "risk_level": "Moderate",
            "trigger": "Moist canopy creates favorable rust fungal infection conditions."
        })
        risk_score += 20

    # C. High Heat / Pest Risk (Spider Mites, Thrips)
    if temperature >= 28.0 and humidity <= 45.0:
        threats.append({
            "disease": "Two-Spotted Spider Mites & Thrips",
            "risk_level": "High",
            "trigger": f"Hot ({temperature}°C) and arid conditions ({humidity}% RH) accelerate insect reproduction."
        })
        risk_score += 35

    risk_score = min(100, risk_score)

    if risk_score >= 70:
        overall_level = "High Risk"
    elif risk_score >= 40:
        overall_level = "Moderate Risk"
    else:
        overall_level = "Low Risk"

    preventative_measures = []
    if any(t["risk_level"] == "High" for t in threats):
        preventative_measures.append("Apply preventative protective copper-based or systemic fungicide before next forecast rain.")
        preventative_measures.append("Avoid overhead sprinkling in late afternoon to reduce leaf surface wetness overnight.")
    else:
        preventative_measures.append("Maintain routine weekly visual canopy scouting.")
        preventative_measures.append("Ensure field borders are clear of weed alternate hosts.")

    return {
        "crop": crop,
        "temperature": temperature,
        "humidity": humidity,
        "precipitation_mm": precipitation,
        "risk_score": risk_score,
        "overall_risk_level": overall_level,
        "potential_threats": threats,
        "preventative_measures": preventative_measures
    }


# ── 3. Smart Irrigation Advisory ──────────────────────────────────────────────

def calculate_irrigation_advice(
    crop: str,
    soil_type: str,
    temperature: float,
    humidity: float,
    precipitation_24h: float,
    irrigation_type: str = "Drip"
) -> Dict[str, Any]:
    """
    Computes precise watering necessity based on evapotranspiration balance and soil physics.
    """
    crop_prof = _get_crop_profile(crop)
    
    # Rainfall surplus check
    if precipitation_24h >= 15.0:
        action = "Hold Irrigation"
        volume_mm = 0.0
        reason = f"Recent precipitation ({precipitation_24h}mm) has fully recharged the root zone. Watering now risks root asphyxiation and nitrogen leaching."
    elif precipitation_24h >= 6.0:
        action = "Reduce Volume"
        volume_mm = 8.0
        reason = f"Moderate rainfall ({precipitation_24h}mm) partially satisfied crop water demand. Supplemental light irrigation (8mm) recommended."
    elif temperature >= 28.0 and humidity <= 50.0:
        action = "Increase Volume"
        volume_mm = 28.0
        reason = f"High heat ({temperature}°C) and low atmospheric humidity ({humidity}%) drive elevated evapotranspiration. Deep cycle (28mm) required."
    else:
        action = "Standard Cycle"
        volume_mm = 18.0
        reason = "Normal weather conditions. Maintain standard scheduled irrigation."

    # Soil adjustments
    soil_lower = soil_type.lower()
    if "sand" in soil_lower:
        soil_note = "Sandy soil has high drainage: split recommended volume into two shorter cycles (morning and late afternoon)."
    elif "clay" in soil_lower:
        soil_note = "Clay soil retains moisture: apply water slowly to prevent surface ponding and runoff."
    else:
        soil_note = "Loamy soil has ideal water retention: single uniform morning application is optimal."

    return {
        "crop": crop,
        "soil_type": soil_type,
        "irrigation_type": irrigation_type,
        "action": action,
        "recommended_volume_mm": volume_mm,
        "optimal_window": "Early Morning (06:00 - 08:30) or Late Afternoon (17:00 - 18:30)",
        "reason": reason,
        "soil_drainage_note": soil_note
    }


# ── 4. Fertilizer & Soil Balancing Advisory ───────────────────────────────────

def calculate_fertilizer_advice(
    crop: str,
    n_percent: float,
    p_percent: float,
    k_percent: float,
    ph: float = 6.5
) -> Dict[str, Any]:
    """
    Calculates specific NPK nutrient deficits and prescribes exact commercial fertilizer treatments.
    """
    crop_prof = _get_crop_profile(crop)
    ideal = crop_prof.get("ideal_npk", {"n": 50, "p": 35, "k": 30})

    deficits = {
        "nitrogen_deficit": max(0.0, round(ideal["n"] - n_percent, 1)),
        "phosphorus_deficit": max(0.0, round(ideal["p"] - p_percent, 1)),
        "potassium_deficit": max(0.0, round(ideal["k"] - k_percent, 1))
    }

    prescriptions = []

    # Nitrogen
    if deficits["nitrogen_deficit"] > 15:
        prescriptions.append({
            "nutrient": "Nitrogen (N)",
            "severity": "High Deficit",
            "product": "CAN (Calcium Ammonium Nitrate 26% N) or Urea (46% N)",
            "rate_per_acre": "50 - 75 kg per acre",
            "timing": "Top-dress in moist soil at early vegetative stage (knee-high for cereals)."
        })
    elif deficits["nitrogen_deficit"] > 5:
        prescriptions.append({
            "nutrient": "Nitrogen (N)",
            "severity": "Moderate Deficit",
            "product": "CAN (26% N)",
            "rate_per_acre": "25 - 40 kg per acre",
            "timing": "Standard top-dressing."
        })

    # Phosphorus
    if deficits["phosphorus_deficit"] > 10:
        prescriptions.append({
            "nutrient": "Phosphorus (P)",
            "severity": "Significant Deficit",
            "product": "DAP (Diammonium Phosphate 18:46:0) or NPK 17:17:17",
            "rate_per_acre": "50 kg per acre",
            "timing": "Basal application at planting or incorporated near root zone."
        })

    # Potassium
    if deficits["potassium_deficit"] > 10:
        prescriptions.append({
            "nutrient": "Potassium (K)",
            "severity": "Deficit",
            "product": "Muriate of Potash (MOP 0:0:60) or NPK 17:17:17",
            "rate_per_acre": "30 - 45 kg per acre",
            "timing": "Apply prior to flowering and fruit setting stages."
        })

    # pH Balancing
    ph_advice = "Soil pH is within acceptable agronomic range (6.0 - 7.0)."
    if ph < 5.5:
        ph_advice = f"Acidic soil (pH {ph}): apply agricultural lime (calcium carbonate) at 500-1000 kg/acre to reduce aluminum toxicity."
    elif ph > 7.8:
        ph_advice = f"Alkaline soil (pH {ph}): incorporate agricultural gypsum or elemental sulfur to enhance micronutrient availability."

    return {
        "crop": crop,
        "current_npk": {"n": n_percent, "p": p_percent, "k": k_percent},
        "target_npk": ideal,
        "deficits": deficits,
        "ph": ph,
        "ph_advice": ph_advice,
        "prescriptions": prescriptions
    }


# ── 5. Farming Calendar & Milestones ──────────────────────────────────────────

def calculate_crop_calendar(crop: str, planting_date_str: str) -> Dict[str, Any]:
    """
    Computes days elapsed, current growth stage, days to harvest, and upcoming milestones.
    """
    crop_prof = _get_crop_profile(crop)
    total_cycle = crop_prof.get("cycle_days", 110)

    try:
        p_date = datetime.strptime(planting_date_str, "%Y-%m-%d").date()
    except Exception:
        p_date = date.today()

    today = date.today()
    days_elapsed = max(0, (today - p_date).days)
    days_remaining = max(0, total_cycle - days_elapsed)
    progress_pct = min(100.0, round((days_elapsed / total_cycle) * 100, 1))

    # Match stage
    current_stage = "Maturity & Harvest"
    milestone = "Harvest at optimal moisture; dry and store safely."
    for stg in crop_prof.get("stages", []):
        start_d, end_d = stg["days"]
        if start_d <= days_elapsed <= end_d:
            current_stage = stg["name"]
            milestone = stg["milestone"]
            break

    return {
        "crop": crop,
        "planting_date": str(p_date),
        "days_elapsed": days_elapsed,
        "total_cycle_days": total_cycle,
        "days_to_harvest": days_remaining,
        "growth_progress_percentage": progress_pct,
        "current_growth_stage": current_stage,
        "upcoming_milestone": milestone,
        "is_ready_for_harvest": days_remaining == 0
    }


# ── 6. Crop Profitability Simulator ───────────────────────────────────────────

def simulate_crop_profitability(
    crop: str,
    acreage: float,
    expected_yield_multiplier: float = 1.0,
    market_price_per_kg: Optional[float] = None,
    currency: str = "KES"
) -> Dict[str, Any]:
    """
    Runs quantitative financial simulation for crop yield, production costs, and net return.
    """
    prof = _get_crop_profile(crop)
    
    price_per_kg = market_price_per_kg or prof.get("base_price_kg", 50.0)
    base_yield = prof.get("base_yield_kg_acre", 2500) * expected_yield_multiplier
    cost_per_acre = prof.get("cost_per_acre", 35000.0)

    total_yield_kg = round(base_yield * acreage, 1)
    gross_revenue = round(total_yield_kg * price_per_kg, 2)
    total_cost = round(cost_per_acre * acreage, 2)
    net_profit = round(gross_revenue - total_cost, 2)
    roi_percent = round((net_profit / total_cost) * 100, 1) if total_cost > 0 else 0.0

    return {
        "crop": crop,
        "acreage": acreage,
        "currency": currency,
        "estimated_yield_total_kg": total_yield_kg,
        "market_price_per_kg": price_per_kg,
        "gross_revenue": gross_revenue,
        "total_production_cost": total_cost,
        "net_profit": net_profit,
        "profit_per_acre": round(net_profit / acreage, 2) if acreage > 0 else 0.0,
        "return_on_investment_pct": roi_percent
    }


# ── 7. Multi-Tenant In-Memory Data Store (With Cross-Org Isolation) ───────────

def _validate_gps(location: Optional[Dict[str, Any]]) -> None:
    """Validates latitude and longitude boundaries where GPS coordinates are provided."""
    if not location or not isinstance(location, dict):
        return
    lat = location.get("latitude")
    lng = location.get("longitude")
    if lat is not None:
        try:
            lat_f = float(lat)
            if not (-90.0 <= lat_f <= 90.0):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid GPS latitude '{lat}': must be between -90.0 and 90.0 degrees."
                )
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid GPS latitude format '{lat}'."
            )
    if lng is not None:
        try:
            lng_f = float(lng)
            if not (-180.0 <= lng_f <= 180.0):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid GPS longitude '{lng}': must be between -180.0 and 180.0 degrees."
                )
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid GPS longitude format '{lng}'."
            )


# Demo farmers partitioned strictly by organisation ID
TENANT_FARMERS: Dict[str, List[Dict[str, Any]]] = {
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

# Demo activities partitioned strictly by organisation ID
TENANT_ACTIVITIES: Dict[str, List[Dict[str, Any]]] = {
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

# Demo data partitioned strictly by organisation ID
TENANT_FARMS: Dict[str, List[Dict[str, Any]]] = {
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

TENANT_EXPENSES: Dict[str, List[Dict[str, Any]]] = {
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

TENANT_SCANS: Dict[str, List[Dict[str, Any]]] = {
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


# ── Farmer Management ────────────────────────────────────────────────────────

def get_farmers_for_org(
    org_id: str,
    search: Optional[str] = None,
    project_id: Optional[str] = None,
    field_officer_id: Optional[str] = None,
    status_filter: str = "active",
    crop: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieves farmers for an organisation with filtering:
    - search: text search across names, nationalId, phone, farmerCode
    - project_id: matches enrolledProjectIds
    - field_officer_id: matches assignedFieldOfficerId
    - status_filter: 'active', 'archived', or 'all'
    - crop: farmers with plots growing the specified crop
    """
    farmers = TENANT_FARMERS.get(org_id, [])
    
    # 1. Status Filter
    if status_filter != "all":
        farmers = [f for f in farmers if f.get("status", "active") == status_filter]
        
    # 2. Project Filter
    if project_id:
        farmers = [f for f in farmers if project_id in f.get("enrolledProjectIds", [])]
        
    # 3. Field Officer Filter
    if field_officer_id:
        farmers = [f for f in farmers if f.get("assignedFieldOfficerId") == field_officer_id]
        
    # 4. Crop Filter
    if crop:
        crop_lower = crop.lower()
        matching_farmer_ids = {
            farm.get("farmerId") for farm in TENANT_FARMS.get(org_id, [])
            if crop_lower in farm.get("crop", "").lower()
        }
        farmers = [f for f in farmers if f.get("id") in matching_farmer_ids]
        
    # 5. Search Filter
    if search:
        s = search.lower().strip()
        filtered = []
        for f in farmers:
            loc = f.get("location") or {}
            match = (
                s in str(f.get("firstName") or "").lower()
                or s in str(f.get("lastName") or "").lower()
                or s in str(f.get("farmerCode") or "").lower()
                or s in str(f.get("nationalId") or "").lower()
                or s in str(f.get("phone") or "").lower()
                or s in str(loc.get("ward") or "").lower()
                or s in str(loc.get("village") or "").lower()
            )
            if match:
                filtered.append(f)
        farmers = filtered
        
    return farmers


def get_farmer_by_id(org_id: str, farmer_id: str) -> Dict[str, Any]:
    """Retrieves a single farmer, blocking cross-organisation access with 403."""
    farmers = TENANT_FARMERS.get(org_id, [])
    for f in farmers:
        if f["id"] == farmer_id:
            return f
            
    # Check if farmer exists in ANY other organisation (for multi-tenant isolation guard)
    for other_org, o_farmers in TENANT_FARMERS.items():
        if other_org != org_id:
            for f in o_farmers:
                if f["id"] == farmer_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Farmer belongs to a different organisation."
                    )
                    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Farmer '{farmer_id}' not found."
    )


def get_farmer_profile(org_id: str, farmer_id: str) -> Dict[str, Any]:
    """Retrieves full profile with associated farms, activities, scans, and metrics."""
    farmer = get_farmer_by_id(org_id, farmer_id)
    farms = [f for f in TENANT_FARMS.get(org_id, []) if f.get("farmerId") == farmer_id]
    farm_ids = {f["id"] for f in farms}
    activities = [
        a for a in TENANT_ACTIVITIES.get(org_id, [])
        if a.get("farmerId") == farmer_id or a.get("farmId") in farm_ids
    ]
    scans = [s for s in TENANT_SCANS.get(org_id, []) if s.get("farmId") in farm_ids]
    
    crops = list({f.get("crop") for f in farms if f.get("crop")})
    total_acreage = round(sum(float(f.get("size", 0.0)) for f in farms), 2)
    
    return {
        "farmer": farmer,
        "farms": farms,
        "activities": activities,
        "scans": scans,
        "metrics": {
            "totalFarms": len(farms),
            "totalAcreage": total_acreage,
            "totalActivities": len(activities),
            "totalScans": len(scans),
            "crops": crops
        }
    }


def create_farmer(org_id: str, farmer_data: Dict[str, Any], current_user: Optional[Any] = None) -> Dict[str, Any]:
    """Creates a new farmer with unique nationalId & farmerCode, GPS validation, and org scoping."""
    if org_id not in TENANT_FARMERS:
        TENANT_FARMERS[org_id] = []
        
    org_farmers = TENANT_FARMERS[org_id]
    
    # 1. Duplicate National ID Check
    nat_id = str(farmer_data.get("nationalId") or "").strip()
    if nat_id:
        for f in org_farmers:
            if f.get("nationalId") == nat_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A farmer with National ID '{nat_id}' already exists in this organisation."
                )
                
    # 2. Duplicate Farmer Code Check
    code = str(farmer_data.get("farmerCode") or "").strip()
    if code:
        for f in org_farmers:
            if f.get("farmerCode") == code:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Farmer code '{code}' is already assigned in this organisation."
                )
    else:
        # Auto-generate a clean identifier
        code_prefix = org_id.replace("org_", "").replace("_", "-").upper()[:4]
        code = f"FM-{code_prefix}-{len(org_farmers) + 101:03d}"
        
    # 3. GPS Coordinate Validation
    _validate_gps(farmer_data.get("location"))
    
    # 4. Generate unique ID
    farmer_id = f"frmr_{org_id[:3]}_{len(org_farmers) + 101}"
    
    # Resolve field officer name if provided
    officer_id = farmer_data.get("assignedFieldOfficerId")
    officer_name = None
    if officer_id:
        if current_user and getattr(current_user, "uid", None) == officer_id:
            officer_name = getattr(current_user, "name", "Field Officer")
        elif officer_id == "usr_field_003":
            officer_name = "Amina Otieno"
        elif officer_id == "usr_mgr_002":
            officer_name = "David Kiprop"
        else:
            officer_name = "Assigned Field Officer"
            
    loc = farmer_data.get("location") or {}
    clean_location = {
        "county": loc.get("county", "Nakuru"),
        "subCounty": loc.get("subCounty", "Rongai"),
        "ward": loc.get("ward", "Solai"),
        "village": loc.get("village", ""),
        "latitude": loc.get("latitude"),
        "longitude": loc.get("longitude")
    }
    
    new_farmer = {
        "id": farmer_id,
        "orgId": org_id,
        "farmerCode": code,
        "nationalId": nat_id if nat_id else None,
        "firstName": farmer_data["firstName"],
        "lastName": farmer_data["lastName"],
        "phone": farmer_data.get("phone"),
        "gender": farmer_data.get("gender", "unspecified"),
        "location": clean_location,
        "assignedFieldOfficerId": officer_id,
        "assignedFieldOfficerName": officer_name,
        "enrolledProjectIds": farmer_data.get("enrolledProjectIds") or [],
        "totalAcreage": float(farmer_data.get("totalAcreage", 0.0)),
        "status": "active",
        "consentGiven": bool(farmer_data.get("consentGiven", True)),
        "registeredAt": datetime.now().isoformat(),
        "updatedAt": None
    }
    
    TENANT_FARMERS[org_id].append(new_farmer)
    return new_farmer


def update_farmer(org_id: str, farmer_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Updates farmer records with duplicate checking and GPS validation."""
    farmer = get_farmer_by_id(org_id, farmer_id)
    org_farmers = TENANT_FARMERS.get(org_id, [])
    
    # 1. If nationalId is being updated, verify uniqueness
    if "nationalId" in updates and updates["nationalId"]:
        new_nat_id = str(updates["nationalId"]).strip()
        for f in org_farmers:
            if f["id"] != farmer_id and f.get("nationalId") == new_nat_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A farmer with National ID '{new_nat_id}' already exists in this organisation."
                )
        farmer["nationalId"] = new_nat_id
        
    # 2. If GPS location is being updated, validate coordinates
    if "location" in updates and updates["location"]:
        _validate_gps(updates["location"])
        farmer["location"] = updates["location"]
        
    # 3. Apply other updates
    for key in ["firstName", "lastName", "phone", "gender", "assignedFieldOfficerId", "enrolledProjectIds", "totalAcreage", "status", "consentGiven"]:
        if key in updates and updates[key] is not None:
            farmer[key] = updates[key]
            
    # Resolve officer name update if officer changed
    if "assignedFieldOfficerId" in updates:
        off_id = updates["assignedFieldOfficerId"]
        if off_id == "usr_field_003":
            farmer["assignedFieldOfficerName"] = "Amina Otieno"
        elif off_id == "usr_mgr_002":
            farmer["assignedFieldOfficerName"] = "David Kiprop"
        elif off_id:
            farmer["assignedFieldOfficerName"] = "Field Officer"
        else:
            farmer["assignedFieldOfficerName"] = None
            
    farmer["updatedAt"] = datetime.now().isoformat()
    return farmer


def archive_farmer(org_id: str, farmer_id: str) -> Dict[str, Any]:
    """Soft-archives a farmer record without permanently deleting historical data."""
    farmer = get_farmer_by_id(org_id, farmer_id)
    farmer["status"] = "archived"
    farmer["updatedAt"] = datetime.now().isoformat()
    return {"message": f"Farmer '{farmer_id}' has been archived successfully.", "farmer": farmer}


def restore_farmer(org_id: str, farmer_id: str) -> Dict[str, Any]:
    """Restores an archived farmer record to active status."""
    farmer = get_farmer_by_id(org_id, farmer_id)
    farmer["status"] = "active"
    farmer["updatedAt"] = datetime.now().isoformat()
    return {"message": f"Farmer '{farmer_id}' has been restored to active status.", "farmer": farmer}


def get_farms_for_org(org_id: str, farmer_id: Optional[str] = None, crop: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves all farms belonging strictly to the requested organisation with optional filters."""
    farms = TENANT_FARMS.get(org_id, [])
    if farmer_id:
        farms = [f for f in farms if f.get("farmerId") == farmer_id]
    if crop:
        farms = [f for f in farms if crop.lower() in f.get("crop", "").lower()]
    return farms


def get_farm_by_id(org_id: str, farm_id: str) -> Dict[str, Any]:
    """Retrieves a single farm, ensuring cross-organisation access is blocked."""
    farms = TENANT_FARMS.get(org_id, [])
    for f in farms:
        if f["id"] == farm_id:
            return f
            
    # Check if farm exists in ANY other organisation (for security violation logging)
    for other_org, o_farms in TENANT_FARMS.items():
        if other_org != org_id:
            for f in o_farms:
                if f["id"] == farm_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Farm belongs to a different organisation."
                    )
                    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Farm '{farm_id}' not found."
    )


def create_farm(org_id: str, farm_data: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a new farm record scoped to the organisation with farmer linkage & GPS validation."""
    if org_id not in TENANT_FARMS:
        TENANT_FARMS[org_id] = []
        
    # 1. Validate GPS Coordinates
    _validate_gps(farm_data.get("location"))
    
    # 2. Check Farmer Association
    farmer_id = farm_data.get("farmerId")
    if farmer_id:
        farmer = get_farmer_by_id(org_id, farmer_id)
        farm_size = float(farm_data.get("size", 1.0))
        farmer["totalAcreage"] = round(float(farmer.get("totalAcreage", 0.0)) + farm_size, 2)
    else:
        farm_id_temp = f"farm_{org_id[:3]}_{len(TENANT_FARMS[org_id]) + 101}"
        farmer_id = f"frmr_{farm_id_temp}"
        
    farm_id = f"farm_{org_id[:3]}_{len(TENANT_FARMS[org_id]) + 101}"
    new_farm = {
        "id": farm_id,
        "orgId": org_id,
        "farmerId": farmer_id,
        "name": farm_data["name"],
        "size": float(farm_data.get("size", 1.0)),
        "unit": farm_data.get("unit", "acres"),
        "crop": farm_data.get("crop", "Maize"),
        "soil": farm_data.get("soil", "Loamy"),
        "irrigation": farm_data.get("irrigation", "Rain-fed"),
        "waterSource": farm_data.get("waterSource", "Rain"),
        "status": farm_data.get("status", "Growing"),
        "plantingDate": farm_data.get("plantingDate", str(date.today())),
        "budget": float(farm_data.get("budget", 50000.0)),
        "soilNutrients": farm_data.get("soilNutrients", {"n": 45.0, "p": 30.0, "k": 25.0}),
        "location": farm_data.get("location", {"name": "Default Location", "latitude": 0.0, "longitude": 0.0})
    }
    TENANT_FARMS[org_id].append(new_farm)
    return new_farm


def update_farm(org_id: str, farm_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Updates farm details or soil NPK with GPS validation and organisation isolation."""
    farm = get_farm_by_id(org_id, farm_id)
    
    # Validate GPS if location is being updated
    if "location" in updates and updates["location"]:
        _validate_gps(updates["location"])
        
    # If farmerId changed, verify new farmer
    if "farmerId" in updates and updates["farmerId"] and updates["farmerId"] != farm.get("farmerId"):
        get_farmer_by_id(org_id, updates["farmerId"])
        
    for key, val in updates.items():
        if key not in ["id", "orgId"]:
            farm[key] = val
    return farm


def delete_farm(org_id: str, farm_id: str) -> Dict[str, Any]:
    """Deletes farm record and associated scoped expenses & activities (preventing orphans)."""
    farm = get_farm_by_id(org_id, farm_id)
    TENANT_FARMS[org_id] = [f for f in TENANT_FARMS[org_id] if f["id"] != farm_id]
    
    # Update farmer's acreage
    farmer_id = farm.get("farmerId")
    if farmer_id:
        try:
            farmer = get_farmer_by_id(org_id, farmer_id)
            farmer["totalAcreage"] = max(0.0, round(float(farmer.get("totalAcreage", 0.0)) - float(farm.get("size", 0.0)), 2))
        except Exception:
            pass
            
    # Cascade delete expenses to maintain referential integrity
    if org_id in TENANT_EXPENSES:
        TENANT_EXPENSES[org_id] = [e for e in TENANT_EXPENSES[org_id] if e.get("farmId") != farm_id]
        
    # Cascade delete activities
    if org_id in TENANT_ACTIVITIES:
        TENANT_ACTIVITIES[org_id] = [a for a in TENANT_ACTIVITIES[org_id] if a.get("farmId") != farm_id]
        
    return {"message": f"Farm '{farm_id}' and associated records deleted successfully."}


# ── Field Activities & History ───────────────────────────────────────────────

def get_activities_for_org(
    org_id: str,
    farm_id: Optional[str] = None,
    farmer_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    responsible_user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves activities scoped to organisation with optional filters."""
    activities = TENANT_ACTIVITIES.get(org_id, [])
    if farm_id:
        activities = [a for a in activities if a.get("farmId") == farm_id]
    if farmer_id:
        activities = [a for a in activities if a.get("farmerId") == farmer_id]
    if activity_type:
        activities = [a for a in activities if a.get("activityType") == activity_type]
    if responsible_user_id:
        activities = [a for a in activities if a.get("responsibleUserId") == responsible_user_id]
        
    # Sort descending by date
    return sorted(activities, key=lambda x: str(x.get("activityDate", "")), reverse=True)


def get_activity_by_id(org_id: str, activity_id: str) -> Dict[str, Any]:
    """Retrieves an activity with cross-organisation access restriction."""
    activities = TENANT_ACTIVITIES.get(org_id, [])
    for a in activities:
        if a["id"] == activity_id:
            return a
            
    for other_org, o_acts in TENANT_ACTIVITIES.items():
        if other_org != org_id:
            for a in o_acts:
                if a["id"] == activity_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Activity belongs to a different organisation."
                    )
                    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Activity '{activity_id}' not found."
    )


def create_activity(org_id: str, activity_data: Dict[str, Any], current_user: Any) -> Dict[str, Any]:
    """Logs a field activity on a farm plot."""
    farm_id = activity_data["farmId"]
    farm = get_farm_by_id(org_id, farm_id)
    
    farmer_id = activity_data.get("farmerId") or farm.get("farmerId")
    farmer_name = None
    if farmer_id:
        try:
            farmer = get_farmer_by_id(org_id, farmer_id)
            farmer_name = f"{farmer['firstName']} {farmer['lastName']}"
        except Exception:
            pass
            
    if org_id not in TENANT_ACTIVITIES:
        TENANT_ACTIVITIES[org_id] = []
        
    activity_id = f"act_{org_id[:3]}_{len(TENANT_ACTIVITIES[org_id]) + 101}"
    user_id = getattr(current_user, "uid", "usr_field_003")
    user_name = getattr(current_user, "name", "Field Officer")
    
    new_act = {
        "id": activity_id,
        "orgId": org_id,
        "farmId": farm_id,
        "farmerId": farmer_id,
        "farmName": farm.get("name", "Farm Plot"),
        "farmerName": farmer_name,
        "activityType": str(activity_data.get("activityType", "farm_visit")),
        "activityDate": str(activity_data.get("activityDate") or date.today()),
        "responsibleUserId": user_id,
        "responsibleUserName": user_name,
        "notes": activity_data.get("notes", ""),
        "metrics": activity_data.get("metrics") or {},
        "observations": activity_data.get("observations") or [],
        "createdAt": datetime.now().isoformat()
    }
    
    TENANT_ACTIVITIES[org_id].append(new_act)
    return new_act


def sync_offline_activities(org_id: str, batch: List[Dict[str, Any]], current_user: Any) -> Dict[str, Any]:
    """
    Safely synchronizes a batch of field activities recorded offline by field officers.
    Guarantees:
    - Idempotency via clientMutationId (never duplicate records upon network retry).
    - Conflict detection: flags if target farm plot does not exist, belongs to another organisation,
      or was deleted while officer was in the field.
    - Preserves field officer offline timestamps (clientCreatedAt).
    - Never silently overwrites data.
    """
    if org_id not in TENANT_ACTIVITIES:
        TENANT_ACTIVITIES[org_id] = []

    user_id = getattr(current_user, "uid", "usr_field_003")
    user_name = getattr(current_user, "name", "Field Officer")

    synced: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []
    duplicates: List[Dict[str, Any]] = []

    # Map existing clientMutationIds for O(1) deduplication
    existing_mutation_ids = {
        a.get("clientMutationId"): a for a in TENANT_ACTIVITIES[org_id] if a.get("clientMutationId")
    }

    # Map existing farms in this tenant
    farms_map = {f["id"]: f for f in TENANT_FARMS.get(org_id, [])}

    for item in batch:
        mutation_id = item.get("clientMutationId")
        if not mutation_id:
            mutation_id = f"mut_gen_{len(TENANT_ACTIVITIES[org_id]) + 1}_{datetime.now().timestamp()}"

        # 1. Idempotency Check: Skip duplicate if already synchronized
        if mutation_id in existing_mutation_ids:
            dup_record = existing_mutation_ids[mutation_id]
            duplicates.append({
                "clientMutationId": mutation_id,
                "activityId": dup_record["id"],
                "status": "already_synced",
                "message": f"Activity with mutation ID '{mutation_id}' was previously synchronized on {dup_record.get('createdAt')}."
            })
            continue

        farm_id = item.get("farmId")
        if not farm_id or farm_id not in farms_map:
            conflicts.append({
                "clientMutationId": mutation_id,
                "farmId": farm_id,
                "status": "conflict_missing_farm",
                "message": f"Target farm '{farm_id}' was not found in organisation '{org_id}' or has been archived."
            })
            continue

        farm = farms_map[farm_id]
        farmer_id = item.get("farmerId") or farm.get("farmerId")
        farmer_name = None
        if farmer_id:
            try:
                farmer = get_farmer_by_id(org_id, farmer_id)
                farmer_name = f"{farmer['firstName']} {farmer['lastName']}"
            except Exception:
                pass

        activity_id = f"act_{org_id[:3]}_{len(TENANT_ACTIVITIES[org_id]) + 101}"
        new_act = {
            "id": activity_id,
            "orgId": org_id,
            "farmId": farm_id,
            "farmerId": farmer_id,
            "farmName": farm.get("name", "Farm Plot"),
            "farmerName": farmer_name,
            "activityType": str(item.get("activityType", "farm_visit")),
            "activityDate": str(item.get("activityDate") or date.today()),
            "responsibleUserId": user_id,
            "responsibleUserName": user_name,
            "notes": item.get("notes", ""),
            "metrics": item.get("metrics") or {},
            "observations": item.get("observations") or [],
            "clientMutationId": mutation_id,
            "syncSource": "offline_queue",
            "clientCreatedAt": item.get("clientCreatedAt") or datetime.now().isoformat(),
            "syncedAt": datetime.now().isoformat(),
            "createdAt": item.get("clientCreatedAt") or datetime.now().isoformat()
        }

        TENANT_ACTIVITIES[org_id].append(new_act)
        existing_mutation_ids[mutation_id] = new_act
        synced.append(new_act)

    return {
        "totalReceived": len(batch),
        "syncedCount": len(synced),
        "conflictCount": len(conflicts),
        "duplicateCount": len(duplicates),
        "synced": synced,
        "conflicts": conflicts,
        "duplicates": duplicates,
        "timestamp": datetime.now().isoformat()
    }


def get_farm_history(org_id: str, farm_id: str) -> Dict[str, Any]:
    """
    Returns a unified chronological timeline of all activities, scans, and expenses
    for a specific farm plot.
    """
    farm = get_farm_by_id(org_id, farm_id)
    events = []
    
    # 1. Planting Event
    if farm.get("plantingDate"):
        events.append({
            "eventType": "planting",
            "date": farm.get("plantingDate"),
            "title": f"Planted {farm.get('crop')}",
            "summary": f"Field plot '{farm.get('name')}' ({farm.get('size')} {farm.get('unit', 'acres')}) established.",
            "actor": "Plot Registry",
            "details": {"crop": farm.get("crop"), "soil": farm.get("soil"), "irrigation": farm.get("irrigation")}
        })
        
    # 2. Field Activities
    for act in TENANT_ACTIVITIES.get(org_id, []):
        if act.get("farmId") == farm_id:
            events.append({
                "eventType": f"activity_{act.get('activityType')}",
                "date": act.get("activityDate"),
                "title": f"{str(act.get('activityType', '')).replace('_', ' ').title()}",
                "summary": act.get("notes"),
                "actor": act.get("responsibleUserName"),
                "details": act.get("metrics", {})
            })
            
    # 3. Diagnostic Leaf Scans
    for scan in TENANT_SCANS.get(org_id, []):
        if scan.get("farmId") == farm_id:
            events.append({
                "eventType": "diagnostic_scan",
                "date": str(scan.get("time", ""))[:10],
                "title": f"Crop Scan: {scan.get('disease')}",
                "summary": f"Confidence {scan.get('confidence')}, Severity: {scan.get('severity_level')}",
                "actor": "AI Leaf Diagnostic Unit",
                "details": {"severityPercentage": scan.get("severity_percentage")}
            })
            
    # 4. Expenses
    for exp in TENANT_EXPENSES.get(org_id, []):
        if exp.get("farmId") == farm_id:
            events.append({
                "eventType": "expense",
                "date": exp.get("date"),
                "title": f"Expense: {exp.get('category')} (KES {exp.get('amount'):,})",
                "summary": exp.get("note") or f"{exp.get('category')} expenditure recorded",
                "actor": "Finance Management",
                "details": {"amount": exp.get("amount"), "category": exp.get("category")}
            })
            
    # Sort chronologically descending
    events.sort(key=lambda x: str(x.get("date", "")), reverse=True)
    
    return {
        "farmId": farm_id,
        "farmName": farm.get("name"),
        "totalEvents": len(events),
        "timeline": events
    }


def get_field_officer_assignments(org_id: str, user_id: str) -> Dict[str, Any]:
    """Retrieves assigned farmers and associated farms for a field officer."""
    farmers = [f for f in TENANT_FARMERS.get(org_id, []) if f.get("assignedFieldOfficerId") == user_id]
    farmer_ids = {f["id"] for f in farmers}
    farms = [farm for farm in TENANT_FARMS.get(org_id, []) if farm.get("farmerId") in farmer_ids]
    
    return {
        "officerId": user_id,
        "assignedFarmers": farmers,
        "assignedFarms": farms,
        "totalFarmers": len(farmers),
        "totalFarms": len(farms),
        "totalAcreage": round(sum(float(farm.get("size", 0.0)) for farm in farms), 2)
    }


def get_agrotrack_dashboard_stats(org_id: str) -> Dict[str, Any]:
    """Computes real-time statistics from actual database records."""
    farmers = TENANT_FARMERS.get(org_id, [])
    farms = TENANT_FARMS.get(org_id, [])
    activities = TENANT_ACTIVITIES.get(org_id, [])
    
    active_farmers = sum(1 for f in farmers if f.get("status") == "active")
    archived_farmers = sum(1 for f in farmers if f.get("status") == "archived")
    
    total_acreage = round(sum(float(f.get("size", 0.0)) for f in farms), 2)
    
    crops_count: Dict[str, int] = {}
    for f in farms:
        crop_name = f.get("crop", "Unknown")
        crops_count[crop_name] = crops_count.get(crop_name, 0) + 1
        
    total_visits = sum(1 for a in activities if a.get("activityType") in ["farm_visit", "crop_inspection"])
    
    # Sort activities by date descending
    sorted_activities = sorted(activities, key=lambda x: str(x.get("activityDate", "")), reverse=True)
    recent_activities = sorted_activities[:10]
    
    return {
        "totalFarmers": len(farmers),
        "activeFarmers": active_farmers,
        "archivedFarmers": archived_farmers,
        "totalFarms": len(farms),
        "totalAcreage": total_acreage,
        "totalActivities": len(activities),
        "totalVisits": total_visits,
        "activeCropsCount": crops_count,
        "recentActivities": recent_activities
    }


def get_expenses_for_org(org_id: str, farm_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves expenses for organisation, optionally filtered by farm."""
    expenses = TENANT_EXPENSES.get(org_id, [])
    if farm_id:
        return [e for e in expenses if e.get("farmId") == farm_id]
    return expenses


def create_expense(org_id: str, exp_data: Dict[str, Any]) -> Dict[str, Any]:
    """Records expense scoped to organisation and farm."""
    # Verify farm belongs to organisation
    farm_id = exp_data["farmId"]
    get_farm_by_id(org_id, farm_id)
    
    if org_id not in TENANT_EXPENSES:
        TENANT_EXPENSES[org_id] = []
        
    new_exp = {
        "id": f"exp_{org_id[:3]}_{len(TENANT_EXPENSES[org_id]) + 1:03d}",
        "orgId": org_id,
        "farmId": farm_id,
        "category": exp_data.get("category", "Other"),
        "amount": float(exp_data.get("amount", 0.0)),
        "date": exp_data.get("date", str(date.today())),
        "note": exp_data.get("note", "")
    }
    TENANT_EXPENSES[org_id].append(new_exp)
    return new_exp


def delete_expense(org_id: str, expense_id: str) -> Dict[str, Any]:
    """Deletes an expense record scoped to organisation."""
    expenses = TENANT_EXPENSES.get(org_id, [])
    found = any(e["id"] == expense_id for e in expenses)
    if not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Expense '{expense_id}' not found.")
        
    TENANT_EXPENSES[org_id] = [e for e in expenses if e["id"] != expense_id]
    return {"message": f"Expense '{expense_id}' deleted successfully."}


def get_scans_for_org(org_id: str, farm_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves diagnostic scan archive for organisation."""
    scans = TENANT_SCANS.get(org_id, [])
    if farm_id:
        return [s for s in scans if s.get("farmId") == farm_id]
    return scans
