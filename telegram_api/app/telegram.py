from typing import Any, Optional

import httpx

from .config import settings


class TelegramError(Exception):
    pass


async def _post(method: str, payload: dict, timeout: float = 15) -> dict:
    if not settings.telegram_bot_token:
        raise TelegramError("TELEGRAM_BOT_TOKEN is not set.")
    url = f"{settings.telegram_api_base}/{method}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
    data = resp.json()
    if not data.get("ok"):
        raise TelegramError(data.get("description", "Unknown Telegram error"))
    return data["result"]


async def send_message(
    chat_id: int,
    text: str,
    open_url: Optional[str] = None,
    button_text: str = "Open LiverLink",
) -> dict:
    """Send a text message, optionally with an inline 'Open app' button.

    The button URL must be https (Telegram requirement); it points at this
    server's /open endpoint, which redirects to the liverlink:// scheme.
    """
    payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
    if open_url:
        payload["reply_markup"] = {
            "inline_keyboard": [[{"text": button_text, "url": open_url}]]
        }
    return await _post("sendMessage", payload)


async def get_updates(
    offset: int | None = None, limit: int = 20, timeout: int = 0
) -> list[dict]:
    """Fetch updates. Pass timeout>0 for long polling (held open by Telegram)."""
    payload: dict[str, Any] = {"limit": limit, "timeout": timeout}
    if offset is not None:
        payload["offset"] = offset
    # httpx must wait longer than Telegram's long-poll timeout.
    return await _post("getUpdates", payload, timeout=timeout + 15)


async def delete_webhook() -> dict:
    """Ensure no webhook is set, otherwise getUpdates returns 409 conflict."""
    return await _post("deleteWebhook", {"drop_pending_updates": False})


async def get_me() -> dict:
    return await _post("getMe", {})
