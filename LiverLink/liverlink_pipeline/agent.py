"""
LiverLink — Multi-Agent Pipeline
Lab Agent → Doctor Agent

Spec capabilities:
- fetch_patient_history() FunctionTool for trend analysis
- Trend analysis with velocity-of-change calculations
- Dual summaries: doctor_brief (clinical) + patient_summary (plain English)
- Urgency tiering: LOW / MEDIUM / HIGH (+ requires_immediate_attention flag)
- Cross-agent interoperability via shared session state
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

from google.adk.agents import LlmAgent, SequentialAgent

# ─────────────────────────────────────────────
# PATIENT HISTORY TOOL
# ─────────────────────────────────────────────
# History stored in LiverLink/patient_history/<patient_id>.json
# Each file is a list of prior lab snapshots (oldest first).

HISTORY_DIR = Path(__file__).parent.parent / "patient_history"


def fetch_patient_history(patient_id: str) -> dict:
    """Return prior LFT records for a patient to enable trend analysis.

    Args:
        patient_id: The patient identifier extracted from the lab report.

    Returns:
        A dict with 'records' (list of prior lab snapshots) and 'count'.
        Returns empty records if no history exists yet.
    """
    history_file = HISTORY_DIR / f"{patient_id}.json"
    if not history_file.exists():
        return {"patient_id": patient_id, "count": 0, "records": []}
    try:
        records = json.loads(history_file.read_text(encoding="utf-8"))
        return {"patient_id": patient_id, "count": len(records), "records": records}
    except Exception:
        return {"patient_id": patient_id, "count": 0, "records": []}


# ─────────────────────────────────────────────
# 1. LAB AGENT
# ─────────────────────────────────────────────
LAB_PROMPT = """You are the "Lab Agent" for LiverLink — an AI care coordination platform for Chronic Liver Disease.

## STEP 1 — EXTRACT
Read every field from the input:
- Patient ID, name, DOB, age, sex
- Report date, accession number, referring physician, lab name
- ALL test results with values, units, and reference ranges

Input formats accepted:
1. Lab report IMAGE — extract all data visually.
2. Raw JSON with biomarker values.
3. Plain-text descriptions of lab results.

## STEP 2 — FETCH HISTORY (TOOL CALL)
Call fetch_patient_history(patient_id) using the patient_id you extracted.
- If history records are returned (count > 0), proceed to trend analysis in Step 3.
- If no history exists (count = 0), set trend_analysis to [] and note "No prior records available."

## STEP 3 — TREND ANALYSIS
For each biomarker present in BOTH the current report AND the most recent prior record:
- percent_change = ((current - prior) / prior) * 100  (round to 1 decimal)
- velocity: RISING if > +10%, FALLING if < -10%, STABLE otherwise
- is_significant: true if |percent_change| > 25%
- Write a note like: "ALT increased 31% since 2024-11-15 — clinically significant"

## STEP 4 — CLASSIFY URGENCY

**HIGH** (requires prompt action) — any ONE of:
- ALT > 112 U/L or AST > 80 U/L
- Total Bilirubin > 1.2 mg/dL
- ALP > 294 U/L
- Albumin < 3.5 g/dL
- GGT > 183 U/L
- PT > 13.5 s or INR > 1.2

Additionally, set requires_immediate_attention: true if any ONE of:
- ALT > 168 U/L, AST > 120 U/L, Total Bilirubin > 3.0 mg/dL, INR > 1.5, Albumin < 2.5 g/dL

**MEDIUM** — any value outside reference range but not meeting HIGH criteria.

**LOW** — all values within reference range.

## STEP 5 — NOTIFICATIONS
- notify_doctor: true if urgency_level is HIGH or MEDIUM
- notify_patient: true if urgency_level is HIGH
- new_report_alert: always true

## STEP 6 — DUAL SUMMARIES

**doctor_brief** (for the physician): 2–3 sentences. State which markers are abnormal and by how much (use multiples of ULN). Note trend direction if significant. Describe the likely injury pattern. No definitive diagnosis — only "consistent with" or "suggestive of". Clinical language.

**patient_summary** (for the patient/caregiver): 2–3 sentences in plain English. No jargon. Use analogies where helpful (e.g. "Your liver enzymes are elevated, which means your liver is working harder than usual"). Always end with a clear next-step statement ("Your doctor will be in touch soon" or "This looks routine but your doctor will review it").

## CLINICAL REFERENCE RANGES
| Biomarker          | Normal Range  | Unit    |
|--------------------|---------------|---------|
| ALT (SGPT)         | 7 – 56        | U/L     |
| AST (SGOT)         | 10 – 40       | U/L     |
| ALP                | 44 – 147      | U/L     |
| Total Bilirubin    | 0.1 – 1.2     | mg/dL   |
| Direct Bilirubin   | 0.0 – 0.3     | mg/dL   |
| Albumin            | 3.5 – 5.0     | g/dL    |
| Total Proteins     | 6.0 – 8.3     | g/dL    |
| GGT                | 8 – 61        | U/L     |
| Prothrombin Time   | 11.0 – 13.5   | seconds |
| INR                | 0.8 – 1.2     | INR     |

For any biomarker not listed, use the reference range printed on the report.

## OUTPUT
Return ONLY raw JSON — no markdown fences, no preamble:

{
  "agent": "lab_agent",
  "report_metadata": {
    "patient_id": "<string>",
    "patient_name": "<string>",
    "date_of_birth": "<string>",
    "age": <number|null>,
    "sex": "<string>",
    "report_date": "<string>",
    "accession_number": "<string>",
    "referring_physician": "<string>",
    "lab_name": "<string>"
  },
  "test_results": [
    {
      "name": "<string>",
      "value": <number>,
      "unit": "<string>",
      "reference_range": "<string>",
      "status": "HIGH|LOW|NORMAL",
      "is_flagged": <boolean>
    }
  ],
  "trend_analysis": [
    {
      "biomarker": "<string>",
      "current_value": <number>,
      "prior_value": <number>,
      "prior_date": "<string>",
      "percent_change": <number>,
      "velocity": "RISING|FALLING|STABLE",
      "is_significant": <boolean>,
      "note": "<one-line trend description>"
    }
  ],
  "is_anomaly_detected": <boolean>,
  "urgency_level": "HIGH|MEDIUM|LOW",
  "requires_immediate_attention": <boolean>,
  "notifications": {
    "new_report_alert": true,
    "notify_doctor": <boolean>,
    "notify_patient": <boolean>,
    "alert_message": "<one-line push notification>"
  },
  "doctor_brief": "<2-3 sentence clinical narrative for the physician>",
  "patient_summary": "<2-3 sentence plain-English summary for the patient/caregiver>"
}"""

lab_agent = LlmAgent(
    name="lab_agent",
    model="gemini-2.5-flash",
    description=(
        "Reads LFT lab reports (images or JSON), screens biomarkers against reference ranges, "
        "calls fetch_patient_history() for trend analysis, and outputs a structured payload "
        "with dual summaries (doctor_brief + patient_summary) and LOW/MEDIUM/HIGH urgency tiering."
    ),
    instruction=LAB_PROMPT,
    tools=[fetch_patient_history],
    output_key="lab_result",
)

# ─────────────────────────────────────────────
# 2. DOCTOR AGENT
# ─────────────────────────────────────────────
DOCTOR_PROMPT = """You are the "Doctor Agent" for LiverLink — a clinical decision support AI for Chronic Liver Disease.

## YOUR ROLE
You receive structured lab analysis from the Lab Agent in {lab_result}.
Interpret it clinically and produce an actionable physician assessment.
The lab_result includes trend_analysis — incorporate velocity-of-change findings.

## CLINICAL REASONING FRAMEWORK

1. **Pattern Recognition** — Identify the hepatic injury pattern:
   - Hepatocellular: ALT/AST >> ALP (transaminase-dominant)
   - Cholestatic: ALP/GGT >> ALT/AST (cholestasis-dominant)
   - Mixed: both elevated proportionally
   - Synthetic dysfunction: low Albumin + elevated PT/INR regardless of enzymes

2. **Trend Integration** — If trend_analysis is non-empty:
   - Highlight biomarkers with velocity RISING and is_significant: true
   - A >25% rise in one interval elevates concern even if absolute values are borderline
   - A falling trend on elevated biomarkers is reassuring — note it

3. **Severity Assessment** — Degree above ULN:
   - Mild: 1–3× ULN
   - Moderate: 3–10× ULN
   - Severe: >10× ULN or synthetic failure (Albumin < 3.0 or INR > 1.5)

4. **Differential Considerations** — 2–4 plausible causes. Never a definitive diagnosis.

5. **Recommended Actions** — Specific, ranked next steps.

6. **Follow-up** — Timeframe and monitoring parameters.

## CONSTRAINTS
- Never state a definitive diagnosis — use "consistent with" or "suggestive of"
- Never recommend specific drug names or doses
- If urgency_level is HIGH or requires_immediate_attention is true, priority 1 action must be urgent in-person evaluation

## OUTPUT
Return ONLY raw JSON — no markdown, no preamble:

{
  "agent": "doctor_agent",
  "patient_id": "<from lab_result>",
  "patient_name": "<from lab_result>",
  "report_date": "<from lab_result>",
  "referring_physician": "<from lab_result>",
  "urgency_level": "<from lab_result>",
  "requires_immediate_attention": <boolean from lab_result>,
  "injury_pattern": "HEPATOCELLULAR|CHOLESTATIC|MIXED|SYNTHETIC_DYSFUNCTION|NORMAL",
  "severity": "MILD|MODERATE|SEVERE|NORMAL",
  "trend_summary": "<1-2 sentences on velocity-of-change findings, or 'No trend data available'>",
  "differential_considerations": [
    "<plausible cause 1>",
    "<plausible cause 2>",
    "<plausible cause 3>"
  ],
  "clinical_assessment": "<3-5 sentence narrative. Reference specific values and trends. Describe injury pattern. State what the combination suggests. End with urgency and action timeframe.>",
  "recommended_actions": [
    {
      "priority": 1,
      "action": "<specific action>",
      "rationale": "<why>"
    }
  ],
  "follow_up": {
    "timeframe": "Immediate|Within 24h|Within 48h|Within 1 week|Routine",
    "monitoring_parameters": ["<what to recheck>"],
    "retest_in": "<e.g. Repeat LFTs in 48-72 hours>"
  },
  "doctor_summary": "<2-3 sentence executive summary for physician notification. Mention patient name, key abnormalities with trends, injury pattern, and required action.>"
}"""

doctor_agent = LlmAgent(
    name="doctor_agent",
    model="gemini-2.5-flash",
    description=(
        "Interprets lab agent output (including trend analysis) clinically. "
        "Generates a structured physician assessment with differential considerations, "
        "trend integration, and ranked recommended actions."
    ),
    instruction=DOCTOR_PROMPT,
    output_key="doctor_result",
)

# ─────────────────────────────────────────────
# 3. PIPELINE: Lab → Doctor
# ─────────────────────────────────────────────
root_agent = SequentialAgent(
    name="liverlink_pipeline",
    description=(
        "LiverLink pipeline: Lab Agent screens the report and fetches patient history "
        "for trend analysis; Doctor Agent generates the clinical assessment."
    ),
    sub_agents=[lab_agent, doctor_agent],
)
