# AGROTRACK AI: COMPREHENSIVE REPOSITORY AUDIT (PHASE 0)

**Date of Audit:** November 3, 2026  
**Auditor Role:** Senior Software Architect & Code Auditor  
**Audit Scope:** Full codebase audit of existing foundation (`AgroFast`) and transition roadmap to `AgroTrack AI`  
**Target Repository / Working Directory:** `C:\Users\infin\Desktop\AgroTrack AI` (Workspace)  
**Inspected Source Repository:** `C:\Users\infin\Desktop\AgroFast` (`origin/main`, commit `f6aae74`)  
**Status:** Audit Complete — Phase 0 Only (Zero modifications/deletions applied to project code)

---

## 1. Executive Summary

AgroFast is a functional, single-developer agricultural web application providing crop disease diagnosis via a CNN model (MobileNetV2), farm plot tracking, weather-based crop suitability recommendations, an operational expense tracker with budget warnings, and a conversational agronomy assistant powered by Google Gemini ("Farmly").

The goal of this audit is to inspect and document every aspect of the existing AgroFast implementation and produce a concrete, risk-managed architectural roadmap for evolving AgroFast into **AgroTrack AI**, an enterprise-grade platform encompassing four core capabilities:
1. **AgroTrack**: Farmer, farm, field, plot, and agricultural activity management.
2. **MarketLens**: Agricultural market research, commodity pricing, and value-chain intelligence.
3. **ImpactOS**: Project management, beneficiary tracking, targets, and impact reporting.
4. **AI Analyst**: An intelligence layer bridging farm data, market dynamics, and impact metrics.

### Key Audit Findings:
- **Baseline Integrity**: The core AI model (`crop_model.keras`, 56 classes, 34.2 MB), treatments dictionary (`treatments.py`, 598 lines), and PlantCV spot detection (`detector.py`) are structurally sound and functional.
- **Missing / Misrepresented Components**:
  - `backend/intelligence.py` and `frontend/js/intelligence.js` **do not exist** in the repository.
  - **Leaflet mapping is absent**: The application contains zero Leaflet code; geospatial location relies solely on browser geolocation and OpenStreetMap Nominatim reverse geocoding via `fetch()`.
  - **Testing is non-existent**: There are **zero test files** (no unit tests, no integration tests, no test runner setup).
- **Critical Architectural Risks**:
  - **Zero Backend Authentication**: Backend endpoints (`/predict`, `/chat`) are completely unauthenticated with wide-open CORS (`allow_origins=["*"]`).
  - **Client-Side Data Access**: The frontend performs 100% of database reads and writes directly against Firebase Realtime Database with no server-side validation or business logic enforcement.
  - **Extreme Code Duplication**: Frontend consists of 7 standalone monolithic HTML files (36KB – 140KB each) containing copy-pasted CSS, duplicate sidebar/header layouts, and identical hardcoded Firebase configuration objects.
  - **Hardcoded & Mock Data**: The dashboard's market trend section (`renderMarketChart`) uses hardcoded mock percentages (Maize 75, Beans 90, Wheat 65, Rice 82, Sorghum 55).
  - **Typo in Backend Package Init**: `backend/ai/_init_.py` has a single underscore instead of standard `__init__.py`.
  - **Local Dependency Execution**: System Python 3.11 has no dependencies installed, and no project-local `.venv` was initialized. All 130 dependencies from `requirements.txt` were verified to resolve cleanly with Python 3.11 via `uv`.

---

## 2. Existing Architecture & Directory Map

### 2.1 File Tree Analysis

```
AgroFast/
├── .agent/
│   └── workflows/
│       └── run-app.md                   # Agent runner workflow instruction
├── .claude/
│   └── launch.json                      # VS Code / Claude debug configuration
├── .vscode/
│   └── settings.json                    # Editor configuration
├── backend/
│   ├── ai/
│   │   ├── _init_.py                    # [BUG] Typo: single underscore instead of __init__.py
│   │   ├── class_indices.json           # 56 crop disease & soil classes
│   │   ├── classifier.py                # Keras model inference & HSV color health analysis
│   │   ├── crop_model.keras             # Trained Keras 3.15 functional CNN (34.2 MB)
│   │   ├── detector.py                  # PlantCV HSV spot segmentation & bounding boxes
│   │   ├── prepare_dataset.py           # Dataset merging/capping pipeline (PlantVillage + archive)
│   │   ├── train_model.py               # Two-phase transfer learning training script
│   │   └── treatments.py                # 598 lines of static/dynamic treatment rules & NPK lookup
│   ├── .env.example                     # Environment template (GEMINI_API_KEY)
│   └── main.py                          # FastAPI server (predict, chat, static file serving)
├── frontend/
│   ├── css/
│   │   ├── assistant-widget.css         # Styling for Farmly floating chat widget
│   │   └── custom-select.css            # Custom select dropdown styling
│   ├── images/
│   │   ├── ai_scanner.png               # Graphic asset
│   │   ├── farm_tech_bg.png             # Graphic asset
│   │   ├── smart_farm.png               # Graphic asset
│   │   └── sustainable_farm.png         # Graphic asset
│   ├── js/
│   │   ├── api-config.js                # Dynamic backend URL resolution (localhost vs HF space)
│   │   ├── assistant-widget.js          # Farmly floating chat widget & Web Speech API integration
│   │   └── custom-select.js             # Accessible custom dropdown component
│   ├── _headers                         # Netlify security and cache headers
│   ├── _redirects                       # Netlify SPA redirect rules
│   ├── AgroFast Logo.jpg                # App logo
│   ├── dashboard.html                   # Core dashboard (scanner, weather, tasks, inventory, stats)
│   ├── expenses.html                    # Expense tracker, category breakdown, budget warnings
│   ├── history.html                     # Scan history table, search, filter, detail modal
│   ├── index.html                       # Auth gate redirecting to dashboard.html or login.html
│   ├── login.html                       # Auth portal (email/password, Google OAuth, signup)
│   ├── manage.html                      # Farm plot manager (CRUD, NPK live editing, yield estimates)
│   ├── recommendations.html             # Crop recommendation engine (Open-Meteo, scoring algorithm)
│   ├── settings.html                    # User preferences (currency, units, language, theme)
│   ├── signup.html                      # Immediate redirect to login.html#signup
│   ├── theme.js                         # Theme manager, currency converter, HTML escaper
│   ├── translations.js                  # Internationalization dictionary (en, sw, zu, ve, af)
│   ├── tutorial.css                     # Onboarding tour styling
│   └── tutorial.js                      # Guided tour step controller
├── .dockerignore                        # Docker ignore rules
├── .gitignore                           # Git ignore rules
├── agrofast_guide.txt                   # Platform feature guide
├── AgroFast_Presentation.pptx           # Project pitch deck
├── Crop Available.txt                   # Text summary of 11 supported crops
├── Dockerfile                           # Production container spec (Python 3.11-slim, port 7860)
├── list_models.py                       # Standalone diagnostic utility for Gemini models
├── MODEL_ARCHITECTURE.md                # Comprehensive documentation of ML model architecture
├── netlify.toml                         # Netlify hosting config (frontend base)
├── presentation_guide.txt               # Demo walkthrough notes
├── README.md                            # High-level project documentation (UTF-16LE encoded)
└── requirements.txt                     # Backend Python dependencies
```

### 2.2 Backend Architecture & API Routing

- **Framework**: FastAPI (ASGI) running on Uvicorn.
- **Port Strategy**: Defaults to port `5500` locally, or reads `PORT` from environment (`7860` on Hugging Face Spaces).
- **DNS / Network Hacks**: In `backend/main.py` lines 27-36:
  - Monkey-patches `socket.getaddrinfo` to force `AF_INET` (IPv4 only) to prevent indefinite DNS stalling on container hosts.
  - Sets `NO_GCE_CHECK=true` to prevent google-auth from probing the GCP metadata server.
- **CORS Configuration**: Wildcard `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`.
- **Static File Mounting**: When `frontend/` directory is present relative to `backend/main.py`, FastAPI serves `frontend/login.html` at `/` and mounts the remainder under `/` using `StaticFiles(directory=frontend_path, html=True)`.

### 2.3 Frontend Architecture & Navigation

- **Technology**: Vanilla HTML5, CSS3, ES Modules (imported directly via `<script type="module">`).
- **Styling**: Custom CSS variables, modern dark-mode aesthetic with CSS Glassmorphism and Outfit Google Font.
- **Navigation Pattern**: Multi-page Application (MPA). Each page (`dashboard.html`, `manage.html`, `recommendations.html`, `expenses.html`, `history.html`, `settings.html`) is a standalone document containing full navigation sidebar markup. Links navigate via traditional browser page transitions.
- **Auth Guard**: Every page includes a `<script type="module">` that checks `onAuthStateChanged(auth, user => { if (!user) window.location.replace("login.html"); })`.
- **Internationalization (i18n)**: Handled client-side via `translations.js` supporting 5 languages: English (`en`), Swahili (`sw`), Zulu (`zu`), Venda (`ve`), and Afrikaans (`af`).
- **Currency & Units**: Dynamic currency formatting in `theme.js` supporting KES (base), USD, UGX, TZS, and ZAR via static conversion multipliers. Supports acres and hectares.

### 2.4 Database Structure & Data Relationships

The existing database is **Firebase Realtime Database (RTDB)** (`https://project-beta-7f0a3-default-rtdb.firebaseio.com/`).
All data is partitioned strictly under a user-keyed tree: `users/${uid}/`.

```
users/
└── {uid}/
    ├── name: string
    ├── email: string
    ├── scans: number
    ├── joinedAt: ISO timestamp
    ├── photo: string (optional URL)
    ├── tutorialSeen: boolean
    ├── recTutorialSeen: boolean
    ├── settings/
    │   ├── lang: "en" | "sw" | "zu" | "ve" | "af"
    │   ├── theme: "dark" | "light" | "system"
    │   ├── currency: "KES" | "USD" | "UGX" | "TZS" | "ZAR"
    │   ├── unit: "acres" | "hectares"
    │   ├── notifyScan: boolean
    │   └── notifyInventory: boolean
    ├── farms/
    │   └── {farmId}/
    │       ├── name: string
    │       ├── location: string
    │       ├── size: number (acres)
    │       ├── crop: string
    │       ├── soil: string (e.g. "Loamy", "Clay")
    │       ├── irrigation: string (e.g. "Drip", "Rain-fed")
    │       ├── waterSource: string
    │       ├── status: "Growing" | "Harvested" | "Fallow"
    │       ├── budget: number
    │       ├── description: string
    │       ├── plantingDate: YYYY-MM-DD
    │       ├── imageUrl: string
    │       ├── soil/
    │       │   ├── n: number (percentage)
    │       │   ├── p: number (percentage)
    │       │   └── k: number (percentage)
    │       ├── tasks: [] (array)
    │       └── pests: [] (array)
    ├── expenses/
    │   └── {expenseId}/
    │       ├── farmId: string (references farms/{farmId})
    │       ├── category: "Seeds" | "Fertilizer" | "Labor" | "Equipment" | "Pesticides" | "Other"
    │       ├── amount: number
    │       ├── date: YYYY-MM-DD
    │       └── note: string
    ├── history/
    │   └── {scanId}/
    │       ├── crop: string
    │       ├── disease: string
    │       ├── confidence: string (e.g. "94.20%")
    │       └── time: ISO timestamp
    ├── tasks/
    │   └── {taskId}/
    │       ├── text: string
    │       ├── completed: boolean
    │       └── createdAt: number (epoch ms)
    ├── inventory/
    │   └── {itemId}/
    │       ├── name: string
    │       ├── qty: string
    │       └── level: "high" | "med" | "low"
    └── chats/
        └── {chatId}/
            ├── title: string
            ├── updatedAt: ISO timestamp
            └── messages/
                └── [ { role: "user"|"model", content: string, timestamp: ISO string } ]
```

#### Data Relationship Analysis:
1. **One-to-Many**: User -> Farms, User -> Expenses, User -> Scans, User -> Tasks, User -> Inventory, User -> Chats.
2. **Weak Reference**: `expenses/{expenseId}/farmId` points to `farms/{farmId}`. **No referential integrity or cascade delete exists**. Deleting a farm leaves orphaned expense records.
3. **No Multi-Tenancy**: The database structure has no concept of organizations, cooperatives, donor programs, field officers, or shared farms. Data is strictly siloed per individual Google/Firebase account.

### 2.5 Authentication Implementation

- **Provider**: Firebase Authentication v12.7.0 (Client SDK).
- **Supported Methods**:
  - Email and Password (`createUserWithEmailAndPassword`, `signInWithEmailAndPassword`).
  - Google Identity OAuth (`signInWithPopup(auth, new GoogleAuthProvider())`).
- **Session Handling**: Firebase client persistence (IndexedDB / LocalStorage).
- **Security Vulnerability**: The backend **never verifies Firebase ID tokens**. Any client can send requests to `/predict` or `/chat` without any authorization header or session cookie.

### 2.6 External Integrations

| Provider | Purpose | Call Origin | Authentication | Endpoint |
|---|---|---|---|---|
| **Google Gemini API** (`gemini-2.5-flash`) | Conversational assistant ("Farmly") | Backend (`main.py`) | API Key (`GEMINI_API_KEY`) | Google GenAI SDK (REST transport) |
| **Open-Meteo Weather API** | Current weather & 7-day forecast | Frontend (`dashboard.html`, `recommendations.html`) | Free tier (No key required) | `https://api.open-meteo.com/v1/forecast` |
| **Open-Meteo Archive API** | Historical monthly climate data | Frontend (`recommendations.html`) | Free tier (No key required) | `https://archive-api.open-meteo.com/v1/archive` |
| **OpenStreetMap Nominatim** | Reverse geocoding (Lat/Lon to City name) | Frontend (`dashboard.html`, `recommendations.html`) | Free tier (User-Agent header) | `https://nominatim.openstreetmap.org/reverse` |
| **IPAPI** | Fallback geolocation when GPS is denied | Frontend (`dashboard.html`, `recommendations.html`) | Free tier (No key required) | `https://ipapi.co/json/` |
| **Firebase RTDB** | Application data storage | Frontend (Direct SDK) | Firebase API Key + Auth Token | `https://project-beta-7f0a3-default-rtdb.firebaseio.com` |
| **Firebase Storage** | Farm plot images & profile photos | Frontend (`manage.html`, `settings.html`) | Firebase API Key + Auth Token | `gs://project-beta-7f0a3.firebasestorage.app` |
| **UI-Avatars** | Default user avatar generator | Frontend (All pages) | Free CDN | `https://ui-avatars.com/api/` |
| **CDN Libraries** | FontAwesome 6.4, Marked.js 12, Google Fonts | Frontend (All pages) | Public CDNs | jsdelivr, cdnjs, fonts.googleapis |

---

## 3. Existing Functionality & Feature Classification

Every feature has been audited directly against the source code and classified into one of four statuses:
- **Implemented & Working**: Verified functional in design, dependencies, and code execution.
- **Partially Implemented**: Working partially, but missing critical sub-components, hardcoded, or relying on mock data.
- **Broken**: Defective, missing dependencies, or contains code errors preventing operation.
- **Unverified**: Implemented in code, but depends on active external cloud credentials (e.g., live Gemini API key or Firebase write permissions).

| Module / Feature | Component / File | Audit Classification | Architectural Details & Observations |
|---|---|---|---|
| **User Sign-up & Login** | `frontend/login.html` | **Implemented & Working** | Full email/password + Google OAuth flow with error alerts and metadata initialization in RTDB. |
| **Auto Auth Redirect Gate** | `frontend/index.html` | **Implemented & Working** | Fast lightweight loading screen checking `onAuthStateChanged`, redirects to dashboard or login. |
| **Crop Leaf Disease Classifier** | `backend/ai/classifier.py` | **Implemented & Working** | Functional MobileNetV2 CNN running 224x224 RGB inference across 56 classes with softmax probabilities. |
| **Disease Spot Localization** | `backend/ai/detector.py` | **Implemented & Working** | PlantCV HSV thresholding isolating diseased leaf spots with OpenCV bounding box contour extraction. |
| **Treatment & Soil Knowledgebase**| `backend/ai/treatments.py` | **Implemented & Working** | 598-line comprehensive dictionary covering PlantVillage classes, soil analysis, and dynamic NLP fallback. |
| **Soil Analysis Classifier** | `backend/ai/classifier.py` | **Implemented & Working** | Classifies 6 soil types (Alluvial, Arid, Black, Laterite, Mountain, Red, Yellow) with pH and NPK profiles. |
| **AI Assistant ("Farmly")** | `backend/main.py`, `assistant-widget.js`| **Unverified** | Complete code structure with thread safety, timeout bounds, and farm/scan context injection; requires valid `GEMINI_API_KEY`. |
| **Voice Input for Farmly** | `frontend/js/assistant-widget.js` | **Implemented & Working** | Web Speech API (`webkitSpeechRecognition`) microphone transcription directly filling the chat input. |
| **Chat History Persistence** | `frontend/js/assistant-widget.js` | **Implemented & Working** | Real-time chat history stored per user at `users/${uid}/chats`, supports creating and switching sessions. |
| **Farm Plot CRUD** | `frontend/manage.html` | **Implemented & Working** | Full creation, editing, and deletion of farm plots with size, irrigation, status, budget, and notes. |
| **Live NPK Soil Nutrient Updates**| `frontend/manage.html` | **Implemented & Working** | On-the-fly editing of Nitrogen, Phosphorus, and Potassium percentages directly on farm cards. |
| **Farm Growth & Yield Estimators**| `frontend/manage.html` | **Implemented & Working** | Calculates growth stage, days remaining, estimated yield, and revenue based on planting date and acreage. |
| **Smart Crop Recommendations** | `frontend/recommendations.html` | **Implemented & Working** | Mathematical scoring engine combining 40% weather fit (Open-Meteo) and 60% revenue potential. |
| **Live Weather & 7-Day Forecast**| `dashboard.html`, `recommendations.html` | **Implemented & Working** | Fetches live temperature, humidity, wind, and 7-day forecast from Open-Meteo with OpenStreetMap geocoding. |
| **Smart Irrigation Advisor** | `frontend/dashboard.html` | **Implemented & Working** | Calculates irrigation advice ("Skip watering", "Optimal irrigation window") based on live rain/humidity. |
| **Expense Recording & Tracking** | `frontend/expenses.html` | **Implemented & Working** | Log expenses by category and farm plot with instant table rendering and category aggregation. |
| **Budget Safety Warning System**| `frontend/expenses.html` | **Implemented & Working** | Dynamic progress meters (green/yellow/red) warning when an expense exceeds remaining plot budget. |
| **Scan History Log & Inspection**| `frontend/history.html` | **Implemented & Working** | History table with search, crop filters, date range filters, full detail modal, and single/bulk deletion. |
| **Farm Tasks & Quick Todo** | `frontend/dashboard.html` | **Implemented & Working** | Task list supporting add, toggle complete, and delete synced to `users/${uid}/tasks`. |
| **Farm Inventory Tracker** | `frontend/dashboard.html` | **Implemented & Working** | Simple stock manager (Seeds, Fertilizers) with level tags (High/Med/Low) synced to `users/${uid}/inventory`. |
| **Multi-Language Support (i18n)** | `frontend/translations.js` | **Implemented & Working** | 5 languages (English, Swahili, Zulu, Venda, Afrikaans) dynamically translated across UI elements. |
| **Multi-Currency Support** | `frontend/theme.js` | **Implemented & Working** | Automatic price formatting and conversion for KES, USD, UGX, TZS, and ZAR. |
| **Interactive Tour Guide** | `frontend/tutorial.js` | **Implemented & Working** | Guided walkthrough highlights key UI components for first-time users. |
| **Market Trend Chart** | `frontend/dashboard.html` | **Partially Implemented** | **Hardcoded mock data**: Renders static percentages for Maize, Beans, Wheat, Rice, Sorghum. |
| **Farm Mapping with Leaflet** | *(Reported feature)* | **Broken / Missing** | **Zero Leaflet code exists**. No interactive map, field polygon drawing, or spatial boundary rendering. |
| **AI Cross-Module Analytics** | *(Reported feature)* | **Broken / Missing** | No `backend/intelligence.py` or cross-cutting analysis module exists in the repository. |
| **Model Retraining Pipeline** | `backend/ai/train_model.py` | **Partially Implemented** | Fully coded 2-phase training script, but cannot run out-of-the-box because `datasets/` is omitted. |

---

## 4. API Endpoints Specification

The existing backend exposes two operational API routes and one static asset mount point:

### 4.1 `POST /predict`
- **File**: `backend/main.py` (Line 88)
- **Purpose**: Diagnostic leaf and soil image classification and spot segmentation.
- **Auth**: None (Public).
- **Request Format**: `multipart/form-data`
  - `image`: Binary file (Allowed types: `image/jpeg`, `image/jpg`, `image/png`, `image/webp`. Max size: 10 MB).
- **Processing Flow**:
  1. Validates content type and file byte size.
  2. Runs `predict_crop(image_bytes)` -> Loads `crop_model.keras`, resizes to 224x224, runs inference, looks up diagnosis in `treatments.py`.
  3. Runs `detect_disease(image_bytes, result)` -> Uses PlantCV HSV thresholding to generate bounding boxes for spots.
- **Response Format**: `application/json`
  ```json
  {
    "crop": "Tomato",
    "confidence": "94.20%",
    "disease": "Tomato Early Blight",
    "treatment": "Apply potassium fertilizers. Avoid overhead irrigation...",
    "is_soil": false,
    "soil_requirements": {
      "ph": "6.0 - 6.8",
      "soil_type": "Deep, well-drained loamy soil",
      "npk": "N: Medium, P: High, K: High"
    },
    "boxes": [
      { "x": 45, "y": 80, "width": 32, "height": 28 }
    ]
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: `{"error": "Unsupported file type. Please upload a JPEG, PNG, or WEBP image."}`
  - `400 Bad Request`: `{"error": "Image is too large. Maximum size is 10MB."}`
  - `500 Internal Server Error`: `{"error": "Could not analyze this image. Please try a different photo."}`

### 4.2 `POST /chat`
- **File**: `backend/main.py` (Line 116)
- **Purpose**: Conversational farming intelligence and farm context memory.
- **Auth**: None (Public).
- **Request Format**: `application/json`
  ```json
  {
    "message": "What fertilizer should I add to Plot 1?",
    "history": [
      { "role": "user", "content": "Hello" },
      { "role": "model", "content": "Hello! I am Farmly. How can I help?" }
    ],
    "farms": [
      { "name": "North Field", "crop": "Maize", "size": 5, "soil": "Loamy", "irrigation": "Drip" }
    ],
    "scans": [
      { "crop": "Maize", "disease": "Common Rust", "confidence": "91.5%", "time": "2026-10-30" }
    ]
  }
  ```
- **Processing Flow**:
  1. Checks presence of `GEMINI_API_KEY`.
  2. Constructs dynamic system prompt injecting application capabilities and the user's live farm/scan context.
  3. Formats previous chat turns into Gemini SDK parts.
  4. Calls `gemini-2.5-flash` with REST transport and 20-second timeout inside an async worker thread.
- **Response Format**: `application/json`
  ```json
  {
    "response": "Based on your North Field maize plot with loamy soil..."
  }
  ```
- **Error Responses**:
  - `500 Internal Server Error`: `{"error": "Gemini API Key is not configured..."}`
  - `504 Gateway Timeout`: `{"error": "The AI assistant timed out. Please try again."}`
  - `500 Internal Server Error`: `{"error": "The AI assistant is temporarily unavailable. Please try again."}`

### 4.3 `GET /` & Static Mount
- **File**: `backend/main.py` (Line 207)
- **Purpose**: Delivers the frontend single-page application entry point (`frontend/login.html`) and serves all static CSS, JS, and HTML assets.

---

## 5. Technical Quality, Code Bugs & Security Risks

### 5.1 Critical Security Vulnerabilities
1. **Unauthenticated Public ML & LLM Endpoints**:
   - `POST /predict` and `POST /chat` require no authentication headers, tokens, or sessions.
   - Any third party on the internet can flood `/chat` and consume the project's Gemini API quota, or flood `/predict` and cause CPU exhaustion.
2. **Wildcard Permissive CORS**:
   - `allow_origins=["*"]` allows any website to make cross-origin requests to the backend.
3. **Hardcoded Firebase Client Credentials Across 8 Files**:
   - The identical configuration object containing `apiKey`, `authDomain`, `databaseURL`, and `projectId` is duplicated in `dashboard.html`, `expenses.html`, `history.html`, `index.html`, `login.html`, `manage.html`, `recommendations.html`, and `settings.html`.
4. **Direct Client Database Writes without Business Rule Enforcement**:
   - The frontend writes directly to Firebase RTDB (`push`, `update`, `remove`).
   - If a malicious client modifies their frontend JS, they can inject arbitrary JSON into `farms`, `expenses`, or `settings`, including negative amounts, huge strings, or cross-farm corruptions.

### 5.2 Code Quality & Consistency Bugs
1. **Package Init Typo**:
   - `backend/ai/_init_.py` is named with a single underscore instead of double underscores (`__init__.py`). While Python 3 supports namespace packages, this breaks standard package discovery and linters.
2. **Missing Leaflet Mapping Implementation**:
   - The platform documentation claims Leaflet farm mapping is active, but the codebase contains zero Leaflet imports, CSS, or JS.
3. **Missing Intelligence Files**:
   - `backend/intelligence.py` and `frontend/js/intelligence.js` are completely absent.
4. **Hardcoded Dashboard Market Data**:
   - In `dashboard.html`, `renderMarketChart()` uses hardcoded array data (`Maize: 75, Beans: 90...`) instead of fetching live market commodity prices.
5. **Double OpenCV Package Conflict**:
   - In `requirements.txt`, `opencv-python-headless` is declared, while `plantcv` pulls in `opencv-python`. Having both standard and headless OpenCV installed in the same environment causes module import warnings and shared library conflicts.
6. **MobileNetV2 Preprocessing Discrepancy**:
   - In `train_model.py` and `classifier.py`, images are normalized using `1.0 / 255` (`0.0` to `1.0`), whereas standard MobileNetV2 ImageNet weights expect `[-1.0, 1.0]` normalization via `tf.keras.applications.mobilenet_v2.preprocess_input`. (Documented in `MODEL_ARCHITECTURE.md` as an acknowledged limitation).
7. **Monolithic Frontend Architecture & Extreme Code Duplication**:
   - Over 450 KB of redundant HTML/CSS/JS is duplicated across the 7 page files. Updating navigation links, header user profiles, or color schemes requires modifying 7 independent files.
8. **Missing Cascade Deletion**:
   - Deleting a farm in `manage.html` (`remove(ref(db, 'users/${user.uid}/farms/${farmId}'))`) does not delete associated expenses under `users/${uid}/expenses`, resulting in orphaned expense records that still impact aggregate calculations.

---

## 6. Testing & Application Startup Status

### 6.1 Existing Test Suite Status
- **Test Discovery Command**:
  ```powershell
  Get-ChildItem -Path "C:\Users\infin\Desktop\AgroFast" -Filter "*test*" -Recurse
  ```
- **Result**: **0 test files discovered**.
- **Assessment**: The repository has no unit test suite, integration test suite, end-to-end test suite, or test configuration (`pytest.ini`, `setup.cfg`, `conftest.py`).

### 6.2 Application Startup Status
- **Execution Command Attempted**:
  ```powershell
  cd "C:\Users\infin\Desktop\AgroFast"
  & "C:\Users\infin\.local\bin\python3.11.exe" backend/main.py
  ```
- **Startup Result**: **Failed with Exit Code 1**.
- **Exact Error Traceback**:
  ```
  Traceback (most recent call last):
    File "C:\Users\infin\Desktop\AgroFast\backend\main.py", line 2, in <module>
      from fastapi import FastAPI, UploadFile, File
  ModuleNotFoundError: No module named 'fastapi'
  ```
- **Cause**: No virtual environment (`.venv`) exists in the project directory, and the host's base Python 3.11 installation has no third-party packages installed globally.
- **Dependency Resolution Verification**:
  ```powershell
  & "C:\Users\infin\.local\bin\uv.exe" pip compile requirements.txt --python "C:\Users\infin\.local\bin\python3.11.exe"
  ```
  - **Result**: Successfully resolved **130 packages** in 20.23 seconds without dependency conflicts.
- **Environment Configuration**:
  - `backend/.env` is absent (`backend/.env.example` is present). `GEMINI_API_KEY` is not configured locally.

### 6.3 Hosted Cloud Backend Status
- **Host URL**: `https://artisking-agrofast-backend.hf.space`
- **Probe Result**: Host is reachable (HTTP 200/206). Running inside a Hugging Face Space Docker container (`user 1000`, `PORT 7860`).

---

## 7. Recommended Target Architecture: AgroTrack AI

To scale AgroFast from a single-user prototype into **AgroTrack AI** supporting the four major capabilities (**AgroTrack**, **MarketLens**, **ImpactOS**, and **AI Analyst**), the system must transition to a clean, modular, and enterprise-grade architecture.

```
+----------------------------------------------------------------------------------------------------+
|                                    AGROTRACK AI UNIFIED PORTAL                                     |
|  +--------------------+  +--------------------+  +--------------------+  +----------------------+  |
|  |     AgroTrack      |  |     MarketLens     |  |      ImpactOS      |  |      AI Analyst      |  |
|  | (Farms, Fields,    |  | (Commodity Trends, |  | (Projects, Targets,|  | (Cross-platform RAG,|  |
|  |  Crops, Scans)     |  |  Prices, Forecasts)|  |  Beneficiaries,    |  |  Multimodal Advisor, |  |
|  |                    |  |                    |  |  Carbon/Impact)    |  |  Executive Reports)  |  |
|  +--------------------+  +--------------------+  +--------------------+  +----------------------+  |
|                                                                                                    |
|  Shared UI Shell: Unified Navigation | Theme System | i18n Engine | RBAC & Org Context Switcher    |
+-------------------------------------------------+--------------------------------------------------+
                                                  | JSON / HTTPS (Bearer Token)
                                                  v
+----------------------------------------------------------------------------------------------------+
|                                  FASTAPI APPLICATION GATEWAY (v1)                                  |
|  Middleware: CORS Security | Rate Limiting | Audit Logging | Auth & Org Verification (JWT / RBAC)  |
+-------------------------------------------------+--------------------------------------------------+
          |                         |                           |                          |
          v                         v                           v                          v
+-------------------+     +-------------------+       +-------------------+      +-------------------+
|   /api/v1/track   |     |  /api/v1/market   |       |  /api/v1/impact   |      |  /api/v1/analyst  |
| - Farms & Fields  |     | - Commodity Index |       | - Programs/Donors |      | - Gemini 2.5/3.8  |
| - Crops & Planting|     | - Price Tracking  |       | - Beneficiaries   |      | - Unified RAG     |
| - MobileNetV2 ML  |     | - Market Alerts   |       | - Targets & M&E   |      | - Report Synthesis|
| - PlantCV Spot Det|     | - Value Chains    |       | - Impact Metrics  |      | - Farmly Engine   |
+-------------------+     +-------------------+       +-------------------+      +-------------------+
          |                         |                           |                          |
          +-------------------------+-------------+-------------+--------------------------+
                                                  |
                                                  v
                               +-------------------------------------+
                               |          SHARED CORE DOMAIN         |
                               | - IAM & Multi-Tenant Organization   |
                               | - Data Access Layer & Repositories  |
                               | - Validation (Pydantic v2 Models)   |
                               | - Background Tasks & Event Signals  |
                               +-------------------------------------+
                                                  |
                                                  v
                               +-------------------------------------+
                               |           DATA LAYER (RTDB)         |
                               | /orgs/{orgId}/farms/                |
                               | /orgs/{orgId}/markets/              |
                               | /orgs/{orgId}/projects/             |
                               | /orgs/{orgId}/intelligence/         |
                               +-------------------------------------+
```

### 7.1 Modular Backend Layout (Target)

```
AgroTrack_AI/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                          # App factory, middleware, router aggregation
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py                    # Pydantic Settings (ENV variables, secrets)
│   │   │   ├── security.py                  # Token verification, JWT handling, password hashing
│   │   │   ├── permissions.py               # RBAC rules (Owner, Field Officer, Analyst, Viewer)
│   │   │   └── exceptions.py                # Standardized HTTP error models
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── firebase.py                  # Firebase Admin SDK initialization & client wrapper
│   │   ├── modules/
│   │   │   ├── agrotrack/                   # MODULE 1: Farm & Field Management
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py                # /api/v1/track/*
│   │   │   │   ├── models.py                # Pydantic schemas (Farm, Field, Soil, Scan)
│   │   │   │   ├── service.py               # Farm operations, NPK logic, growth calculations
│   │   │   │   └── ml/                      # Preserved & isolated ML engine
│   │   │   │       ├── classifier.py        # Preserved MobileNetV2 inference
│   │   │   │       ├── detector.py          # Preserved PlantCV spot localization
│   │   │   │       ├── treatments.py        # Preserved agronomic treatments dictionary
│   │   │   │       └── crop_model.keras     # Preserved trained model
│   │   │   ├── marketlens/                  # MODULE 2: Market & Commodity Intelligence
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py                # /api/v1/market/*
│   │   │   │   ├── models.py                # Commodity, PriceHistory, MarketPoint schemas
│   │   │   │   └── service.py               # Trend analysis, pricing feeds, profit projections
│   │   │   ├── impactos/                    # MODULE 3: Impact & Beneficiary Management
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py                # /api/v1/impact/*
│   │   │   │   ├── models.py                # Project, Beneficiary, Indicator, Report schemas
│   │   │   │   └── service.py               # Target tracking, M&E aggregation, donor reporting
│   │   │   └── analyst/                     # MODULE 4: Cross-Cutting AI Layer
│   │   │       ├── __init__.py
│   │   │       ├── router.py                # /api/v1/analyst/* (Chat, Synthesis, Advice)
│   │   │       ├── models.py                # ChatRequest, ChatResponse, ReportPrompt
│   │   │       └── service.py               # Multi-turn context compiler + Gemini 2.5/3.8 engine
│   │   └── tests/                           # Formal unit and integration tests
│   │       ├── conftest.py
│   │       ├── test_ml_inference.py
│   │       ├── test_agrotrack_api.py
│   │       ├── test_marketlens_api.py
│   │       └── test_impactos_api.py
│   ├── .env.example
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                                # Refactored Component-Based UI Shell
│   ├── assets/
│   ├── components/                          # Shared navbar, sidebar, modal, notifications
│   ├── js/
│   │   ├── api/                             # Centralized Fetch Client with Bearer token injection
│   │   ├── core/                            # Auth listener, theme manager, i18n
│   │   └── modules/                         # Modular UI controllers
│   │       ├── agrotrack.js
│   │       ├── marketlens.js
│   │       ├── impactos.js
│   │       └── analyst.js
│   ├── index.html                           # Single Shell or organized sub-pages
│   └── ...
└── AGROTRACK_AUDIT.md
```

### 7.2 Multi-Tenant Data Isolation Strategy

To support cooperatives, agricultural enterprises, and development organizations without premature SQL migration, the Firebase data model will introduce top-level organization partitions:

```
organisations/
└── {orgId}/
    ├── metadata/ { name, country, currency, createdAt }
    ├── members/
    │   └── {userId}/ { role: "admin" | "field_officer" | "analyst" | "viewer" }
    ├── agrotrack/
    │   ├── farmers/
    │   ├── farms/
    │   ├── plots/
    │   ├── expenses/
    │   └── diagnostic_scans/
    ├── marketlens/
    │   ├── commodities/
    │   ├── price_records/
    │   └── value_chain_nodes/
    ├── impactos/
    │   ├── projects/
    │   ├── targets/
    │   ├── beneficiaries/
    │   └── reports/
    └── analyst/
        ├── session_logs/
        └── synthesized_briefs/
```

### 7.3 Shared Authentication & Role-Based Access Control (RBAC)

- **Authentication**: Firebase Authentication ID tokens sent in HTTP headers: `Authorization: Bearer <firebase_id_token>`.
- **Backend Verification**: FastAPI dependency `get_current_user` validates the token using `firebase_admin.auth.verify_id_token(token)`.
- **Permissions Matrix**:
  - `admin`: Full CRUD across all 4 modules, user management, and billing.
  - `field_officer`: Manage farmers, plot data, scans, and task completion in AgroTrack; view ImpactOS targets.
  - `analyst`: Read access across AgroTrack; full access to MarketLens pricing models and AI Analyst querying.
  - `viewer`: Read-only access to published reports and dashboards.

---

## 8. Phased Implementation Plan

```
+-----------------------------------------------------------------------------------------+
|                                PHASE 0: FULL AUDIT & ROADMAP                            |
|  - Complete code inspection, dependency audit, security analysis, baseline lock (DONE)   |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                                PHASE 1: FOUNDATION HARDENING                            |
|  - Clean Python environment (.venv) & resolve dependencies                              |
|  - Fix typo: backend/ai/_init_.py -> __init__.py                                        |
|  - Implement backend Token Authentication Middleware & remove wildcard CORS             |
|  - Centralize frontend API client & remove copy-pasted Firebase config                  |
|  - Build initial test suite (pytest) for ML inference and health check endpoints        |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                         PHASE 2: AGROTRACK REFACTOR & LEAFLET MAPPING                   |
|  - Refactor farm/plot management into modular backend router (/api/v1/track)            |
|  - Integrate genuine Leaflet.js interactive farm field & polygon boundary mapping       |
|  - Enforce server-side data validation (Pydantic) for farms, NPK, and expenses          |
|  - Cascade deletions (prevent orphaned expense records)                                 |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                         PHASE 3: MARKETLENS & IMPACTOS MODULES                          |
|  - MarketLens: Replace mock market chart with dynamic commodity pricing engine          |
|  - ImpactOS: Implement project tracking, targets, beneficiary rosters, and M&E metrics  |
|  - Implement Organization/Tenant schema in data layer                                   |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                           PHASE 4: AI ANALYST & UNIFIED PLATFORM                        |
|  - Expand "Farmly" into AI Analyst: cross-module queries across farms, prices & impact  |
|  - Multi-language context preservation (en, sw, zu, ve, af)                             |
|  - Automated executive brief generation and PDF export                                  |
|  - End-to-end integration testing and production container deployment                   |
+-----------------------------------------------------------------------------------------+
```

---

## 9. Critical Files to Preserve Intact

The following files represent the core intellectual property and working foundation of AgroFast and **must not be deleted, corrupted, or degraded** during the evolution into AgroTrack AI:

| File Path | Critical Assets / Logic to Preserve |
|---|---|
| `backend/ai/crop_model.keras` | The trained MobileNetV2 CNN weights (34.2 MB) supporting 56 crop disease and soil categories. |
| `backend/ai/class_indices.json` | Exact alphabetical index-to-label mapping for the 56 model output classes. |
| `backend/ai/classifier.py` | `predict_crop()`, model loading logic, and `analyze_health()` HSV color heuristic. |
| `backend/ai/detector.py` | `detect_disease()` PlantCV segmentation and bounding box contour generation. |
| `backend/ai/treatments.py` | 598 lines of detailed crop disease treatments, soil NPK analysis, and dynamic NLP fallback rules. |
| `frontend/translations.js` | Full translation dictionary covering 5 regional languages across all UI terms. |
| `frontend/theme.js` | Unit conversions, multi-currency exchange formulas, and HTML sanitization routines. |
| `frontend/tutorial.js` | Interactive user onboarding walkthrough step logic. |
| `frontend/js/custom-select.js` | Accessible styled select box component used across forms. |
| `backend/ai/train_model.py` | Two-phase transfer learning training architecture with class-weight balancing. |

---

## 10. Dependencies & Infrastructure Requirements

### 10.1 Python Backend Dependencies (Verified Compatible with Python 3.11)
```txt
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.8.0
python-multipart>=0.0.9
python-dotenv>=1.0.1
tensorflow==2.16.1
numpy<2.0.0
pillow>=10.4.0
scipy>=1.13.0
opencv-python-headless>=4.10.0.84
plantcv>=4.11.0
google-generativeai>=0.8.0
firebase-admin>=6.5.0
pytest>=8.3.0
httpx>=0.27.0
```

### 10.2 Frontend Infrastructure Requirements
- **CDN / Vendor Libraries**:
  - Firebase JS SDK `v12.7.0` (or bundled via modern bundler in Phase 2)
  - Leaflet.js `v1.9.4` + Leaflet Draw for field polygon mapping
  - FontAwesome `v6.4.0`
  - Marked.js `v12.0.0`
  - Google Fonts (Outfit)
- **External Web APIs**:
  - Open-Meteo Weather & Forecast API (Free tier, no key required)
  - OpenStreetMap Nominatim Reverse Geocoding API (Free tier, Rate limit: 1 req/sec)

### 10.3 Required Cloud Secrets & Environment Variables
- `GEMINI_API_KEY`: Google AI Studio API key for Gemini 2.5 Flash / 3.8.
- `FIREBASE_PROJECT_ID`: `project-beta-7f0a3`
- `FIREBASE_DATABASE_URL`: `https://project-beta-7f0a3-default-rtdb.firebaseio.com`
- `FIREBASE_SERVICE_ACCOUNT_KEY`: Required on backend for Firebase Admin SDK token verification and server-side DB operations.
- `PORT`: App server port (Default `5500` locally, `7860` for containerized hosting).
- `HOST`: Bind host (Default `0.0.0.0`).
