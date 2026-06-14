"""
LiverLink Hepatology Doctor Agent — Google ADK definition.

This agent provides advanced clinical decision support for hepatologists,
capable of calculating MELD-Na and Child-Pugh scores, retrieving evidence-
based clinical pathways, and searching the web for up-to-date guidelines.
"""

from google.adk.agents import Agent

from doctor_agent.prompts import DOCTOR_AGENT_INSTRUCTION
from doctor_agent.tools import (
    search_web,
    calculate_meld_na,
    calculate_child_pugh,
    get_hepatology_clinical_pathway,
    get_patient_comprehensive_profile,
    notify_doctor_and_prep_emergency_admission,
    update_patient_prescription,
    order_lab_test_and_alert_lab,
    order_imaging_scan,
    get_clinical_feed_knowing_patient_details,
)

root_agent = Agent(
    name="hepatology_specialist_agent",
    model="gemini-2.5-flash",
    description=(
        "An advanced clinical decision support agent for hepatologists. "
        "Capable of calculating MELD-Na, Child-Pugh class, analyzing liver "
        "disease progression (MASH, cirrhosis, ascites), retrieving patient comprehensive profiles, "
        "updating patient prescriptions, dispatching lab test orders to the central lab, "
        "ordering imaging scans (like CT scans), fetching patient tailored clinical feed based on profile data, and retrieving web data using Tavily for up-to-date medical guidelines."
    ),
    instruction=DOCTOR_AGENT_INSTRUCTION,
    tools=[
        calculate_meld_na,
        calculate_child_pugh,
        get_hepatology_clinical_pathway,
        search_web,
        get_patient_comprehensive_profile,
        notify_doctor_and_prep_emergency_admission,
        update_patient_prescription,
        order_lab_test_and_alert_lab,
        order_imaging_scan,
        get_clinical_feed_knowing_patient_details,
    ],
)
