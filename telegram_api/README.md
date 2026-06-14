# LiverLink — Telegram API

The bot is the **single pipe** between the care agents and the patient.
Agents send messages through this API; patient replies are captured and stored
in the shared **MongoDB** (`liverlink` db) so any agent can read them.

```
Agent ──POST /send──► this API ──► Telegram ──► Patient
Patient reply ──► Telegram ──► this API (poller) ──► Mongo `messages`
Any agent ──GET /messages──► reads the conversation
```

`patient_id` is a string (same convention as your other collections, e.g.
`patient_john_doe`).

---

## Integrating (this is all your agent needs)

Base URL: `http://<host>:8000`. If `API_KEY` is set, add header `X-API-Key: <key>`.

### Send a message to a patient
```bash
POST /send
{
  "patient_id": "patient_john_doe",
  "from_agent": "doctor_agent",        # doctor_agent | caregiver_agent | patient_agent | lab_agent
  "text": "On a scale of 1-10, how do you feel today?",
  "open_app": false                    # set true to attach an "Open app" button
}
```
To attach the button that opens the iOS app, set `"open_app": true`
(optionally `"button_text": "..."`). The button points at the app's hosted
redirect page (`APP_OPEN_URL`), which launches `liverflapcheck://`.

### Read patient replies
```bash
GET /messages?patient_id=patient_john_doe                      # full conversation (oldest first)
GET /messages?patient_id=patient_john_doe&direction=in         # patient replies only
GET /messages?patient_id=patient_john_doe&direction=in&since=<iso_ts>   # poll for NEW replies
GET /messages/latest-reply?patient_id=patient_john_doe         # most recent reply (e.g. the rating)
```
`since` lets you poll: remember the last `timestamp` you saw and pass it back.

### Onboard a patient (one-time, automated)
```bash
GET /onboarding-link?patient_id=patient_john_doe
→ { "url": "https://t.me/CirhosisBot?start=patient_john_doe" }
```
Send that link to the patient → they tap **Start** → the bot stores their
`chat_id` automatically. After that, `/send` works for that patient.
(`patient_id` must be letters/digits/`_`/`-`, ≤64 chars.)

---

## Don't want HTTP? Read Mongo directly

Everything lives in the shared `liverlink` db:

```js
// patients : patient_id ↔ telegram chat
{ patient_id, chat_id, name, created_at, updated_at }

// messages : the two-way conversation log
{ patient_id, chat_id,
  direction,            // "out" = sent to patient,  "in" = reply from patient
  from_agent,           // who sent it ("patient" for inbound)
  text, telegram_message_id, timestamp }
```
You can `find({patient_id, direction:"in"})` to read replies yourself — but to
*send*, always go through `POST /send` (it talks to Telegram + logs the message).

---

## API reference

| Method | Path | Purpose |
|---|---|---|
| POST | `/send` | Send a message to a patient (optional open-app button) |
| GET  | `/messages` | Read conversation (`patient_id`, `direction`, `since`, `limit`) |
| GET  | `/messages/latest-reply` | Patient's most recent reply |
| GET  | `/onboarding-link` | Build the `t.me?start=` self-registration link |
| GET  | `/patients` · POST `/patients` | List / manually register patients |
| GET  | `/health` · `/bot-info` | Liveness / verify bot token |

Interactive docs (try it live): `http://<host>:8000/docs`

---

## Running it locally

```bash
cd telegram_api
cp .env.example .env          # fill in TELEGRAM_BOT_TOKEN, MONGODB_URI, APP_OPEN_URL
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The server only makes **outbound** calls to Telegram, so it works fine on
localhost — no public URL needed for sending or for onboarding. (A public URL is
only relevant to the app's redirect page, which the iOS teammate hosts.)

### As part of the full stack (`run_all.sh`)

`run_all.sh` launches this server on **port 8001** (the port the agents POST to).
It uses the project's **root `.venv`**, so install our deps into it once:

```bash
.venv/bin/pip install -r telegram_api/requirements.txt
```

and make sure `telegram_api/.env` exists (the launcher skips the Telegram API
if it's missing). Logs go to `telegram_api.log`.

`.env` keys: `TELEGRAM_BOT_TOKEN`, `MONGODB_URI`, `MONGODB_DB` (default
`liverlink`), `APP_OPEN_URL` (app redirect page), `API_KEY` (optional auth),
`APP_SCHEME` (default `liverflapcheck`, used only by the built-in `/open` fallback).
