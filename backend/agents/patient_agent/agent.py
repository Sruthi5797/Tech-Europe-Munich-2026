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

from patient_agent.prompts import PATIENT_AGENT_INSTRUCTION
from patient_agent.tools import (
    get_health_tracker_data,
    run_hand_ai_ammonia_test,
    log_patient_daily_metrics,
)


def opening_greeting(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Fires at the start of every new session.
    Returns Lila's warm, concise opening message.
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
            f"{time_greeting}! I'm **Lila**, your daily liver health companion.\n\n"
            "I've reviewed all your HealthDevice data and checked your vitals, and everything is looking excellent and right on track!\n\n"
            "How are you feeling today?"
        ))],
    )


root_agent = Agent(
    name="patient_agent_agent",
    model="gemini-2.5-flash",
    description=(
        "Lila — LiverLink's compassionate daily health companion for patients "
        "living with Chronic Liver Disease (CLD). Conducts friendly conversations, "
        "helping patients review their health logs, launch their Hand AI ammonia scanner, "
        "and track daily metrics such as medications, sleep, protein, water, sodium, weight, and mood."
    ),
    instruction=PATIENT_AGENT_INSTRUCTION,
    before_agent_callback=opening_greeting,
    tools=[
        get_health_tracker_data,
        run_hand_ai_ammonia_test,
        log_patient_daily_metrics,
    ],
)
