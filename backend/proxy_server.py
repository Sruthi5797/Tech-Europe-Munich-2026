"""
LiverLink — Proxy Server
Serves index.html, upload.html, and proxies /apps/* and /run to the ADK server.
Everything on one origin → no CORS issues.
"""

import httpx
import json
from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timezone
from tavily import TavilyClient
from google import genai
from google.genai import types

ADK_BASE = "http://127.0.0.1:8000"
APP_NAME = "liverlink_pipeline"
HERE = Path(__file__).parent

# Load environment variables from the root folder
dotenv_path = HERE.parent / ".env"
load_dotenv(dotenv_path)

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "liverlink")
PATIENT_ID = os.getenv("PATIENT_ID", "patient_john_doe")

if MONGODB_URI:
    mongo_client = MongoClient(MONGODB_URI)
    db = mongo_client[MONGODB_DB]
else:
    db = None

app = FastAPI(max_request_body_size=20 * 1024 * 1024)  # 20 MB

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def index():
    return (HERE.parent / "frontend" / "index.html").read_text(encoding="utf-8")

@app.get("/index.css")
async def get_css():
    return Response(
        content=(HERE.parent / "frontend" / "index.css").read_text(encoding="utf-8"),
        media_type="text/css"
    )

@app.get("/index.js")
async def get_js():
    return Response(
        content=(HERE.parent / "frontend" / "index.js").read_text(encoding="utf-8"),
        media_type="application/javascript"
    )

@app.get("/scanner", response_class=HTMLResponse)
async def scanner():
    return (HERE.parent / "frontend" / "upload.html").read_text(encoding="utf-8")

@app.get("/api/doctor/patient-profile")
async def get_doctor_patient_profile(patient_id: str = "John Doe"):
    query_id = "patient_john_doe" if patient_id == "John Doe" else "patient_sarah_connor"
    import sys
    sys.path.append(str(HERE / "agents"))
    from doctor_agent.tools import get_patient_comprehensive_profile
    profile = get_patient_comprehensive_profile(query_id)
    return JSONResponse(profile)

@app.get("/api/doctor/lab-records")
async def get_lab_records(patient_id: str = "patient_john_doe"):
    # Normalize ID to match standard patient identifier in MongoDB
    query_id = PATIENT_ID if patient_id == "John Doe" or patient_id == "patient_john_doe" else "patient_sarah_connor"
    
    if db is None:
        return JSONResponse([])
    
    cursor = db.lab_reports.find({"patient_id": query_id}).sort("timestamp", 1)
    records = []
    for doc in cursor:
        metadata = doc.get("report_metadata", {})
        results = doc.get("test_results", [])
        
        alt = 40
        ast = 35
        bili = 1.0
        albumin = 3.8
        inr = 1.0
        creatinine = 1.0
        sodium = 137.0
        
        for r in results:
            name_lower = r.get("name", "").lower()
            val = r.get("value")
            if val is not None:
                if "alt" in name_lower or "alanine" in name_lower:
                    alt = int(val)
                elif "ast" in name_lower or "aspartate" in name_lower:
                    ast = int(val)
                elif "bilirubin" in name_lower:
                    try:
                        bili = float(val)
                    except (ValueError, TypeError):
                        pass
                elif "albumin" in name_lower:
                    try:
                        albumin = float(val)
                    except (ValueError, TypeError):
                        pass
                elif "inr" in name_lower:
                    try:
                        inr = float(val)
                    except (ValueError, TypeError):
                        pass
                elif "creatinine" in name_lower:
                    try:
                        creatinine = float(val)
                    except (ValueError, TypeError):
                        pass
                elif "sodium" in name_lower:
                    try:
                        sodium = float(val)
                    except (ValueError, TypeError):
                        pass
                        
        date_str = metadata.get("report_date", "June 13")
        if "-" in date_str:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                date_str = dt.strftime("%b %d")
            except Exception:
                pass
                
        records.append({
            "date": date_str,
            "alt": alt,
            "ast": ast,
            "bilirubin": bili,
            "albumin": albumin,
            "inr": inr,
            "creatinine": creatinine,
            "sodium": sodium,
            "orderedBy": metadata.get("referring_physician", "Dr. Vance"),
            "status": "Completed"
        })
    return JSONResponse(records)

@app.get("/api/doctor/lab-orders")
async def get_lab_orders():
    if db is None:
        return JSONResponse([])
    
    # Find all "lab_ordered" events in health_logs
    cursor = db.health_logs.find({"event": "lab_ordered"}).sort("timestamp", 1)
    orders = []
    seen_ids = set()
    for doc in cursor:
        d = doc.get("data", {})
        order_id = d.get("order_id")
        if order_id not in seen_ids:
            seen_ids.add(order_id)
            orders.append({
                "id": order_id,
                "patient": d.get("patient_name"),
                "panel": d.get("requested_panel"),
                "date": doc.get("date"),
                "status": d.get("status", "Pending")
            })
            
    # Include default mock if empty
    if not orders:
        orders.append({
            "id": "ORD-9821",
            "patient": "John Doe",
            "panel": "Comprehensive Liver Function Panel",
            "date": "June 13, 2026",
            "status": "Pending"
        })
    return JSONResponse(orders)

@app.post("/api/doctor/lab-orders")
async def post_lab_order(request: Request):
    if db is None:
        return JSONResponse({"status": "error", "message": "MongoDB not connected"}, status_code=500)
    data = await request.json()
    patient_name = data.get("patient_name", "John Doe")
    patient_id = PATIENT_ID if patient_name == "John Doe" else "patient_sarah_connor"
    panel = data.get("panel")
    order_id = data.get("id")
    
    now = datetime.now(timezone.utc)
    db.health_logs.insert_one({
        "patient_id": patient_id,
        "event": "lab_ordered",
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now,
        "data": {
            "order_id": order_id,
            "patient_name": patient_name,
            "requested_panel": panel,
            "status": "Pending",
            "ordered_by": "Dr. Elizabeth Vance"
        }
    })
    return JSONResponse({"status": "success"})

@app.get("/api/doctor/morning-briefing")
async def get_morning_briefing():
    tavily_key = os.getenv("TAVILY_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    
    if not tavily_key:
        return JSONResponse({
            "summary": "Tavily API key is missing. Please add TAVILY_API_KEY to your .env file to enable live research searches.",
            "articles": []
        })

    # 1. Search Tavily for recent clinical developments
    try:
        tavily_client = TavilyClient(api_key=tavily_key)
        query = "recent AASLD guidelines clinical trials liver cirrhosis MASH developments 2026"
        resp = tavily_client.search(query=query, max_results=5)
        results = resp.get("results", [])
    except Exception as e:
        return JSONResponse({
            "summary": f"Failed to execute Tavily search: {str(e)}",
            "articles": []
        })

    articles = []
    for r in results:
        articles.append({
            "title": r.get("title", "Clinical Publication"),
            "snippet": r.get("snippet", ""),
            "url": r.get("url", "#")
        })

    # 2. Use Gemini to synthesize a concise professional summary
    if google_key and articles:
        try:
            genai_client = genai.Client(api_key=google_key)
            prompt = f"""
            You are a specialized clinical research summarizer for Hepatology.
            You are pre-summarizing the latest news and publications on liver disease for a busy liver specialist (Dr. Vance) this morning.
            Below is the raw search results fetched from Tavily:
            
            {json.dumps(articles, indent=2)}
            
            Please provide an extremely professional, concise clinical briefing (3-4 sentences maximum) highlighting the most important breakthrough or update. Focus on therapeutic changes, clinical trials, or guidelines. Speak in expert medical terminology. Do not include markdown headers or greetings.
            """
            gemini_resp = genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[types.Part.from_text(text=prompt)]
            )
            summary = gemini_resp.text.strip()
        except Exception as e:
            summary = "Failed to generate AI synthesis. Please review the live articles below."
    else:
        summary = "Live search results returned successfully. (Gemini AI synthesis unavailable)."

    return JSONResponse({
        "summary": summary,
        "articles": articles
    })

@app.get("/api/caregiver/alerts")
async def get_caregiver_alerts(patient_id: str = "patient_john_doe"):
    query_id = PATIENT_ID if patient_id == "John Doe" else "patient_sarah_connor"
    
    if db is None:
        return JSONResponse([])
    
    cursor = db.caregiver_alerts.find({"patient_id": query_id, "acknowledged": False}).sort("timestamp", -1)
    alerts = []
    for doc in cursor:
        ts = doc.get("timestamp")
        if isinstance(ts, datetime):
            ts_str = ts.strftime("%I:%M %p")
        else:
            ts_str = str(ts)[:5]
            
        severity = doc.get("severity", "info")
        if severity == "urgent":
            log_type = "alert"
        elif severity == "moderate":
            log_type = "info"
        else:
            log_type = "success"
            
        alerts.append({
            "timestamp": ts_str,
            "text": doc.get("message", ""),
            "type": log_type
        })
    return JSONResponse(alerts)

@app.post("/api/patient/symptoms")
async def post_symptoms(request: Request):
    if db is None:
        return JSONResponse({"status": "error", "message": "MongoDB not connected"}, status_code=500)
    data = await request.json()
    patient_name = data.get("patient_name", "John Doe")
    patient_id = PATIENT_ID if patient_name == "John Doe" else "patient_sarah_connor"
    fatigue = data.get("fatigue", "None")
    nausea = data.get("nausea", "None")
    jaundice = data.get("jaundice", "No")
    
    now = datetime.now(timezone.utc)
    
    # Save to health_logs
    db.health_logs.insert_one({
        "patient_id": patient_id,
        "event": "mood_and_symptoms",
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now,
        "data": {
            "fatigue_level_str": fatigue,
            "nausea_str": nausea,
            "jaundice_str": jaundice
        }
    })
    
    # Check if we need to raise caregiver alerts
    if jaundice == "Yes" or nausea == "Severe":
        db.caregiver_alerts.insert_one({
            "patient_id": patient_id,
            "severity": "urgent",
            "message": f"CRITICAL: {patient_name} reported severe symptoms (Fatigue: {fatigue}, Nausea: {nausea}, Jaundice: {jaundice}).",
            "acknowledged": False,
            "timestamp": now
        })
    elif fatigue in ("Moderate", "Severe") or nausea == "Moderate":
        db.caregiver_alerts.insert_one({
            "patient_id": patient_id,
            "severity": "moderate",
            "message": f"WARNING: {patient_name} is experiencing heightened symptoms (Fatigue: {fatigue}, Nausea: {nausea}).",
            "acknowledged": False,
            "timestamp": now
        })
        
    return JSONResponse({"status": "success"})

@app.post("/api/doctor/prescription")
async def post_prescription(request: Request):
    if db is None:
        return JSONResponse({"status": "error", "message": "MongoDB not connected"}, status_code=500)
    data = await request.json()
    patient_name = data.get("patient_name", "John Doe")
    patient_id = PATIENT_ID if patient_name == "John Doe" else "patient_sarah_connor"
    med = data.get("medication")
    freq = data.get("frequency")
    
    db.prescriptions.update_one(
        {"patient_id": patient_id},
        {"$set": {
            "medication": med,
            "frequency": freq,
            "timestamp": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    return JSONResponse({"status": "success"})

@app.get("/api/patient/prescription")
async def get_prescription(patient_id: str = "John Doe"):
    query_id = PATIENT_ID if patient_id == "John Doe" else "patient_sarah_connor"
    default_med = "Ursodiol 300mg" if patient_id == "John Doe" else "Obeticholic Acid 5mg"
    default_freq = "2 times daily (with breakfast & dinner)" if patient_id == "John Doe" else "Once daily in the morning"
    
    if db is None:
        return JSONResponse({"medication": default_med, "frequency": default_freq})
        
    doc = db.prescriptions.find_one({"patient_id": query_id})
    if doc:
        return JSONResponse({
            "medication": doc.get("medication"),
            "frequency": doc.get("frequency")
        })
    return JSONResponse({"medication": default_med, "frequency": default_freq})

@app.get("/api/patient/health-logs")
async def get_patient_health_logs(patient_id: str = "John Doe"):
    query_id = PATIENT_ID if patient_id == "John Doe" or patient_id == "patient_john_doe" else "patient_sarah_connor"
    
    if db is None:
        return JSONResponse([])
        
    cursor = db.health_logs.find({"patient_id": query_id}).sort("timestamp", -1)
    logs = []
    for doc in cursor:
        logs.append({
            "event": doc.get("event"),
            "date": doc.get("date"),
            "timestamp": doc.get("timestamp").isoformat() if isinstance(doc.get("timestamp"), datetime) else str(doc.get("timestamp")),
            "data": doc.get("data", {}),
            "flags": doc.get("flags", [])
        })
    return JSONResponse(logs)

@app.post("/api/patient/health-logs")
async def post_patient_health_log(request: Request):
    if db is None:
        return JSONResponse({"status": "error", "message": "MongoDB not connected"}, status_code=500)
    data = await request.json()
    patient_name = data.get("patient_name", "John Doe")
    patient_id = PATIENT_ID if patient_name == "John Doe" or patient_name == "patient_john_doe" else "patient_sarah_connor"
    event = data.get("event")
    log_data = data.get("data", {})
    flags = data.get("flags", [])
    
    now = datetime.now(timezone.utc)
    db.health_logs.insert_one({
        "patient_id": patient_id,
        "event": event,
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now,
        "data": log_data,
        "flags": flags
    })
    
    # Trigger moderate caregiver alert if ammonia status or exercise is anomalous (optional)
    if event == "ammonia_level" and log_data.get("status") == "elevated":
        db.caregiver_alerts.insert_one({
            "patient_id": patient_id,
            "severity": "moderate",
            "message": f"WARNING: {patient_name} ran a Hand AI Ammonia scan. Blood ammonia level is elevated at {log_data.get('ammonia_level_ppm')} ppm.",
            "acknowledged": False,
            "timestamp": now
        })
        
    return JSONResponse({"status": "success"})

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request):
    url = f"{ADK_BASE}/{path}"
    body = await request.body()
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.request(
            method=request.method,
            url=url,
            content=body,
            # Strip origin/referer so ADK's origin-check middleware lets it through
            headers={k: v for k, v in request.headers.items()
                     if k.lower() not in ("host", "origin", "referer")},
            params=dict(request.query_params),
        )
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info",
                http="h11", limit_max_requests=None,
                timeout_keep_alive=120)
