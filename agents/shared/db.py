"""
Shared MongoDB connection for LiverLink agents.

Used by both patient_checkin and caregiver_agent to read/write health data
and caregiver alerts (A2A communication channel).
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.database import Database

load_dotenv()

# Default patient for the demo — can be extended to multi-patient later
PATIENT_ID = os.getenv("PATIENT_ID", "patient_john_doe")


@lru_cache(maxsize=1)
def get_db() -> Database:
    """Return a cached MongoDB database handle."""
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB", "liverlink")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = client[db_name]
    _ensure_indexes(db)
    return db


def _ensure_indexes(db: Database) -> None:
    """Create indexes once on first connection."""
    try:
        db.health_logs.create_index(
            [("patient_id", ASCENDING), ("date", DESCENDING), ("event", ASCENDING)]
        )
        db.caregiver_alerts.create_index(
            [("patient_id", ASCENDING), ("acknowledged", ASCENDING), ("timestamp", DESCENDING)]
        )
    except Exception:
        pass  # Non-fatal — indexes are a performance hint only
