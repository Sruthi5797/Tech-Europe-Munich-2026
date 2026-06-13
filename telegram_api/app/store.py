"""Patient registry + message log.

Mongo-backed when MONGODB_URI is set (shared team cluster); otherwise falls
back to a local JSON file for the patient registry (messages need Mongo).

All methods are async so the same interface works for both backends.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import db as mongo
from .config import settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Store:
    # --- patients -------------------------------------------------------------
    async def upsert_patient(
        self, patient_id: str, chat_id: int, name: Optional[str]
    ) -> dict:
        if mongo.enabled():
            await mongo.db.patients.update_one(
                {"patient_id": patient_id},
                {
                    "$set": {"chat_id": chat_id, "name": name, "updated_at": _now()},
                    "$setOnInsert": {"created_at": _now()},
                },
                upsert=True,
            )
        else:
            _json_upsert(patient_id, chat_id, name)
        return {"patient_id": patient_id, "chat_id": chat_id, "name": name}

    async def get_chat_id(self, patient_id: str) -> Optional[int]:
        if mongo.enabled():
            doc = await mongo.db.patients.find_one({"patient_id": patient_id})
            return doc["chat_id"] if doc else None
        rec = _json_load().get(patient_id)
        return rec["chat_id"] if rec else None

    async def patient_id_for_chat(self, chat_id: int) -> Optional[str]:
        if mongo.enabled():
            doc = await mongo.db.patients.find_one({"chat_id": chat_id})
            return doc["patient_id"] if doc else None
        for pid, rec in _json_load().items():
            if rec["chat_id"] == chat_id:
                return pid
        return None

    async def all_patients(self) -> list[dict]:
        if mongo.enabled():
            out = []
            async for d in mongo.db.patients.find():
                out.append(
                    {"patient_id": d["patient_id"], "chat_id": d["chat_id"], "name": d.get("name")}
                )
            return out
        return [{"patient_id": pid, **rec} for pid, rec in _json_load().items()]

    # --- messages (Mongo only) ------------------------------------------------
    async def log_message(
        self,
        patient_id: Optional[str],
        chat_id: int,
        direction: str,  # "in" (from patient) | "out" (to patient)
        text: str,
        from_agent: Optional[str] = None,
        telegram_message_id: Optional[int] = None,
    ) -> Optional[dict]:
        if not mongo.enabled():
            return None
        doc = {
            "patient_id": patient_id,
            "chat_id": chat_id,
            "direction": direction,
            "from_agent": from_agent,
            "text": text,
            "telegram_message_id": telegram_message_id,
            "timestamp": _now(),
        }
        await mongo.db.messages.insert_one(doc)
        return doc

    async def get_messages(
        self,
        patient_id: Optional[str] = None,
        chat_id: Optional[int] = None,
        direction: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[dict]:
        if not mongo.enabled():
            return []
        q: dict = {}
        if patient_id:
            q["patient_id"] = patient_id
        if chat_id is not None:
            q["chat_id"] = chat_id
        if direction:
            q["direction"] = direction
        if since:
            q["timestamp"] = {"$gt": since}
        out = []
        cursor = mongo.db.messages.find(q).sort("timestamp", 1).limit(limit)
        async for d in cursor:
            d["_id"] = str(d["_id"])
            out.append(d)
        return out


# --- JSON fallback helpers (patient registry only) ----------------------------
def _json_path() -> Path:
    return Path(settings.patients_file)


def _json_load() -> dict:
    p = _json_path()
    return json.loads(p.read_text() or "{}") if p.exists() else {}


def _json_upsert(patient_id: str, chat_id: int, name: Optional[str]) -> None:
    data = _json_load()
    data[patient_id] = {"chat_id": chat_id, "name": name}
    _json_path().write_text(json.dumps(data, indent=2))


store = Store()
