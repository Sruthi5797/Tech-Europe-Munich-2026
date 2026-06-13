"""
Tool functions for the LiverLink Caregiver Agent.

All patient data is read from MongoDB (health_logs collection).
Caregiver alerts written by the patient agent are read from caregiver_alerts.
This is the A2A communication channel — no direct agent-to-agent call needed.
"""

from datetime import datetime, timezone, timedelta
import json

from shared.db import get_db, PATIENT_ID


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _date_range(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _get_events_for_date(date_str: str) -> list:
    """Return all health_log entries for a patient on a given date."""
    try:
        return list(
            get_db().health_logs.find(
                {"patient_id": PATIENT_ID, "date": date_str},
                {"_id": 0},
            )
        )
    except Exception as e:
        print(f"[DB READ ERROR] {e}")
        return []


def _get_events_since(days: int, event: str = None) -> list:
    """Return health_log entries for the last N days, optionally filtered by event type."""
    query = {
        "patient_id": PATIENT_ID,
        "timestamp": {"$gte": _date_range(days)},
    }
    if event:
        query["event"] = event
    try:
        return list(get_db().health_logs.find(query, {"_id": 0}).sort("timestamp", -1))
    except Exception as e:
        print(f"[DB READ ERROR] {e}")
        return []


# ──────────────────────────────────────────────────────────────────────────────
#  Patient Daily Summary
# ──────────────────────────────────────────────────────────────────────────────

def get_patient_daily_summary(date: str = "today") -> dict:
    """
    Retrieve the patient's daily check-in summary from MongoDB.

    Args:
        date: Date in YYYY-MM-DD format, or "today" / "yesterday".

    Returns:
        A structured summary of all check-in data logged for that day.
    """
    if date in ("today", ""):
        resolved_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    elif date == "yesterday":
        resolved_date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        resolved_date = date

    events = _get_events_for_date(resolved_date)

    if not events:
        return {
            "status": "no_data",
            "date": resolved_date,
            "message": f"No check-in data found for {resolved_date}. John may not have completed a check-in yet.",
        }

    # Index events by type for easy lookup
    by_event = {}
    for e in events:
        by_event.setdefault(e["event"], []).append(e["data"])

    def latest(event_type):
        return by_event.get(event_type, [{}])[-1]

    # Collect all flags across the day
    all_flags = [f for e in events for f in e.get("flags", [])]

    summary = {
        "timestamp": _now(),
        "date": resolved_date,
        "patient_name": "John Doe",
        "check_in_completed": len(events) > 0,
        "medications": latest("medication_adherence"),
        "sleep": latest("sleep_quality"),
        "nutrition": {
            "protein": latest("protein_intake"),
            "hydration": latest("water_intake"),
            "sodium": latest("salt_intake"),
            "appetite": latest("appetite"),
        },
        "activity": latest("activity_level"),
        "weight": latest("weight"),
        "fatigue": latest("fatigue"),
        "mood": latest("mood_and_symptoms"),
        "hand_ai_test": latest("hand_ai_test_initiated"),
        "flags": all_flags,
    }

    print(f"[LIVERLINK LOG] Daily summary retrieved for {resolved_date} ({len(events)} events)")
    return {"status": "success", "data": summary}


# ──────────────────────────────────────────────────────────────────────────────
#  Health Trend Report  (flags unusual patterns)
# ──────────────────────────────────────────────────────────────────────────────

def get_health_trend_report(days: int = 7) -> dict:
    """
    Analyse real health data from MongoDB over the last N days and flag unusual patterns.

    Tracks: medication adherence, activity level, weight changes, fatigue, appetite.

    Args:
        days: Number of days to include (7, 14, or 30).

    Returns:
        A trend report with computed averages, pattern flags, and recommendations.
    """
    cutoff = _date_range(days)

    def fetch(event):
        return _get_events_since(days, event)

    meds       = fetch("medication_adherence")
    sleep_logs = fetch("sleep_quality")
    fatigue    = fetch("fatigue")
    appetite   = fetch("appetite")
    activity   = fetch("activity_level")
    weight     = fetch("weight")
    mood       = fetch("mood_and_symptoms")

    # ── Medication adherence ──────────────────────────────────────────────────
    missed_days = sum(1 for e in meds if not e["data"].get("medications_taken", True))
    adherence_pct = round(((len(meds) - missed_days) / len(meds)) * 100) if meds else None

    # ── Fatigue ───────────────────────────────────────────────────────────────
    fatigue_levels = [e["data"].get("fatigue_level", 5) for e in fatigue]
    avg_fatigue    = round(sum(fatigue_levels) / len(fatigue_levels), 1) if fatigue_levels else None
    high_fatigue_days = sum(1 for f in fatigue_levels if f >= 8)

    # ── Appetite ──────────────────────────────────────────────────────────────
    appetite_levels  = [e["data"].get("appetite_level", 5) for e in appetite]
    avg_appetite     = round(sum(appetite_levels) / len(appetite_levels), 1) if appetite_levels else None
    low_appetite_days = sum(1 for a in appetite_levels if a <= 3)

    # ── Activity ──────────────────────────────────────────────────────────────
    inactive_days = sum(
        1 for e in activity
        if e["data"].get("activity_type", "none") == "none"
        or (e["data"].get("steps", 0) == 0 and e["data"].get("duration_minutes", 0) == 0)
    )

    # ── Weight ────────────────────────────────────────────────────────────────
    weights = sorted(
        [(e["timestamp"], e["data"].get("weight_kg")) for e in weight if e["data"].get("weight_kg")],
        key=lambda x: x[0],
    )
    weight_delta = None
    if len(weights) >= 2:
        weight_delta = round(weights[-1][1] - weights[0][1], 2)

    # ── Sleep ─────────────────────────────────────────────────────────────────
    sleep_hours  = [e["data"].get("hours_slept", 7) for e in sleep_logs]
    avg_sleep    = round(sum(sleep_hours) / len(sleep_hours), 1) if sleep_hours else None

    # ── Pattern flags ─────────────────────────────────────────────────────────
    pattern_flags = []

    if adherence_pct is not None and adherence_pct < 80:
        pattern_flags.append({
            "type": "LOW_MEDICATION_ADHERENCE",
            "severity": "moderate",
            "message": f"Medication adherence dropped to {adherence_pct}% over the last {days} days.",
        })

    if high_fatigue_days >= 3:
        pattern_flags.append({
            "type": "PERSISTENT_HIGH_FATIGUE",
            "severity": "moderate",
            "message": f"High fatigue (8+/10) reported on {high_fatigue_days} of the last {days} days.",
        })

    if low_appetite_days >= 3:
        pattern_flags.append({
            "type": "PERSISTENT_LOW_APPETITE",
            "severity": "moderate",
            "message": f"Very low appetite (3 or below) on {low_appetite_days} of the last {days} days. Nutritional risk.",
        })

    if inactive_days >= 3:
        pattern_flags.append({
            "type": "EXTENDED_INACTIVITY",
            "severity": "mild",
            "message": f"No physical activity logged on {inactive_days} of the last {days} days.",
        })

    if weight_delta is not None and weight_delta >= 2.0:
        pattern_flags.append({
            "type": "WEIGHT_GAIN_TREND",
            "severity": "moderate",
            "message": f"John has gained {weight_delta} kg over the last {days} days. Monitor for fluid retention.",
        })

    if weight_delta is not None and weight_delta <= -3.0:
        pattern_flags.append({
            "type": "WEIGHT_LOSS_TREND",
            "severity": "moderate",
            "message": f"John has lost {abs(weight_delta)} kg over the last {days} days. Monitor for muscle wasting.",
        })

    report = {
        "timestamp": _now(),
        "period_days": days,
        "patient_name": "John Doe",
        "data_points": len(meds) + len(fatigue) + len(appetite) + len(activity) + len(weight),
        "trends": {
            "medication_adherence": {
                "check_in_days": len(meds),
                "missed_days": missed_days,
                "adherence_rate_percent": adherence_pct,
            },
            "fatigue": {
                "readings": len(fatigue_levels),
                "avg_fatigue_level": avg_fatigue,
                "high_fatigue_days": high_fatigue_days,
            },
            "appetite": {
                "readings": len(appetite_levels),
                "avg_appetite_level": avg_appetite,
                "low_appetite_days": low_appetite_days,
            },
            "activity": {
                "total_logged_days": len(activity),
                "inactive_days": inactive_days,
            },
            "weight": {
                "readings": len(weights),
                "first_kg": weights[0][1] if weights else None,
                "latest_kg": weights[-1][1] if weights else None,
                "change_kg": weight_delta,
            },
            "sleep": {
                "readings": len(sleep_logs),
                "avg_hours": avg_sleep,
            },
        },
        "pattern_flags": pattern_flags,
    }

    print(f"[LIVERLINK LOG] Trend report generated for last {days} days — {len(pattern_flags)} pattern flags")
    return {"status": "success", "data": report}


# ──────────────────────────────────────────────────────────────────────────────
#  Pending Alerts  (A2A inbox for the caregiver)
# ──────────────────────────────────────────────────────────────────────────────

def get_pending_alerts() -> dict:
    """
    Fetch all unacknowledged alerts sent by the patient agent.

    This is the caregiver's A2A inbox — alerts are written here automatically
    when the patient agent detects a clinical threshold crossing during check-in.

    Returns:
        List of pending alerts ordered by severity then timestamp.
    """
    try:
        raw = list(
            get_db().caregiver_alerts.find(
                {"patient_id": PATIENT_ID, "acknowledged": False},
                {"_id": 0},
                sort=[("timestamp", -1)],
            )
        )
    except Exception as e:
        return {"status": "error", "message": str(e), "alerts": []}

    # Serialise datetime objects for JSON output
    alerts = []
    for a in raw:
        a["timestamp"] = a["timestamp"].isoformat() if hasattr(a["timestamp"], "isoformat") else str(a["timestamp"])
        alerts.append(a)

    # Sort: urgent first, then moderate, then mild
    order = {"urgent": 0, "moderate": 1, "mild": 2}
    alerts.sort(key=lambda x: order.get(x.get("severity", "mild"), 3))

    print(f"[LIVERLINK LOG] Fetched {len(alerts)} pending caregiver alerts")
    return {
        "status": "success",
        "count": len(alerts),
        "alerts": alerts,
        "message": (
            f"John's patient agent sent {len(alerts)} unacknowledged alert(s)."
            if alerts else
            "No pending alerts from John's check-in agent."
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Acknowledge Alert
# ──────────────────────────────────────────────────────────────────────────────

def acknowledge_patient_alert(alert_id: str, action_taken: str, resolved: bool = False) -> dict:
    """
    Acknowledge a patient alert and log the caregiver's response in MongoDB.

    Args:
        alert_id: The alert_id to acknowledge.
        action_taken: What the caregiver did in response.
        resolved: True if the issue is fully resolved, False if still monitoring.

    Returns:
        Confirmation of acknowledgement.
    """
    try:
        get_db().caregiver_alerts.update_one(
            {"alert_id": alert_id, "patient_id": PATIENT_ID},
            {"$set": {
                "acknowledged": True,
                "acknowledged_at": datetime.now(timezone.utc),
                "action_taken": action_taken,
                "resolved": resolved,
            }},
        )
    except Exception as e:
        print(f"[DB WRITE ERROR] {e}")

    record = {
        "timestamp": _now(),
        "alert_id": alert_id,
        "action_taken": action_taken,
        "resolved": resolved,
        "status": "resolved" if resolved else "monitoring",
    }
    print(f"[LIVERLINK LOG] Alert acknowledged: {record}")
    return {
        "status": "acknowledged",
        "message": (
            "Alert marked as resolved. 💙"
            if resolved else
            "Alert acknowledged and logged. The care team can see your response."
        ),
        "data": record,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Log Caregiver Observation
# ──────────────────────────────────────────────────────────────────────────────

def log_caregiver_observation(
    observation: str,
    severity: str,
    symptoms_observed: list[str] = [],
    action_taken: str = "",
) -> dict:
    """
    Log an observation made by the caregiver about the patient.

    Args:
        observation: Free-text description of what the caregiver observed.
        severity: One of "routine", "mild_concern", "moderate_concern", "urgent".
        symptoms_observed: Specific symptoms the caregiver noticed.
        action_taken: Any action the caregiver already took.

    Returns:
        Confirmation with observation ID.
    """
    obs_id = f"obs_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    record = {
        "timestamp": _now(),
        "observation_id": obs_id,
        "patient_id": PATIENT_ID,
        "logged_by": "caregiver",
        "observation": observation,
        "severity": severity,
        "symptoms_observed": symptoms_observed,
        "action_taken": action_taken,
    }

    try:
        get_db().caregiver_observations.insert_one({**record})
    except Exception as e:
        print(f"[DB WRITE ERROR] {e}")

    print(f"[LIVERLINK LOG] Caregiver observation logged: {obs_id}")
    return {
        "status": "logged",
        "observation_id": obs_id,
        "message": "Your observation has been recorded and shared with the care team.",
        "data": record,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Escalation to Care Team
# ──────────────────────────────────────────────────────────────────────────────

def send_escalation_to_care_team(
    reason: str,
    urgency: str,
    symptoms: list[str] = [],
    caregiver_message: str = "",
) -> dict:
    """
    Send an escalation alert to the patient's care team.

    Args:
        reason: Clinical reason (e.g. "possible hepatic encephalopathy").
        urgency: One of "routine", "soon", "urgent", "emergency".
        symptoms: Symptoms prompting escalation.
        caregiver_message: Optional message from the caregiver.

    Returns:
        Escalation confirmation with ticket ID and next steps.
    """
    ticket_id = f"esc_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    next_steps = {
        "routine":   "The care team will review this at the next scheduled appointment.",
        "soon":      "The care team has been notified and will contact you within 24 hours.",
        "urgent":    "The care team has been alerted and will call you today.",
        "emergency": "Please call 999 / 112 immediately.",
    }.get(urgency, "The care team has been notified.")

    record = {
        "timestamp": _now(),
        "ticket_id": ticket_id,
        "patient_id": PATIENT_ID,
        "reason": reason,
        "urgency": urgency,
        "symptoms": symptoms,
        "caregiver_message": caregiver_message,
        "notified_team": ["Dr. Smith", "Liver Nurse Specialist"],
        "status": "sent",
    }

    try:
        get_db().escalations.insert_one({**record})
    except Exception as e:
        print(f"[DB WRITE ERROR] {e}")

    print(f"[LIVERLINK LOG] Escalation sent: {ticket_id} ({urgency})")
    return {
        "status": "escalated",
        "ticket_id": ticket_id,
        "next_steps": next_steps,
        "data": record,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  CLD Care Guidance
# ──────────────────────────────────────────────────────────────────────────────

def get_cld_care_tip(topic: str) -> dict:
    """
    Retrieve practical CLD-specific care guidance for the caregiver.

    Args:
        topic: Care topic — e.g. "sodium", "fatigue", "encephalopathy",
               "medications", "burnout", "doctor", "appetite", "activity".

    Returns:
        Structured guidance with key points and warning signs.
    """
    topic_lower = topic.lower()

    guidance_library = {
        "sodium": {
            "title": "Low-Sodium Cooking & Meal Management",
            "key_points": [
                "Target < 2g sodium/day (approx 5g table salt) to reduce fluid retention.",
                "Avoid processed foods, canned soups, and ready meals — hidden sodium sources.",
                "Use herbs, lemon, garlic, and spices for flavour instead of salt.",
                "Choose fresh or frozen vegetables over tinned ones.",
            ],
            "warning_signs": ["Sudden swelling in ankles or abdomen may indicate too much sodium."],
        },
        "encephalopathy": {
            "title": "Recognising Hepatic Encephalopathy (HE)",
            "key_points": [
                "HE happens when the liver can't remove toxins, affecting brain function.",
                "Early signs: forgetfulness, slower thinking, personality changes, sleep reversal.",
                "Later signs: confusion, disorientation, tremors, slurred speech.",
                "Triggers: constipation, infections, dehydration, missed medications.",
            ],
            "warning_signs": [
                "Any confusion or unusual behaviour → call the care team same day.",
                "Severe confusion or unresponsiveness → call 999/112 immediately.",
            ],
        },
        "fatigue": {
            "title": "Managing Fatigue in CLD",
            "key_points": [
                "Fatigue is one of the most common CLD symptoms — it is real and valid.",
                "Encourage short rest periods (20-30 min) rather than long daytime naps.",
                "Light activity like gentle walks can actually help energy levels.",
                "Ensure adequate protein intake — muscle wasting worsens fatigue.",
            ],
            "warning_signs": ["Sudden severe worsening of fatigue may signal decompensation."],
        },
        "appetite": {
            "title": "Supporting Appetite and Nutrition",
            "key_points": [
                "Small, frequent meals (5-6 per day) are easier to tolerate than large ones.",
                "A late-evening snack helps prevent overnight fasting which worsens muscle loss.",
                "Prioritise protein-rich foods: eggs, fish, lentils, dairy.",
                "Nausea can suppress appetite — ask the doctor about anti-nausea medication.",
            ],
            "warning_signs": ["3+ days of very low appetite warrants a call to the care team."],
        },
        "activity": {
            "title": "Physical Activity with CLD",
            "key_points": [
                "Gentle exercise (walking, yoga, stretching) helps maintain muscle and improve mood.",
                "Even 10-15 minutes of light movement daily has measurable benefits.",
                "Avoid strenuous exercise during flares or when fatigue is severe.",
                "Physiotherapy referral can help if mobility is significantly impaired.",
            ],
            "warning_signs": ["Complete inactivity for 3+ days — discuss with care team."],
        },
        "medications": {
            "title": "Supporting Medication Adherence",
            "key_points": [
                "Use a weekly pill organiser to track what has been taken.",
                "Set a consistent daily alarm as a reminder.",
                "Never stop or adjust doses without the doctor's instruction.",
                "Some CLD medications interact with common painkillers — always check.",
            ],
            "warning_signs": ["Missed doses of diuretics or lactulose can cause rapid worsening."],
        },
        "burnout": {
            "title": "Caregiver Wellbeing & Preventing Burnout",
            "key_points": [
                "You cannot pour from an empty cup — your health matters too.",
                "Ask for help and accept help when offered.",
                "Stay connected with your own support network.",
                "It is okay to feel frustrated or exhausted — these feelings are valid.",
            ],
            "warning_signs": [],
        },
        "doctor": {
            "title": "When to Call the Doctor vs. Go to A&E",
            "call_doctor": [
                "New or worsening swelling in legs or abdomen",
                "Increasing confusion or forgetfulness",
                "Persistent nausea or loss of appetite",
                "Fever above 38C",
            ],
            "go_to_ae": [
                "Vomiting blood or blood in stools",
                "Severe confusion or unresponsiveness",
                "Sudden severe abdominal pain",
                "Difficulty breathing",
            ],
        },
    }

    matched = None
    for key in guidance_library:
        if key in topic_lower or topic_lower in key:
            matched = guidance_library[key]
            break

    if not matched:
        matched = {
            "title": f"Care Guidance: {topic}",
            "key_points": [
                "No specific guide found for that topic.",
                "You can ask about: sodium, fatigue, encephalopathy, medications, appetite, activity, burnout, or when to call the doctor.",
            ],
            "warning_signs": [],
        }

    print(f"[LIVERLINK LOG] Care tip retrieved for topic: {topic}")
    return {"status": "success", "topic": topic, "guidance": matched}
