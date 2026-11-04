import os
import sys

# Ensure repository root is on sys.path so 'backend' package imports always succeed
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, UploadFile, File
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from fastapi.responses import FileResponse, JSONResponse
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
# pyrefly: ignore [missing-import]
import uvicorn
import os
import asyncio
# pyrefly: ignore [missing-import]
import google.generativeai as genai
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
try:
    from backend.ai.classifier import predict_crop
    from backend.ai.detector import detect_disease
    from backend.agrotrack.quality import is_valid_image_header
except ImportError:
    from ai.classifier import predict_crop
    from ai.detector import detect_disease
    from agrotrack.quality import is_valid_image_header

# Force IPv4-only DNS resolution for outbound calls. On some container hosts
# (e.g. Hugging Face Spaces) DNS advertises an IPv6 route to Google's APIs
# that isn't actually reachable, and gRPC's fallback-to-IPv4 behavior can
# stall for a long time before giving up. Disabling AF_INET6 results here
# makes the underlying gRPC/HTTP client skip straight to IPv4.
import socket
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_only_getaddrinfo

# Belt-and-suspenders: never let google-auth fall back to probing the GCE
# metadata server (which can hang 20-90s on non-GCP hosts) — this app always
# authenticates with an explicit API key, never Application Default Credentials.
os.environ.setdefault("NO_GCE_CHECK", "true")

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def _clean_api_key(raw):
    """Tolerate a misconfigured key/secret: strip whitespace/newlines, an
    accidentally-included 'GEMINI_API_KEY=' prefix (e.g. when the whole .env
    line is pasted as a Hugging Face secret value), and surrounding quotes.
    A newline or '=' in the value otherwise crashes the REST auth header."""
    if not raw:
        return raw
    key = raw.strip().strip('"').strip("'").strip()
    if key.startswith("GEMINI_API_KEY="):
        key = key.split("=", 1)[1].strip().strip('"').strip("'").strip()
    return key

GEMINI_API_KEY = _clean_api_key(os.getenv("GEMINI_API_KEY"))
if GEMINI_API_KEY:
    # transport="rest" avoids the gRPC C-core transport, which has multiple
    # open upstream reports of indefinite socket stalls with no exception
    # and no timeout (e.g. googleapis/python-genai#1893). REST uses Python's
    # ordinary HTTP stack, so request_options={"timeout": ...} reliably bounds it.
    genai.configure(api_key=GEMINI_API_KEY, transport="rest")

GEMINI_TIMEOUT_SECONDS = 20


app = FastAPI(
    title="AgroTrack AI Platform API",
    description="Agricultural Intelligence and Development Management Platform — Core Foundation API",
    version="1.0.0"
)

try:
    from backend.api import router as api_v1_router
    from backend.agrotrack.router import router as agrotrack_router
    from backend.marketlens.router import router as marketlens_router
    from backend.impactos.router import router as impactos_router
    from backend.analyst.router import router as analyst_router
except ImportError:
    from api import router as api_v1_router
    from agrotrack.router import router as agrotrack_router
    from marketlens.router import router as marketlens_router
    from impactos.router import router as impactos_router
    from analyst.router import router as analyst_router

app.include_router(api_v1_router)
app.include_router(agrotrack_router)
app.include_router(marketlens_router)
app.include_router(impactos_router)
app.include_router(analyst_router)

# Initialize Firebase Admin SDK if service account key is configured
try:
    from backend.firebase import initialize_firebase
    initialize_firebase()
except ImportError:
    try:
        from firebase import initialize_firebase
        initialize_firebase()
    except Exception as e:
        print(f"[!] Firebase Admin initialization notice: {e}")
except Exception as e:
    print(f"[!] Firebase Admin initialization notice: {e}")

from typing import List, Optional, Any

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = None
    scans: Optional[List[Any]] = None
    farms: Optional[List[Any]] = None

# CORS Configuration (Production Hardened with Configurable Origins)
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
if not allowed_origins:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Production Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}

@app.post("/predict")
async def predict(image: UploadFile = File(...)):
    print(f"Received image: {image.filename} ({image.content_type})")

    if image.content_type not in ALLOWED_IMAGE_TYPES:
        return JSONResponse(status_code=400, content={"error": "Unsupported file type. Please upload a JPEG, PNG, or WEBP image."})

    image_bytes = await image.read()
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        return JSONResponse(status_code=400, content={"error": "Image is too large. Maximum size is 10MB."})

    if not is_valid_image_header(image_bytes):
        return JSONResponse(status_code=400, content={"error": "Invalid image binary header. Please upload a genuine JPEG, PNG, or WEBP image."})

    try:
        # Get AI classification and health summary (runs the model once)
        result = predict_crop(image_bytes)

        # Get detailed "Real Scanning" data (bounding boxes for spots),
        # reusing the classification above instead of re-running the model
        detection = detect_disease(image_bytes, result)

        # Merge results
        result["boxes"] = detection.get("boxes", [])
        result["severity_percentage"] = detection.get("severity_percentage", 0.0)
        result["severity_level"] = detection.get("severity_level", "None (Healthy)")

        return result
    except Exception as e:
        print(f"Error during prediction: {str(e)}")
        # Don't leak internal exception details to the client
        return JSONResponse(status_code=500, content={"error": "Could not analyze this image. Please try a different photo."})

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not GEMINI_API_KEY:
        return JSONResponse(status_code=500, content={"error": "Gemini API Key is not configured. Please add GEMINI_API_KEY to your backend/.env file."})
    
    try:
        system_instruction = (
            "You are an expert agricultural AI assistant named Farmly. "
            "Provide helpful, accurate, brief, and highly effective advice to farmers regarding crops, diseases, pests, and farm management. "
            "CRITICAL: Always detect the language of the user's query and respond in that exact language (the application supports and translates to English, Swahili, Zulu, Venda, and Afrikaans). "
            "Keep your responses concise, direct, action-oriented, and easy to read. Avoid long paragraphs; use brief bullet points or short sentences. "
            "Base your answers on best farming practices. Format your responses using Markdown for better readability.\n\n"
            "You also have comprehensive knowledge about AgroFast (this application) and can explain its features to users if they ask. "
            "Key features of AgroFast (the app you power as Farmly) include:\n"
            "1. **Smart Auth**: Secure registration and login using Firebase, with customized farm profiles.\n"
            "2. **Manage Farms**: Add, edit, or delete multiple farm plots, specifying soil type, irrigation type, water source, planting dates, and soil nutrients (NPK % values) which can be updated live from the cards.\n"
            "3. **AI Leaf Diagnostics (AI Scanner / Crop Scanner)**: Scan crop leaf photos to detect diseases. It runs on a trained convolutional neural network (achieving a validation accuracy of 91% across 58 agricultural classes, covering apple, pepper, maize, mango, potato, tomato, coffee, cassava, rice, tea, and wheat leaf categories).\n"
            "4. **Smart Crop Recommendations Engine**: Auto-detects location via GPS to fetch live temperature, humidity, wind, and feels-like temperature (using Open-Meteo). Predicts month-by-month profitability based on a custom scoring algorithm: 40% Weather Fit (compares crop requirements with monthly forecasts) and 60% Revenue Score (based on market price and yield per acre).\n"
            "5. **Expense Tracker & Budget Safety**: Record and track farm expenses by category (e.g. Seeds, Fertilizer, Labor) for each farm plot. Displays visual color-coded budget progress meters (green to yellow to red) and has a Budget Warning System that cautions users when an expense exceeds their budget, suggesting a safe budget buffer.\n"
            "6. **User Interface & UX**: Sleek, modern, and dark-mode interface, featuring multi-language translations (dynamic translations file) and an interactive step-by-step tour tutorial guide."
        )

        # Inject real-time user context (farms and scans) to make the assistant "remember" them
        context_parts = []
        if request.farms:
            farms_desc = "\nHere are the user's farms that they currently manage:\n"
            for f in request.farms:
                name = f.get('name', 'Unnamed Plot')
                crop = f.get('crop', 'None')
                size = f.get('size', 'Unknown')
                soil = f.get('soil', 'Unknown')
                irrigation = f.get('irrigation', 'Unknown')
                farms_desc += f"- Plot Name: {name}, Main Crop: {crop}, Size: {size} acres, Soil: {soil}, Irrigation: {irrigation}\n"
            context_parts.append(farms_desc)

        if request.scans:
            scans_desc = "\nHere are the user's recent crop diagnostic scan records:\n"
            # Take last 5 scans to avoid context bloat
            recent_scans = request.scans[-5:]
            for s in recent_scans:
                crop_name = s.get('crop', 'Unknown Crop')
                disease = s.get('disease', 'Healthy')
                time_val = s.get('time', 'Unknown Time')
                confidence = s.get('confidence', '100%')
                scans_desc += f"- Scanned {crop_name}: result was '{disease}' with {confidence} confidence (date: {time_val})\n"
            context_parts.append(scans_desc)

        if context_parts:
            system_instruction += "\n\n### USER REAL-TIME CONTEXT (REMEMBERED FARMS AND SCANS):\n" + "\n".join(context_parts)

        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_instruction)
        
        # Format the chat history into the structure expected by the Gemini SDK
        history = []
        if request.history:
            for msg in request.history:
                role = "user" if msg.role == "user" else "model"
                history.append({
                    "role": role,
                    "parts": [msg.content]
                })
        
        chat = model.start_chat(history=history)

        def _call_gemini():
            # request_options timeout bounds the REST call itself; this only
            # takes effect reliably because transport="rest" was set above.
            return chat.send_message(
                request.message,
                request_options={"timeout": GEMINI_TIMEOUT_SECONDS},
            )

        try:
            # Run the blocking SDK call in a worker thread so it can never
            # freeze the single asyncio event loop (which would otherwise
            # also stall unrelated /predict requests), and enforce a hard
            # outer deadline so the client always gets a response even if
            # the SDK-level timeout fails to fire on a true socket stall.
            response = await asyncio.wait_for(
                asyncio.to_thread(_call_gemini),
                timeout=GEMINI_TIMEOUT_SECONDS + 5,
            )
        except asyncio.TimeoutError:
            print("Gemini call exceeded outer deadline")
            return JSONResponse(status_code=504, content={"error": "The AI assistant timed out. Please try again."})

        return {"response": response.text}
    except Exception as e:
        print(f"Error in chat: {str(e)}")
        return JSONResponse(status_code=500, content={"error": "The AI assistant is temporarily unavailable. Please try again."})

# Serve Static Files (only present when running alongside the frontend locally;
# a backend-only deploy, e.g. a Docker/cloud host, won't have this directory)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.isdir(frontend_path):
    @app.get("/")
    async def read_index():
        target_file = "index.html" if os.path.exists(os.path.join(frontend_path, "index.html")) else "login.html"
        return FileResponse(os.path.join(frontend_path, target_file))

    # Mount frontend at root BUT after specific API routes to ensure they take precedence
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    @app.get("/")
    async def read_index():
        return {"status": "AgroFast backend is running"}

if __name__ == "__main__":
    # HOST/PORT are set by cloud hosts (e.g. Hugging Face Spaces needs 0.0.0.0:7860);
    # defaults to 127.0.0.1:5500 locally to match the dashboard's compatibility checks.
    # host = os.getenv("HOST", "127.0.0.1")
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5500))
    uvicorn.run(app, host=host, port=port)
