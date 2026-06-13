import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from urllib.parse import quote, urlencode

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse

from . import db, poller, telegram
from .config import settings
from .schemas import MessageOut, PatientOut, RegisterPatient, SendMessage, SendResult
from .store import store


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    task = asyncio.create_task(poller.run_poller())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await db.close()


app = FastAPI(
    title="LiverLink Telegram API",
    description="Sends messages to patients via Telegram on behalf of the care agents, "
    "and can deep-link patients into the LiverLink iOS app.",
    version="1.0.0",
    lifespan=lifespan,
)


# --- auth (optional shared secret) --------------------------------------------
def require_api_key(x_api_key: str = Header(default="")) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key.")


def _build_open_url(deeplink_path: str) -> str:
    """https URL that goes in the Telegram 'Open app' button.

    Prefers APP_OPEN_URL (the teammate's hosted redirect page). Falls back to
    this server's own /open bridge if APP_OPEN_URL isn't configured.
    """
    if settings.app_open_url:
        base = settings.app_open_url.rstrip("/")
        if deeplink_path:
            sep = "&" if "?" in base else "?"
            return f"{base}{sep}{urlencode({'path': deeplink_path})}"
        return base
    qs = urlencode({"path": deeplink_path})
    return f"{settings.public_base_url.rstrip('/')}/open?{qs}"


async def _resolve_chat_id(body: SendMessage) -> int:
    if body.chat_id is not None:
        return body.chat_id
    chat_id = await store.get_chat_id(body.patient_id or "")
    if chat_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown patient_id '{body.patient_id}'. Onboard them via "
            "GET /onboarding-link, or register via POST /patients, or pass a raw chat_id.",
        )
    return chat_id


# --- health / info ------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/bot-info", dependencies=[Depends(require_api_key)])
async def bot_info():
    """Confirms the bot token works (calls Telegram getMe)."""
    try:
        return await telegram.get_me()
    except telegram.TelegramError as e:
        raise HTTPException(status_code=502, detail=str(e))


# --- patient registry ---------------------------------------------------------
@app.post("/patients", response_model=PatientOut, dependencies=[Depends(require_api_key)])
async def register_patient(body: RegisterPatient):
    return await store.upsert_patient(body.patient_id, body.chat_id, body.name)


@app.get("/patients", response_model=list[PatientOut], dependencies=[Depends(require_api_key)])
async def list_patients():
    return await store.all_patients()


@app.get("/recent-chats", dependencies=[Depends(require_api_key)])
async def recent_chats():
    """Chat ids of people who recently messaged the bot (collected by the poller).

    Mostly a fallback/debug view — with auto-registration, patients map
    themselves via the onboarding link and you rarely need this.
    """
    return list(poller.recent_chats.values())


@app.get("/onboarding-link", dependencies=[Depends(require_api_key)])
async def onboarding_link(patient_id: str = Query(..., description="Your internal patient id.")):
    """Build the deep link a patient taps to auto-register themselves.

    Send this link to the patient. When they open it and tap Start, the bot
    receives '/start <patient_id>', captures their chat_id, and registers the
    mapping automatically.
    """
    username = await poller.bot_username()
    if not username:
        raise HTTPException(
            status_code=502,
            detail="Could not resolve bot username (check TELEGRAM_BOT_TOKEN).",
        )
    return {
        "patient_id": patient_id,
        "url": f"https://t.me/{username}?start={quote(patient_id)}",
    }


# --- the main endpoint agents call --------------------------------------------
@app.post("/send", response_model=SendResult, dependencies=[Depends(require_api_key)])
async def send(body: SendMessage):
    """Send a message to a patient.

    Plain message:
        {"patient_id": "john-58", "text": "Your ALT increased by 25%."}

    Message + open-app button:
        {"patient_id": "john-58", "text": "Please do your hand test.",
         "open_app": true, "deeplink_path": "handtest?patient=john-58"}
    """
    chat_id = await _resolve_chat_id(body)

    open_url = None
    if body.open_app:
        open_url = _build_open_url(body.deeplink_path)

    try:
        result = await telegram.send_message(
            chat_id=chat_id,
            text=body.text,
            open_url=open_url,
            button_text=body.button_text,
        )
    except telegram.TelegramError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Log the outbound message so the whole care team can see the conversation.
    patient_id = body.patient_id or await store.patient_id_for_chat(chat_id)
    await store.log_message(
        patient_id=patient_id,
        chat_id=chat_id,
        direction="out",
        text=body.text,
        from_agent=body.from_agent,
        telegram_message_id=result.get("message_id"),
    )

    return SendResult(
        ok=True,
        chat_id=chat_id,
        telegram_message_id=result.get("message_id"),
        open_url=open_url,
    )


# --- reading patient replies (for any agent) ----------------------------------
@app.get("/messages", response_model=list[MessageOut], dependencies=[Depends(require_api_key)])
async def get_messages(
    patient_id: str | None = Query(None),
    chat_id: int | None = Query(None),
    direction: str | None = Query(None, description="'in' = from patient, 'out' = to patient."),
    since: datetime | None = Query(
        None, description="ISO timestamp; return only messages after this. For polling new replies."
    ),
    limit: int = Query(50, le=500),
):
    """Read a patient's conversation (both directions, oldest first).

    Poll for new patient replies:
        GET /messages?patient_id=patient_john_doe&direction=in&since=<last_seen_ts>
    """
    if not db.enabled():
        raise HTTPException(status_code=503, detail="Message history requires MongoDB (MONGODB_URI).")
    msgs = await store.get_messages(
        patient_id=patient_id, chat_id=chat_id, direction=direction, since=since, limit=limit
    )
    return [
        MessageOut(
            patient_id=m.get("patient_id"),
            chat_id=m["chat_id"],
            direction=m["direction"],
            from_agent=m.get("from_agent"),
            text=m["text"],
            telegram_message_id=m.get("telegram_message_id"),
            timestamp=m["timestamp"].isoformat(),
        )
        for m in msgs
    ]


@app.get("/messages/latest-reply", response_model=MessageOut | None,
         dependencies=[Depends(require_api_key)])
async def latest_reply(patient_id: str = Query(...)):
    """The patient's most recent inbound message (e.g. their 'how I feel' rating)."""
    if not db.enabled():
        raise HTTPException(status_code=503, detail="Message history requires MongoDB (MONGODB_URI).")
    msgs = await store.get_messages(patient_id=patient_id, direction="in", limit=500)
    if not msgs:
        return None
    m = msgs[-1]
    return MessageOut(
        patient_id=m.get("patient_id"),
        chat_id=m["chat_id"],
        direction=m["direction"],
        from_agent=m.get("from_agent"),
        text=m["text"],
        telegram_message_id=m.get("telegram_message_id"),
        timestamp=m["timestamp"].isoformat(),
    )


# --- the https -> liverlink:// bridge -----------------------------------------
@app.get("/open", response_class=HTMLResponse)
async def open_app(path: str = Query("", description="Path appended after the scheme.")):
    """Redirect page: Telegram opens this https URL, this page launches the app.

    Telegram won't let a button point straight at liverlink://, so the button
    points here, and this page hands off to the custom scheme.
    """
    deeplink = f"{settings.app_scheme}://{path}"
    safe = quote(deeplink, safe=":/?=&%")
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Opening LiverLink…</title>
  <style>
    body {{ font-family: -apple-system, system-ui, sans-serif; text-align: center;
            padding: 48px 24px; color: #1c2b3a; }}
    a.btn {{ display: inline-block; margin-top: 20px; padding: 14px 28px;
             background: #0a84ff; color: #fff; border-radius: 12px;
             text-decoration: none; font-weight: 600; }}
  </style>
</head>
<body>
  <h2>Opening LiverLink…</h2>
  <p>If the app doesn't open automatically, tap the button below.</p>
  <a class="btn" href="{safe}">Open LiverLink</a>
  <script>
    // Try to launch the native app immediately.
    window.location.replace("{safe}");
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)
