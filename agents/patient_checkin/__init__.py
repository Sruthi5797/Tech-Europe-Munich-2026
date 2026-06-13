"""
LiverLink Patient Check-in Agent package.

Exports `root_agent` — required by Google ADK's `adk web` and `adk run` commands.
"""

from patient_checkin.agent import root_agent

__all__ = ["root_agent"]
