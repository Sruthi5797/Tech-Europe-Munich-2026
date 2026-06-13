"""
LiverLink Exercise & Physical Trainer Agent — Google ADK definition.

Coaches the patient on gentle, safe physical activities and logs workouts to MongoDB.
"""

from google.adk.agents import Agent

from exercise_agent.prompts import EXERCISE_AGENT_INSTRUCTION
from exercise_agent.tools import do_exercise_today, search_exercise_video

root_agent = Agent(
    name="exercise_agent",
    model="gemini-2.5-flash",
    description=(
        "Coach Jax — LiverLink's friendly physical fitness and exercise coach. "
        "Helps Chronic Liver Disease (CLD) patients stay active with ultra-safe, low-impact routines "
        "or short meditation videos to prevent muscle loss, and logs daily sessions to MongoDB."
    ),
    instruction=EXERCISE_AGENT_INSTRUCTION,
    tools=[do_exercise_today, search_exercise_video],
)
