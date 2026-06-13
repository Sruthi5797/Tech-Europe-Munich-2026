from typing import Optional

from pydantic import BaseModel, Field, model_validator


class RegisterPatient(BaseModel):
    patient_id: str = Field(..., description="Your internal patient identifier.")
    chat_id: int = Field(..., description="Telegram chat id of the patient.")
    name: Optional[str] = Field(None, description="Optional display name.")


class PatientOut(BaseModel):
    patient_id: str
    chat_id: int
    name: Optional[str] = None


class SendMessage(BaseModel):
    """Send a message to a patient.

    Identify the patient by EITHER patient_id (registered) OR a raw chat_id.

    Set open_app=True to attach an "Open LiverLink" button that launches the
    iOS app via the liverlink:// scheme (through the server's /open redirect).
    """

    patient_id: Optional[str] = None
    chat_id: Optional[int] = None

    text: str = Field(..., description="Message body sent to the patient.")

    from_agent: Optional[str] = Field(
        None,
        description="Which agent is sending, e.g. 'doctor_agent'. Logged with the message.",
    )

    open_app: bool = Field(
        False, description="If true, attach a button that opens the LiverLink app."
    )
    deeplink_path: str = Field(
        "",
        description="Path appended after the scheme, e.g. 'patient/123' -> liverlink://patient/123",
    )
    button_text: str = Field("Open LiverLink", description="Label for the open-app button.")

    @model_validator(mode="after")
    def _require_target(self):
        if self.patient_id is None and self.chat_id is None:
            raise ValueError("Provide either 'patient_id' or 'chat_id'.")
        return self


class SendResult(BaseModel):
    ok: bool
    chat_id: int
    telegram_message_id: Optional[int] = None
    open_url: Optional[str] = None


class MessageOut(BaseModel):
    patient_id: Optional[str] = None
    chat_id: int
    direction: str  # "in" = from patient, "out" = to patient
    from_agent: Optional[str] = None
    text: str
    telegram_message_id: Optional[int] = None
    timestamp: str
