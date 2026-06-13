"""MongoDB connection (shared team cluster).

Adds two collections to the team's `liverlink` db, aligned with their
existing `patient_id` string convention:

  patients : { patient_id, chat_id, name, created_at, updated_at }
  messages : { patient_id, chat_id, direction, from_agent, text,
               telegram_message_id, timestamp }
"""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import settings

log = logging.getLogger("liverlink.db")

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


async def connect() -> None:
    global client, db
    if not settings.mongodb_uri:
        log.warning("MONGODB_URI not set; using local JSON store fallback.")
        return
    client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=8000)
    await client.server_info()  # fail fast if unreachable
    db = client[settings.mongodb_db]
    await db.patients.create_index("patient_id", unique=True)
    await db.patients.create_index("chat_id")
    await db.messages.create_index([("patient_id", 1), ("timestamp", 1)])
    await db.messages.create_index([("chat_id", 1), ("timestamp", 1)])
    log.info("Connected to MongoDB db=%s", settings.mongodb_db)


async def close() -> None:
    if client:
        client.close()


def enabled() -> bool:
    return db is not None
