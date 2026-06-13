"""
LiverLink Patient Check-in Agent — Google ADK definition.

This agent conducts a warm, empathetic daily health check-in for patients
living with Chronic Liver Disease (CLD), tracking medications, sleep, nutrition,
hydration, salt intake, mood, and optional Hand AI neurological assessment.
"""

from typing import Optional

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from patient_checkin.prompts import PATIENT_AGENT_INSTRUCTION
from patient_checkin.tools import (
    log_medication_status,
    log_sleep_quality,
    log_protein_intake,
    log_water_intake,
    log_salt_intake,
    log_mood,
    log_fatigue,
    log_appetite,
    log_activity_level,
    log_weight,
    initiate_hand_ai_test,
)


def opening_greeting(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Fires at the start of every new session.
    Returns Lila's warm opening message so she speaks first —
    the patient never has to break the silence.
    """
    if callback_context.state.get("greeted"):
        return None  # Already greeted in this session

    callback_context.state["greeted"] = True

    from datetime import datetime
    hour = datetime.now().hour
    if hour < 12:
        time_greeting = "Good morning"
    elif hour < 17:
        time_greeting = "Good afternoon"
    else:
        time_greeting = "Good evening"

    return types.Content(
        role="model",
        parts=[types.Part(text=(
            f"{time_greeting}! 🌿 I'm **Lila**, your LiverLink daily health companion.\n\n"
            "I'm really glad you checked in today. Just being here is an act of "
            "self-care, and that means a lot. 💙\n\n"
            "I'd love to spend a few minutes doing your daily check-in together. "
            "We'll go through a few gentle questions — medications, sleep, "
            "nutrition, hydration, and how you're feeling overall. "
            "Nothing overwhelming, I promise — just a caring conversation.\n\n"
            "**First things first — were you able to take all of your medications today?** 💊"
        ))],
    )


root_agent = Agent(
    name="patient_checkin_agent",
    model="gemini-2.5-flash",
    description=(
        "Lila — LiverLink's compassionate daily health companion for patients "
        "living with Chronic Liver Disease (CLD). Conducts structured check-ins "
        "covering medications, sleep, protein, hydration, sodium, mood, and "
        "optional Hand AI neurological assessment."
    ),
    instruction=PATIENT_AGENT_INSTRUCTION,
    before_agent_callback=opening_greeting,
    tools=[
        log_medication_status,
        log_sleep_quality,
        log_protein_intake,
        log_water_intake,
        log_salt_intake,
        log_mood,
        log_fatigue,
        log_appetite,
        log_activity_level,
        log_weight,
        initiate_hand_ai_test,
    ],
)
