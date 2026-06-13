"""
Tool functions for the LiverLink Patient Check-in Agent.

Each tool logs a piece of daily health data for a CLD patient into MongoDB.
When a reading crosses a clinical threshold, a caregiver alert is written
to the caregiver_alerts collection — the A2A notification channel.
"""

from datetime import datetime, timezone

from shared.db import get_db, PATIENT_ID


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> str:
    return _now().strftime("%Y-%m-%d")


def _write_health_log(event: str, data: dict, flags: list = None) -> None:
    """Persist a health log entry to MongoDB. Non-fatal on failure."""
    try:
        get_db().health_logs.insert_one({
            "patient_id": PATIENT_ID,
            "event": event,
            "date": _today(),
            "timestamp": _now(),
            "data": data,
            "flags": flags or [],
        })
    except Exception as e:
        print(f"[DB WRITE ERROR] {e}")


def _notify_caregiver(alert_type: str, severity: str, message: str) -> None:
    """
    Write an alert to caregiver_alerts — the A2A channel.

    The caregiver agent reads this collection on session start and via
    get_pending_alerts(). Severity levels: mild | moderate | urgent
    """
    try:
        alert_id = f"alert_{_now().strftime('%Y%m%d_%H%M%S_%f')}"
        get_db().caregiver_alerts.insert_one({
            "alert_id": alert_id,
            "patient_id": PATIENT_ID,
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "source": "patient_checkin_agent",
            "timestamp": _now(),
            "acknowledged": False,
        })
        print(f"[A2A] Caregiver alert sent -> {alert_type} ({severity}): {message}")
    except Exception as e:
        print(f"[A2A ERROR] {e}")


# ──────────────────────────────────────────────────────────────────────────────
#  Medication Adherence
# ──────────────────────────────────────────────────────────────────────────────

def log_medication_status(taken: bool, missed_medications: list[str] = [], notes: str = "") -> dict:
    """
    Log whether the patient took their prescribed medications today.

    Args:
        taken: True if all medications were taken, False if any were missed.
        missed_medications: List of specific medications that were missed.
        notes: Any additional context the patient shared.

    Returns:
        A confirmation dict with the logged record.
    """
    record = {
        "timestamp": _now().isoformat(),
        "event": "medication_adherence",
        "medications_taken": taken,
        "missed_medications": missed_medications,
        "adherence_rate": "100%" if taken else f"{max(0, 100 - len(missed_medications) * 20)}%",
        "notes": notes,
    }

    flags = []
    if not taken:
        flags.append("MEDICATION_MISSED")
        _notify_caregiver(
            alert_type="MEDICATION_MISSED",
            severity="moderate",
            message=(
                f"John did not take all medications today. "
                f"Missed: {', '.join(missed_medications) if missed_medications else 'unspecified'}."
            ),
        )

    _write_health_log("medication_adherence", record, flags)
    print(f"[LIVERLINK LOG] {record}")
    return {
        "status": "logged",
        "message": "Medication status recorded successfully.",
        "data": record,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Sleep Quality
# ──────────────────────────────────────────────────────────────────────────────

def log_sleep_quality(hours: float, quality: str, disturbances: list[str] = [], notes: str = "") -> dict:
    """
    Log the patient's sleep duration and quality from last night.

    Args:
        hours: Number of hours slept (e.g. 7.5).
        quality: Subjective quality — one of: "poor", "fair", "good", "excellent".
        disturbances: Any sleep disturbances (e.g. ["itching", "leg cramps"]).
        notes: Additional context from the patient.

    Returns:
        A confirmation dict with the logged record.
    """
    record = {
        "timestamp": _now().isoformat(),
        "event": "sleep_quality",
        "hours_slept": hours,
        "quality": quality.lower(),
        "disturbances": disturbances,
        "notes": notes,
    }

    flags = []
    if hours < 4 or quality.lower() == "poor":
        flags.append("POOR_SLEEP")

    _write_health_log("sleep_quality", record, flags)
    print(f"[LIVERLINK LOG] {record}")
    return {
        "status": "logged",
        "message": "Sleep quality recorded successfully.",
        "data": record,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Protein Intake
# ──────────────────────────────────────────────────────────────────────────────

def log_protein_intake(grams: float, sources: list[str] = [], notes: str = "") -> dict:
    """
    Log the patient's total protein consumption today.

    CLD patients require 1.2-1.5 g/kg/day to prevent muscle wasting.

    Args:
        grams: Estimated total protein intake in grams.
        sources: Food sources (e.g. ["eggs", "lentils"]).
        notes: Any additional context.

    Returns:
        A confirmation dict with the logged record.
    """
    record = {
        "timestamp": _now().isoformat(),
        "event": "protein_intake",
        "protein_grams": grams,
        "sources": sources,
        "notes": notes,
    }
    _write_health_log("protein_intake", record)
    print(f"[LIVERLINK LOG] {record}")
    return {
        "status": "logged",
        "message": "Protein intake recorded successfully.",
        "data": record,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Water / Fluid Intake
# ──────────────────────────────────────────────────────────────────────────────

def log_water_intake(liters: float, includes_other_fluids: bool = False, notes: str = "") -> dict:
    """
    Log the patient's water and fluid consumption today.

    Args:
        liters: Total fluid intake in litres.
        includes_other_fluids: Whether figure includes non-water fluids.
        notes: Additional context.

    Returns:
        A confirmation dict with the logged record.
    """
    record = {
        "timestamp": _now().isoformat(),
        "event": "water_intake",
        "fluid_litres": liters,
        "includes_other_fluids": includes_other_fluids,
        "notes": notes,
    }
    _write_health_log("water_intake", record)
    print(f"[LIVERLINK LOG] {record}")
    return {
        "status": "logged",
        "message": "Water intake recorded successfully.",
        "data": record,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Salt / Sodium Intake
# ──────────────────────────────────────────────────────────────────────────────

def log_salt_intake(grams: float, high_sodium_foods: list[str] = [], notes: str = "") -> dict:
    """
    Log the patient's estimated sodium/salt intake today.

    CLD patients with ascites are restricted to < 5 g table salt per day.

    Args:
        grams: Estimated total salt intake in grams.
        high_sodium_foods: Notably salty foods the patient mentioned.
        notes: Additional context.

    Returns:
        A confirmation dict with the logged record.
    """
    threshold_g = 5.0
    within_limit = grams <= threshold_g

    record = {
        "timestamp": _now().isoformat(),
        "event": "salt_intake",
        "salt_grams": grams,
        "within_recommended_limit": within_limit,
        "recommended_limit_grams": threshold_g,
        "high_sodium_foods": high_sodium_foods,
        "notes": notes,
    }

    flags = []
    if not within_limit:
        flags.append("EXCEEDS_SODIUM_LIMIT")
        _notify_caregiver(
            alert_type="HIGH_SODIUM",
            severity="mild",
            message=f"John's salt intake today was {grams}g, exceeding the 5g daily limit.",
        )

    _write_health_log("salt_intake", record, flags)
    print(f"[LIVERLINK LOG] {record}")
    return {
        "status": "logged",
        "message": "Salt intake recorded successfully.",
        "data": record,
        "flag": None if within_limit else "EXCEEDS_SODIUM_LIMIT",
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Mood & Symptoms
# ──────────────────────────────────────────────────────────────────────────────

def log_mood(
    mood: str,
    energy_level: int,
    physical_symptoms: list[str] = [],
    emotional_notes: str = "",
) -> dict:
    """
    Log the patient's overall mood, energy level, and any symptoms.

    Args:
        mood: Overall mood (e.g. "good", "tired", "anxious").
        energy_level: Self-reported energy 1-10 (1 = exhausted, 10 = great).
        physical_symptoms: Reported symptoms (e.g. ["fatigue", "nausea"]).
        emotional_notes: Free-text emotional context.

    Returns:
        A confirmation dict with the logged record.
    """
    red_flag_symptoms = {
        "confusion", "disorientation", "forgetfulness", "tremor",
        "jaundice", "yellow skin", "yellow eyes", "vomiting blood",
        "black stool", "severe pain", "swelling", "fever",
    }
    flagged = [s for s in physical_symptoms if any(r in s.lower() for r in red_flag_symptoms)]

    record = {
        "timestamp": _now().isoformat(),
        "event": "mood_and_symptoms",
        "mood": mood.lower(),
        "energy_level": max(1, min(10, energy_level)),
        "physical_symptoms": physical_symptoms,
        "emotional_notes": emotional_notes,
        "red_flag_symptoms_detected": flagged,
    }

    flags = []
    if flagged:
        flags.append("RED_FLAG_SYMPTOMS")
        _notify_caregiver(
            alert_type="RED_FLAG_SYMPTOMS",
            severity="urgent",
            message=f"John reported red-flag symptoms: {', '.join(flagged)}. Immediate review recommended.",
        )

    _write_health_log("mood_and_symptoms", record, flags)
    print(f"[LIVERLINK LOG] {record}")
    return {
        "status": "logged",
        "message": "Mood and symptoms recorded successfully.",
        "data": record,
        "flag": "RED_FLAG_SYMPTOMS_DETECTED" if flagged else None,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Fatigue
# ──────────────────────────────────────────────────────────────────────────────

def log_fatigue(fatigue_level: int, notes: str = "") -> dict:
    """
    Log the patient's fatigue level today.

    Fatigue is one of the most common and debilitating CLD symptoms.
    Sudden worsening can signal decompensation.

    Args:
        fatigue_level: Self-reported fatigue 1-10 (1 = no fatigue, 10 = severe/bedridden).
        notes: Any context the patient shared about their fatigue.

    Returns:
        A confirmation dict with the logged record.
    """
    fatigue_level = max(1, min(10, fatigue_level))

    record = {
        "timestamp": _now().isoformat(),
        "event": "fatigue",
        "fatigue_level": fatigue_level,
        "notes": notes,
    }

    flags = []
    if fatigue_level >= 8:
        flags.append("HIGH_FATIGUE")
        _notify_caregiver(
            alert_type="HIGH_FATIGUE",
            severity="moderate",
            message=f"John reported severe fatigue today (level {fatigue_level}/10). {notes}".strip(),
        )

    _write_health_log("fatigue", record, flags)
    print(f"[LIVERLINK LOG] {record}")
    return {
        "status": "logged",
        "message": "Fatigue level recorded successfully.",
        "data": record,
        "flag": "HIGH_FATIGUE" if flags else None,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Appetite
# ──────────────────────────────────────────────────────────────────────────────

def log_appetite(appetite_level: int, food_consumed: str = "", notes: str = "") -> dict:
    """
    Log the patient's appetite and food intake today.

    Poor appetite in CLD leads to nutritional deficiency and muscle wasting.

    Args:
        appetite_level: Self-reported appetite 1-10 (1 = no appetite, 10 = normal).
        food_consumed: Brief description of what the patient ate today.
        notes: Any additional context.

    Returns:
        A confirmation dict with the logged record.
    """
    appetite_level = max(1, min(10, appetite_level))

    record = {
        "timestamp": _now().isoformat(),
        "event": "appetite",
        "appetite_level": appetite_level,
        "food_consumed": food_consumed,
        "notes": notes,
    }

    flags = []
    if appetite_level <= 3:
        flags.append("LOW_APPETITE")
        _notify_caregiver(
            alert_type="LOW_APPETITE",
            severity="moderate",
            message=f"John's appetite is very low today (level {appetite_level}/10). Risk of nutritional deficit.",
        )

    _write_health_log("appetite", record, flags)
    print(f"[LIVERLINK LOG] {record}")
    return {
        "status": "logged",
        "message": "Appetite recorded successfully.",
        "data": record,
        "flag": "LOW_APPETITE" if flags else None,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Activity Level
# ──────────────────────────────────────────────────────────────────────────────

def log_activity_level(
    steps: int = 0,
    activity_type: str = "none",
    duration_minutes: int = 0,
    intensity: str = "light",
) -> dict:
    """
    Log the patient's physical activity today.

    Gentle exercise helps CLD patients maintain muscle mass and reduce fatigue.

    Args:
        steps: Approximate step count (0 if unknown).
        activity_type: Type of activity — e.g. "walk", "yoga", "none".
        duration_minutes: How long the activity lasted.
        intensity: One of "none", "light", "moderate", "high".

    Returns:
        A confirmation dict with the logged record.
    """
    record = {
        "timestamp": _now().isoformat(),
        "event": "activity_level",
        "steps": steps,
        "activity_type": activity_type.lower(),
        "duration_minutes": duration_minutes,
        "intensity": intensity.lower(),
    }

    flags = []
    if activity_type.lower() == "none" or (steps == 0 and duration_minutes == 0):
        flags.append("NO_ACTIVITY")
        _notify_caregiver(
            alert_type="NO_ACTIVITY",
            severity="mild",
            message="John reported no physical activity today. Monitor for extended inactivity pattern.",
        )

    _write_health_log("activity_level", record, flags)
    print(f"[LIVERLINK LOG] {record}")
    return {
        "status": "logged",
        "message": "Activity level recorded successfully.",
        "data": record,
        "flag": "NO_ACTIVITY" if flags else None,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Weight
# ──────────────────────────────────────────────────────────────────────────────

def log_weight(weight_kg: float, notes: str = "") -> dict:
    """
    Log the patient's weight today and compare to the previous reading.

    Rapid weight gain (>= 1 kg) in CLD patients often signals fluid retention
    (ascites/oedema) and requires prompt review.

    Args:
        weight_kg: Today's weight in kilograms.
        notes: Any context (e.g. "ankles swollen", "weighed after breakfast").

    Returns:
        A confirmation dict including weight change since last reading.
    """
    record = {
        "timestamp": _now().isoformat(),
        "event": "weight",
        "weight_kg": weight_kg,
        "notes": notes,
    }

    flags = []

    # Compare against the most recent prior weight reading
    try:
        prev = get_db().health_logs.find_one(
            {"patient_id": PATIENT_ID, "event": "weight"},
            sort=[("timestamp", -1)],
        )
        if prev:
            prev_kg = prev["data"].get("weight_kg")
            change = round(weight_kg - prev_kg, 2)
            record["weight_change_kg"] = change
            record["previous_weight_kg"] = prev_kg

            if change >= 1.0:
                flags.append("RAPID_WEIGHT_GAIN")
                _notify_caregiver(
                    alert_type="RAPID_WEIGHT_GAIN",
                    severity="moderate",
                    message=(
                        f"John gained {change} kg since the last weigh-in "
                        f"({prev_kg} kg -> {weight_kg} kg). "
                        "Possible fluid retention — review recommended."
                    ),
                )
            elif change <= -2.0:
                flags.append("SIGNIFICANT_WEIGHT_LOSS")
                _notify_caregiver(
                    alert_type="SIGNIFICANT_WEIGHT_LOSS",
                    severity="moderate",
                    message=(
                        f"John lost {abs(change)} kg since the last weigh-in "
                        f"({prev_kg} kg -> {weight_kg} kg). Monitor for muscle wasting."
                    ),
                )
    except Exception as e:
        print(f"[DB READ ERROR] {e}")

    _write_health_log("weight", record, flags)
    print(f"[LIVERLINK LOG] {record}")
    return {
        "status": "logged",
        "message": "Weight recorded successfully.",
        "data": record,
        "flag": flags[0] if flags else None,
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Hand AI Test
# ──────────────────────────────────────────────────────────────────────────────

def initiate_hand_ai_test() -> dict:
    """
    Initiate the Hand AI neurological assessment test.

    Analyses hand movement via device camera to detect early signs of
    hepatic encephalopathy (HE). Early detection enables faster intervention.

    Returns:
        A dict with test session details and patient instructions.
    """
    test_id = f"hand_ai_{_now().strftime('%Y%m%d_%H%M%S')}"

    record = {
        "timestamp": _now().isoformat(),
        "event": "hand_ai_test_initiated",
        "test_id": test_id,
        "estimated_duration_minutes": 2,
    }
    _write_health_log("hand_ai_test_initiated", record)
    print(f"[LIVERLINK LOG] {record}")
    return {
        "status": "initiated",
        "test_id": test_id,
        "instructions": (
            "Your Hand AI test is ready!\n\n"
            "1. Find a well-lit space and hold your device at eye level.\n"
            "2. Hold out one hand and follow the on-screen movements.\n"
            "3. Stay relaxed — there are no wrong answers.\n"
            "4. The test takes about 2 minutes.\n\n"
            "Tap 'Begin Test' whenever you're ready."
        ),
        "data": record,
    }
