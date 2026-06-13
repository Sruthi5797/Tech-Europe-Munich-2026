# LiverLink — Chronic Liver Disease Support Platform

LiverLink is a unified, reactive healthcare platform connecting patients, caregivers, doctors, and diagnostic labs for proactive chronic liver disease (CLD) management. 

By linking real-time web dashboards with specialized AI agents (powered by Google ADK & Gemini 2.5), LiverLink breaks down communication silos and coordinates care proactively.

---

## 🏗️ Architecture Overview

The platform operates on a **Unified Origin Architecture** utilizing two primary servers:

```
                  ┌──────────────────────────────────────────┐
                  │          LiverLink User Interface        │
                  │   (Main Dashboard & Lab report Scanner)  │
                  └────────────────────┬─────────────────────┘
                                       │
                                       ▼ http://localhost:8080
                  ┌──────────────────────────────────────────┐
                  │       LiverLink Proxy/Web Server         │
                  │            (proxy_server.py)             │
                  └──────┬────────────────────────────┬──────┘
                         │                            │
      Direct API queries │                            │ Route /run & /apps
      to MongoDB Atlas   │                            │ (A2A Pipelines)
                         ▼                            ▼ http://localhost:8000
                  ┌──────────────┐             ┌─────────────────────────────┐
                  │  MongoDB     │             │     Google ADK Server       │
                  │  Database    │             │   (Central Orchestrator)    │
                  └──────────────┘             └─────────────────────────────┘
```

1. **Google ADK Agent Server** (Port `8000`): Runs the four specialized AI agents (Lila, Aria, Lab Agent, Hepatology Specialist Agent) and their custom tool registries.
2. **LiverLink Proxy/Web Server** (Port `8080`): Serves the unified frontend resources and proxies conversational/vision pipelines to the ADK agent endpoints (avoiding CORS and origin mismatches).

---

## 🚀 Step-by-Step Launch Guide

Follow these simple steps to run the complete, connected fullstack application:

### Prerequisites
Make sure you have your virtual environment configured and your `.env` file populated at the project root with the following keys:
* `GOOGLE_API_KEY` (Gemini model operations)
* `MONGODB_URI` (MongoDB Atlas connectivity)
* `MONGODB_DB` (defaults to `liverlink`)
* `TAVILY_API_KEY` (Web search capabilities for the clinician consultant)

---

### Step 1: Start the Google ADK Agent Server
This initializes the central orchestrator and registers the tools (e.g. database adapters, MELD-Na calculators, and web engines).

```bash
# Navigate to the agents workspace
cd backend/agents

# Launch the ADK server
../../.venv/bin/adk web
```
* **Developer Chat Playground**: Access the direct conversation interface at [http://127.0.0.1:8000/](http://127.0.0.1:8000/). Talk to Lila, Aria, or Dr. Vance directly to verify tools are binding correctly.

---

### Step 2: Start the LiverLink Proxy/Web Server
This serves the front-end pages and routes MongoDB updates and pipeline queries securely.

```bash
# In a new terminal window, navigate to the root directory
# Run the proxy server script
.venv/bin/python backend/proxy_server.py
```
* **Interactive Portal Dashboard**: Open your browser of choice to [http://127.0.0.1:8080/](http://127.0.0.1:8080/).

---

## 🎛️ Interaction Guide

Here is how to demonstrate and test the live fullstack capabilities:

### Mode A: AI-Powered Lab Report Scanner
* Navigate to `http://127.0.0.1:8080/scanner` (or click **AI Lab Scanner** in the website header).
* Upload or drag & drop one of the pre-built sample patient reports from the `data/test_data/` directories.
* Click **Analyse Report**.
* **What happens behind the scenes**:
  1. The **Lab Agent** extracts biomarkers and correlates with prior patient history in MongoDB to produce trend vectors.
  2. The **Hepatology Specialist Agent** ingests those trends, calculates scores (MELD-Na/Child-Pugh), determines the injury pattern, and produces a medical recommendation list.
  3. The structured responses are synchronized and dynamically drawn onto the dashboard.

### Mode B: Patient-to-Caregiver Communication (A2A Alert Sync)
1. Open the **Patient Portal** from the main dashboard view at [http://127.0.0.1:8080/](http://127.0.0.1:8080/).
2. Submit symptoms like **Jaundice** or severe nausea through the symptom logger.
3. Behind the scenes, the Patient Portal issues a secure request to MongoDB, creating critical warnings.
4. Open the **Caregiver Hub** from the selector. The live activity stream will automatically update with an alert generated directly by the underlying companion agent!

### Mode C: Doctor Treatment Adjustment
1. Enter the **Doctor Panel** dashboard.
2. Review the live biochemistry chart (drawn dynamically from patient records in your MongoDB).
3. Modify a treatment plan (e.g., prescribing *Obeticholic Acid*) and click **Update Prescription**.
4. The change is registered immediately. The next time the patient enters their portal, their checklist target is automatically recreated based on the real medical order.

---

## 🏗️ Project Structure

```
Tech-Europe-Munich-2026/
├── .env                            # Environment keys (Google Gemini, MongoDB, Tavily)
├── README.md                       # Comprehensive guide (this file)
├── frontend/                       # Interactive User Interfaces
│   ├── index.html                  # Stakeholder Dashboard
│   ├── index.css                   # Theme and component styles
│   ├── index.js                    # State synchronizer & Chart engine
│   └── upload.html                 # Vision-powered AI Scanner
├── backend/                        # Backend architecture
│   ├── requirements.txt            # Python dependencies
│   ├── proxy_server.py             # FastAPI Server & Proxy gateway
│   └── agents/                     # Google ADK agent configurations
│       ├── orchestrator/           # Central routing agent
│       ├── patient_agent/          # Daily companion (Lila)
│       ├── caregiver_agent/        # Supporter companion (Aria)
│       ├── lab_agent/              # Biochemical extractor
│       ├── doctor_agent/           # Hepatology clinical consultant
│       └── shared/                 # MongoDB database adapter
```

