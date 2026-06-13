# LiverLink

> AI-powered care coordination platform that connects labs, doctors, caregivers, and patients to detect deterioration early and prevent avoidable liver disease complications.

**Tech Europe Munich Hackathon 2026**

---

## The Problem

Liver disease is a silent killer. Patients deteriorate between appointments, labs go unreviewed, and caregivers are left disconnected from the clinical picture — until it's too late. Avoidable hospitalizations, delayed diagnosis, and fragmented communication are the norm.

## The Solution

LiverLink is an intelligent coordination layer that sits between all stakeholders in a liver patient's journey. Using AI agents powered by Google Gemini, it continuously monitors lab trends, surfaces early warning signals, coordinates care actions, and ensures nothing falls through the cracks.

## How It Works

```
Labs → Lab Analysis Agent → Patient Monitoring Agent → Alert Escalation Agent
                                      ↓
                           Care Coordination Agent
                                      ↓
              [Doctor] ←→ [Caregiver] ←→ [Patient]
```

1. **Lab results** arrive and are parsed for liver-specific biomarkers (ALT, AST, bilirubin, INR, albumin, MELD score)
2. **Patient Monitoring Agent** tracks trends over time and flags deterioration patterns
3. **Alert Escalation Agent** decides severity and routes alerts to the right stakeholder
4. **Care Coordination Agent** drafts action plans, follow-up tasks, and caregiver instructions

## Agents (Google ADK + Gemini)

| Agent | Status | Role |
|---|---|---|
| `patient_checkin` | ✅ Live | Daily check-in companion (Lila) for CLD patients |
| `lab-analysis` | 🔜 Planned | Parses lab reports, extracts biomarkers, flags anomalies |
| `patient-monitoring` | 🔜 Planned | Tracks longitudinal trends, computes risk scores |
| `alert-escalation` | 🔜 Planned | Determines severity, routes alerts to doctor / caregiver |
| `care-coordination` | 🔜 Planned | Generates care plans and patient-facing summaries |

---

## Patient Check-in Agent — Lila 💙

> "Good morning! It's so good to see you checking in today..."

**Lila** is a compassionate AI companion that conducts a structured daily health
check-in for patients living with Chronic Liver Disease. Every conversation covers:

| # | Check-in Topic | Why It Matters for CLD |
|---|---|---|
| 1 | 💊 **Medications** | Adherence is the cornerstone of liver disease management |
| 2 | 🌙 **Sleep quality** | CLD disrupts sleep; poor rest worsens inflammation |
| 3 | 🥚 **Protein intake** | Too little = muscle wasting; too much = HE risk |
| 4 | 💧 **Water consumption** | Hydration supports kidneys and prevents HRS |
| 5 | 🧂 **Salt / sodium** | Low-sodium diet is critical to managing ascites |
| 6 | 💙 **How you're feeling** | Catches mood, fatigue, and red-flag symptoms early |
| 7 | 🤲 **Hand AI test** *(optional)* | Screens for early hepatic encephalopathy via hand movement |

Lila uses **7 structured logging tools** to persist each data point, and flags
red-flag symptoms (confusion, jaundice, vomiting blood) for immediate escalation.

---

## Project Structure

```
Tech-Europe-Munich-2026/
├── .env.example                    # Environment variable template
├── .gitignore
├── README.md
├── frontend/                       # UI files (HTML, CSS, JS)
├── backend/                        # Python backend and ADK agents
│   ├── requirements.txt            # Python dependencies
│   ├── LiverLink/                  # Proxy server and Lab pipeline
│   └── agents/                     # ADK agent packages
│       └── patient_checkin/        # ADK agent package (run `adk web` from here)
│           ├── __init__.py         # Exports root_agent (required by ADK)
│           ├── agent.py            # Agent definition — model, tools, description
│           ├── prompts.py          # Full system instruction for Lila
│           └── tools.py            # 7 logging tools (medications, sleep, protein…)
├── data/                           # Datasets
```

---

## Tech Stack

- **AI / Agents**: [Google ADK](https://google.github.io/adk-docs/) + Gemini 2.0 Flash
- **Backend**: Python (FastAPI) *(coming soon)*
- **Data**: JSON structured logs → FHIR-compatible patient records
- **Alerts**: Webhook / push notification layer *(coming soon)*

---

## Getting Started

### 1. Clone & install

```bash
git clone https://github.com/your-org/liverlink
cd Tech-Europe-Munich-2026

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Set your API key

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY from https://aistudio.google.com/app/apikey
```

### 3. Run the Patient Check-in Agent

```bash
cd agents
adk web                          # Opens the ADK dev UI at http://localhost:8000
```

Or run from the terminal:

```bash
cd agents
adk run patient_checkin
```

---

## Team

Built at Tech Europe Munich Hackathon 2026.
