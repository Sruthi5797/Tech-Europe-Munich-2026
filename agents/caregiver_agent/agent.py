"""
LiverLink Caregiver Agent — Google ADK definition.

Aria supports caregivers of CLD patients with daily summaries, trend reports,
escalation tools, and CLD-specific care guidance.
"""

from typing import Optional

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from caregiver_agent.prompts import CAREGIVER_AGENT_INSTRUCTION
from caregiver_agent.tools import (
    get_patient_daily_summary,
    get_health_trend_report,
    get_pending_alerts,
    log_caregiver_observation,
    send_escalation_to_care_team,
    get_cld_care_tip,
    acknowledge_patient_alert,
)


def opening_briefing(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Fires at the start of every new session.
    Aria greets the caregiver and immediately pulls the patient's latest status
    so the caregiver has the information they need right away.
    """
    if callback_context.state.get("briefed"):
        return None

    callback_context.state["briefed"] = True

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
            f"{time_greeting}! 🌿 I'm **Aria**, the LiverLink caregiver companion.\n\n"
            "I'm here to keep you informed and supported as you care for your loved one. "
            "Let me pull up today's check-in summary right away so you know exactly "
            "how things are going. 💙\n\n"
            "One moment..."
        ))],
    )


root_agent = Agent(
    name="caregiver_agent",
    model="gemini-2.5-flash",
    description=(
        "Aria — LiverLink's dedicated AI companion for CLD caregivers. "
        "Provides daily patient summaries, health trend reports, escalation support, "
        "and practical CLD care guidance."
    ),
    instruction=CAREGIVER_AGENT_INSTRUCTION,
    before_agent_callback=opening_briefing,
    tools=[
        get_patient_daily_summary,
        get_health_trend_report,
        get_pending_alerts,
        log_caregiver_observation,
        send_escalation_to_care_team,
        get_cld_care_tip,
        acknowledge_patient_alert,
    ],
)
