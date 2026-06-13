"""Background long-poller that auto-registers patients.

A patient opens the bot via a deep link  https://t.me/<bot>?start=<patient_id>
(or types  /start <patient_id>  manually). Telegram delivers the text
"/start <patient_id>". We capture their chat_id, register the mapping, and
reply with a confirmation — no manual /recent-chats + /patients step needed.
"""

import asyncio
import logging

from . import telegram
from .config import settings
from .store import store

log = logging.getLogger("liverlink.poller")

# chat_id -> last seen chat info (powers GET /recent-chats without re-polling)
recent_chats: dict[int, dict] = {}

_offset: int | None = None
_bot_username: str | None = None


async def bot_username() -> str | None:
    """Bot @username, cached. Used to build onboarding deep links."""
    global _bot_username
    if _bot_username is None and settings.telegram_bot_token:
        try:
            me = await telegram.get_me()
            _bot_username = me.get("username")
        except telegram.TelegramError as e:
            log.warning("get_me failed: %s", e)
    return _bot_username


def _parse_start_payload(text: str) -> str | None:
    """Extract the patient_id from '/start <patient_id>'. None if absent."""
    text = text.strip()
    if not text.startswith("/start"):
        return None
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) == 2 and parts[1].strip() else None


async def _handle_update(update: dict) -> None:
    msg = update.get("message") or update.get("edited_message") or {}
    chat = msg.get("chat")
    if not chat:
        return

    chat_id = chat["id"]
    name = chat.get("first_name") or chat.get("username")
    recent_chats[chat_id] = {
        "chat_id": chat_id,
        "first_name": chat.get("first_name"),
        "username": chat.get("username"),
        "type": chat.get("type"),
    }

    text = (msg.get("text") or "").strip()
    start_patient_id = _parse_start_payload(text)

    if start_patient_id:
        await store.upsert_patient(start_patient_id, chat_id, name)
        log.info("Auto-registered patient_id=%s -> chat_id=%s", start_patient_id, chat_id)
        await telegram.send_message(
            chat_id,
            f"✅ You're connected to LiverLink as '{start_patient_id}'.\n"
            "Your care team can now reach you here.",
        )
        return

    if text in ("/start", "/help"):
        await telegram.send_message(
            chat_id,
            "Welcome to LiverLink 👋\n"
            "To connect your account, ask your care team for your link, "
            "or send:  /start <your-patient-id>",
        )
        return

    # Any other message is a patient reply — log it so any agent can read it.
    if text:
        patient_id = await store.patient_id_for_chat(chat_id)
        await store.log_message(
            patient_id=patient_id,
            chat_id=chat_id,
            direction="in",
            text=text,
            from_agent="patient",
        )
        log.info("Logged inbound reply from patient_id=%s chat_id=%s", patient_id, chat_id)


async def run_poller() -> None:
    """Long-poll loop. Started as a background task on app startup."""
    global _offset
    if not settings.telegram_bot_token:
        log.warning("No TELEGRAM_BOT_TOKEN set; auto-registration poller disabled.")
        return

    try:
        await telegram.delete_webhook()
    except telegram.TelegramError as e:
        log.warning("deleteWebhook failed (continuing): %s", e)

    await bot_username()
    log.info("Auto-registration poller started.")

    while True:
        try:
            updates = await telegram.get_updates(offset=_offset, timeout=25)
            for u in updates:
                _offset = u["update_id"] + 1
                try:
                    await _handle_update(u)
                except Exception as e:  # one bad update shouldn't kill the loop
                    log.exception("Error handling update: %s", e)
        except asyncio.CancelledError:
            log.info("Poller stopped.")
            break
        except Exception as e:
            log.warning("Polling error, retrying shortly: %s", e)
            await asyncio.sleep(3)
