import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
HERE = Path(__file__).parent
dotenv_path = HERE.parent / ".env"
load_dotenv(dotenv_path)

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "liverlink")
PATIENT_ID = os.getenv("PATIENT_ID", "patient_john_doe")

if not MONGODB_URI:
    print("Error: MONGODB_URI not found in .env")
    sys.exit(1)

print(f"Connecting to MongoDB database: '{MONGODB_DB}'")
client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]

def clear_existing_logs():
    """Clear existing logs to ensure a clean demo environment."""
    print("Clearing existing health_logs and caregiver_alerts for patient_john_doe...")
    db.health_logs.delete_many({"patient_id": PATIENT_ID})
    db.caregiver_alerts.delete_many({"patient_id": PATIENT_ID})
    print("Clear complete.")

def insert_sample_logs():
    now = datetime.now(timezone.utc)
    
    # We will generate daily health logs for the last 5 days
    logs = []
    
    # Day 1: 4 days ago
    d1 = now - timedelta(days=4)
    d1_str = d1.strftime("%Y-%m-%d")
    logs.extend([
        {"event": "medication_adherence", "date": d1_str, "timestamp": d1, "data": {"medications_taken": True, "notes": "Took all morning/evening doses."}},
        {"event": "sleep_quality", "date": d1_str, "timestamp": d1, "data": {"hours_slept": 7.2, "quality": "good", "disturbances": []}},
        {"event": "protein_intake", "date": d1_str, "timestamp": d1, "data": {"protein_grams": 78, "sources": ["eggs", "salmon"]}},
        {"event": "water_intake", "date": d1_str, "timestamp": d1, "data": {"fluid_litres": 2.4}},
        {"event": "salt_intake", "date": d1_str, "timestamp": d1, "data": {"salt_grams": 3.5, "within_recommended_limit": True}},
        {"event": "mood_and_symptoms", "date": d1_str, "timestamp": d1, "data": {"mood": "good", "energy_level": 7, "physical_symptoms": []}},
        {"event": "fatigue", "date": d1_str, "timestamp": d1, "data": {"fatigue_level": 3}},
        {"event": "appetite", "date": d1_str, "timestamp": d1, "data": {"appetite_level": 8, "food_consumed": "Salmon and rice"}},
        {"event": "activity_level", "date": d1_str, "timestamp": d1, "data": {"steps": 5200, "activity_type": "walk", "duration_minutes": 25}},
        {"event": "weight", "date": d1_str, "timestamp": d1, "data": {"weight_kg": 78.1}},
        {"event": "ammonia_level", "date": d1_str, "timestamp": d1, "data": {"ammonia_level_ppm": 34.2, "status": "normal"}},
        {"event": "exercise", "date": d1_str, "timestamp": d1, "data": {"exercise_completed": True, "exercise_type": "gentle walk", "duration_minutes": 25}}
    ])

    # Day 2: 3 days ago
    d2 = now - timedelta(days=3)
    d2_str = d2.strftime("%Y-%m-%d")
    logs.extend([
        {"event": "medication_adherence", "date": d2_str, "timestamp": d2, "data": {"medications_taken": True, "notes": "No missed meds."}},
        {"event": "sleep_quality", "date": d2_str, "timestamp": d2, "data": {"hours_slept": 6.8, "quality": "fair", "disturbances": ["itching"]}},
        {"event": "protein_intake", "date": d2_str, "timestamp": d2, "data": {"protein_grams": 82, "sources": ["greek yogurt", "chicken"]}},
        {"event": "water_intake", "date": d2_str, "timestamp": d2, "data": {"fluid_litres": 2.5}},
        {"event": "salt_intake", "date": d2_str, "timestamp": d2, "data": {"salt_grams": 4.1, "within_recommended_limit": True}},
        {"event": "mood_and_symptoms", "date": d2_str, "timestamp": d2, "data": {"mood": "stable", "energy_level": 6, "physical_symptoms": ["mild itching"]}},
        {"event": "fatigue", "date": d2_str, "timestamp": d2, "data": {"fatigue_level": 4}},
        {"event": "appetite", "date": d2_str, "timestamp": d2, "data": {"appetite_level": 7, "food_consumed": "Chicken breast with green beans"}},
        {"event": "activity_level", "date": d2_str, "timestamp": d2, "data": {"steps": 6100, "activity_type": "walk", "duration_minutes": 30}},
        {"event": "weight", "date": d2_str, "timestamp": d2, "data": {"weight_kg": 78.0}},
        {"event": "ammonia_level", "date": d2_str, "timestamp": d2, "data": {"ammonia_level_ppm": 38.5, "status": "normal"}},
        {"event": "exercise", "date": d2_str, "timestamp": d2, "data": {"exercise_completed": True, "exercise_type": "gentle walk", "duration_minutes": 30}}
    ])

    # Day 3: 2 days ago
    d3 = now - timedelta(days=2)
    d3_str = d3.strftime("%Y-%m-%d")
    logs.extend([
        {"event": "medication_adherence", "date": d3_str, "timestamp": d3, "data": {"medications_taken": True, "notes": "On track."}},
        {"event": "sleep_quality", "date": d3_str, "timestamp": d3, "data": {"hours_slept": 8.0, "quality": "excellent", "disturbances": []}},
        {"event": "protein_intake", "date": d3_str, "timestamp": d3, "data": {"protein_grams": 90, "sources": ["lentils", "tofu", "turkey"]}},
        {"event": "water_intake", "date": d3_str, "timestamp": d3, "data": {"fluid_litres": 2.8}},
        {"event": "salt_intake", "date": d3_str, "timestamp": d3, "data": {"salt_grams": 3.2, "within_recommended_limit": True}},
        {"event": "mood_and_symptoms", "date": d3_str, "timestamp": d3, "data": {"mood": "great", "energy_level": 9, "physical_symptoms": []}},
        {"event": "fatigue", "date": d3_str, "timestamp": d3, "data": {"fatigue_level": 2}},
        {"event": "appetite", "date": d3_str, "timestamp": d3, "data": {"appetite_level": 9, "food_consumed": "Turkey breast and lentil soup"}},
        {"event": "activity_level", "date": d3_str, "timestamp": d3, "data": {"steps": 8000, "activity_type": "walk", "duration_minutes": 40}},
        {"event": "weight", "date": d3_str, "timestamp": d3, "data": {"weight_kg": 77.8}},
        {"event": "ammonia_level", "date": d3_str, "timestamp": d3, "data": {"ammonia_level_ppm": 31.0, "status": "normal"}},
        {"event": "exercise", "date": d3_str, "timestamp": d3, "data": {"exercise_completed": True, "exercise_type": "cardio walk", "duration_minutes": 40}}
    ])

    # Day 4: 1 day ago
    d4 = now - timedelta(days=1)
    d4_str = d4.strftime("%Y-%m-%d")
    logs.extend([
        {"event": "medication_adherence", "date": d4_str, "timestamp": d4, "data": {"medications_taken": True, "notes": "No issues."}},
        {"event": "sleep_quality", "date": d4_str, "timestamp": d4, "data": {"hours_slept": 7.5, "quality": "good", "disturbances": []}},
        {"event": "protein_intake", "date": d4_str, "timestamp": d4, "data": {"protein_grams": 85, "sources": ["eggs", "fish"]}},
        {"event": "water_intake", "date": d4_str, "timestamp": d4, "data": {"fluid_litres": 2.6}},
        {"event": "salt_intake", "date": d4_str, "timestamp": d4, "data": {"salt_grams": 3.8, "within_recommended_limit": True}},
        {"event": "mood_and_symptoms", "date": d4_str, "timestamp": d4, "data": {"mood": "good", "energy_level": 8, "physical_symptoms": []}},
        {"event": "fatigue", "date": d4_str, "timestamp": d4, "data": {"fatigue_level": 2}},
        {"event": "appetite", "date": d4_str, "timestamp": d4, "data": {"appetite_level": 8, "food_consumed": "Baked cod and broccoli"}},
        {"event": "activity_level", "date": d4_str, "timestamp": d4, "data": {"steps": 7200, "activity_type": "walk", "duration_minutes": 35}},
        {"event": "weight", "date": d4_str, "timestamp": d4, "data": {"weight_kg": 77.9}},
        {"event": "ammonia_level", "date": d4_str, "timestamp": d4, "data": {"ammonia_level_ppm": 33.5, "status": "normal"}},
        {"event": "exercise", "date": d4_str, "timestamp": d4, "data": {"exercise_completed": True, "exercise_type": "gentle walk", "duration_minutes": 35}}
    ])

    # Day 5: Today
    d5 = now
    d5_str = d5.strftime("%Y-%m-%d")
    logs.extend([
        {"event": "medication_adherence", "date": d5_str, "timestamp": d5, "data": {"medications_taken": True, "notes": "Took Ursodiol on schedule."}},
        {"event": "sleep_quality", "date": d5_str, "timestamp": d5, "data": {"hours_slept": 7.8, "quality": "good", "disturbances": []}},
        {"event": "protein_intake", "date": d5_str, "timestamp": d5, "data": {"protein_grams": 80, "sources": ["greek yogurt", "salmon"]}},
        {"event": "water_intake", "date": d5_str, "timestamp": d5, "data": {"fluid_litres": 2.7}},
        {"event": "salt_intake", "date": d5_str, "timestamp": d5, "data": {"salt_grams": 3.6, "within_recommended_limit": True}},
        {"event": "mood_and_symptoms", "date": d5_str, "timestamp": d5, "data": {"mood": "cheerful", "energy_level": 8, "physical_symptoms": []}},
        {"event": "fatigue", "date": d5_str, "timestamp": d5, "data": {"fatigue_level": 3}},
        {"event": "appetite", "date": d5_str, "timestamp": d5, "data": {"appetite_level": 8, "food_consumed": "Oatmeal with berries, salmon and quinoa"}},
        {"event": "activity_level", "date": d5_str, "timestamp": d5, "data": {"steps": 6800, "activity_type": "yoga", "duration_minutes": 30}},
        {"event": "weight", "date": d5_str, "timestamp": d5, "data": {"weight_kg": 78.0}},
        {"event": "ammonia_level", "date": d5_str, "timestamp": d5, "data": {"ammonia_level_ppm": 32.1, "status": "normal"}},
        {"event": "exercise", "date": d5_str, "timestamp": d5, "data": {"exercise_completed": True, "exercise_type": "liver-friendly yoga", "duration_minutes": 30}}
    ])

    # Insert patient_id to each record
    for log in logs:
        log["patient_id"] = PATIENT_ID
        log["flags"] = []

    print(f"Inserting {len(logs)} logs into the health_logs collection...")
    db.health_logs.insert_many(logs)
    print("Database population completed successfully!")

if __name__ == "__main__":
    clear_existing_logs()
    insert_sample_logs()
