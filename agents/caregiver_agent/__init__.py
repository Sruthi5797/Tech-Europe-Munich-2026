"""
LiverLink Caregiver Agent package.

Exports `root_agent` — required by Google ADK's `adk web` and `adk run` commands.
"""

from caregiver_agent.agent import root_agent

__all__ = ["root_agent"]
