import os
import json
from pathlib import Path
from datetime import datetime, timezone
from pymongo import MongoClient
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
dotenv_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path)

# Initialize API clients
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "liverlink")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set in .env")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI is not set in .env")

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]

# Initialize Gemini Client
genai_client = genai.Client(api_key=GOOGLE_API_KEY)

TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "test_data"

def clean_json_text(text: str) -> str:
    """Strip code fences from LLM output."""
    cleaned = text.strip()
    for prefix in ("```json", "```"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    return cleaned.removesuffix("```").strip()

def process_patient_report(file_path: Path):
    print(f"Processing parsed report: {file_path.name}")
    try:
        raw_data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error reading JSON file {file_path}: {e}")
        return

    patient_id = raw_data.get("patient_id", file_path.parent.name)
    patient_name = raw_data.get("name", "Unknown Patient")

    # Generate the structured lab_agent report using Gemini 2.5 Flash
    prompt = f"""
You are the Lab Agent for LiverLink, an AI care coordination platform for Chronic Liver Disease.
Your task is to analyze the following raw parsed Liver Function Test (LFT) data and output a single JSON document conforming exactly to the required schema.

INPUT PARSED LAB DATA:
{json.dumps(raw_data, indent=2)}

REQUIRED OUTPUT SCHEMA:
{{
  "patient_id": "{patient_id}", 
  "agent": "lab_agent",
  "report_metadata": {{
    "patient_name": "{patient_name}",
    "date_of_birth": "<YYYY-MM-DD or as listed>",
    "age": <integer age or null>,
    "sex": "<Male or Female or Female/Male>",
    "report_date": "<YYYY-MM-DD or as listed>",
    "accession_number": "<e.g. ACC-XXXXX>",
    "referring_physician": "<physician name>",
    "lab_name": "<lab name>"
  }},
  "test_results": [
    {{
      "name": "<biomarker name, e.g. ALT (SGPT), AST (SGOT), ALP, Total Bilirubin, Direct Bilirubin, Albumin, Total Proteins, GGT, PT (Prothrombin Time), INR>",
      "value": <numeric value or null>,
      "unit": "<unit>",
      "reference_range": "<reference range>",
      "status": "<HIGH|LOW|NORMAL>",
      "is_flagged": <boolean>
    }}
  ],
  "trend_analysis": [],
  "is_anomaly_detected": <boolean>,
  "urgency_level": "<HIGH|MEDIUM|LOW>",
  "requires_immediate_attention": <boolean>,
  "notifications": {{
    "new_report_alert": true,
    "notify_doctor": <boolean>,
    "notify_patient": <boolean>,
    "alert_message": "<one-line alert message, e.g. 'CRITICAL: Urgent liver marker elevation detected for Tuan Nguyen.'>"
  }},
  "doctor_brief": "<2-3 sentence clinical narrative for the physician>",
  "patient_summary": "<2-3 sentence plain-English summary for the patient/caregiver>"
}}

RULES FOR STATUS, URGENCY & SEVERITY (from our guidelines):
- ALT Normal range: 7-56 U/L. Status is HIGH if > 56. Urgency is HIGH if ALT > 112. Requires immediate attention if ALT > 168.
- AST Normal range: 10-40 U/L. Status is HIGH if > 40. Urgency is HIGH if AST > 80. Requires immediate attention if AST > 120.
- ALP Normal range: 44-147 U/L. Status is HIGH if > 147. Urgency is HIGH if ALP > 294.
- Total Bilirubin Normal range: 0.1-1.2 mg/dL. Status is HIGH if > 1.2. Urgency is HIGH if > 1.2. Requires immediate attention if > 3.0.
- Direct Bilirubin Normal range: 0.0-0.3 mg/dL. Status is HIGH if > 0.3.
- Albumin Normal range: 3.5-5.0 g/dL. Status is LOW if < 3.5. Urgency is HIGH if Albumin < 3.5. Requires immediate attention if Albumin < 2.5.
- GGT Normal range: 8-61 U/L. Status is HIGH if > 61. Urgency is HIGH if GGT > 183.
- PT Normal range: 11.0-13.5 seconds. Status is HIGH if > 13.5. Urgency is HIGH if PT > 13.5.
- INR Normal range: 0.8-1.2. Status is HIGH if > 1.2. Urgency is HIGH if INR > 1.2. Requires immediate attention if INR > 1.5.

**Urgency Level Classification:**
- HIGH: if any HIGH urgency criteria is met.
- MEDIUM: if any value is outside the reference range but not meeting HIGH criteria.
- LOW: if all values are within reference ranges.

**Requires Immediate Attention:**
- True if any ALT > 168, AST > 120, Total Bilirubin > 3.0, INR > 1.5, or Albumin < 2.5.

**Notifications:**
- notify_doctor: True if urgency_level is HIGH or MEDIUM, else False.
- notify_patient: True if urgency_level is HIGH, else False.
- alert_message: Standard high-urgency/medium-urgency alert or normal check-in alert.

**Summaries:**
- doctor_brief: Professional, medical language summarizing the elevated/reduced values and potential clinical implications.
- patient_summary: Warm, empathetic, plain-English summary avoiding medical jargon. Ends with a reassuring/actionable step.

Output ONLY valid JSON — no markdown, no explanation, no code fences.
"""

    response = genai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Part.from_text(text=prompt)]
    )

    try:
        report_json = json.loads(clean_json_text(response.text))
    except Exception as e:
        print(f"Failed to parse Gemini response as JSON for {patient_id}: {e}")
        print("Response text was:")
        print(response.text)
        return

    # Add timestamp field for MongoDB sorting
    report_json["timestamp"] = datetime.now(timezone.utc).isoformat()

    # 1. Insert into lab_reports collection
    try:
        res = db.lab_reports.insert_one(report_json)
        print(f"  Saved to lab_reports collection (ID: {res.inserted_id})")
    except Exception as e:
        print(f"  Error inserting into lab_reports: {e}")

    # 2. Insert into health_logs collection as a lab_report event
    try:
        health_log_entry = {
            "patient_id": patient_id,
            "event": "lab_report",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "timestamp": datetime.now(timezone.utc),
            "data": report_json,
            "flags": ["anomaly"] if report_json.get("is_anomaly_detected") else [],
        }
        res_hl = db.health_logs.insert_one(health_log_entry)
        print(f"  Saved to health_logs collection as event 'lab_report' (ID: {res_hl.inserted_id})")
    except Exception as e:
        print(f"  Error inserting into health_logs: {e}")

    print(f"Successfully processed patient {patient_id} ({patient_name})\n")


def _parse_args(args: list[str]) -> tuple[str, list[str]]:
    """Return (model, patient_ids)."""
    model = "gliner2"  # Default to pioneer parser output model
    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            model = args[idx + 1]

    target_ids = [
        a for a in args
        if not a.startswith("--") and a not in (model,)
    ]
    return model, target_ids


def main():
    import sys
    model, target_ids = _parse_args(sys.argv[1:])
    print(f"Starting MongoDB populator for parsed LFT reports using model '{model}'...\n")

    if target_ids:
        parsed_files = []
        for pid in target_ids:
            found = list(TEST_DATA_DIR.glob(f"**/{pid}_parsed_{model}.json"))
            if found:
                parsed_files.extend(found)
            else:
                print(f"WARNING: No parsed report found for patient {pid} using model {model}")
    else:
        # Search for all *_parsed_{model}.json files
        parsed_files = sorted(TEST_DATA_DIR.glob(f"**/PT-2026-*_parsed_{model}.json"))
    
    if not parsed_files:
        print(f"No parsed patient reports found with pattern *_parsed_{model}.json. Please run pioneer_lab_parser.py first.")
        return

    print(f"Found {len(parsed_files)} parsed patient report(s) for model '{model}'.")
    
    for file_path in parsed_files:
        process_patient_report(file_path)

    print(f"All patient records for model '{model}' successfully processed and loaded into MongoDB.")


if __name__ == "__main__":
    main()
    main()
