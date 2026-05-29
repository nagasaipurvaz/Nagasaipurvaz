"""
CrewAI-based Care Management Crew.

Crew composition:
  - Care Coordinator   → orchestrates the workflow
  - Clinical Analyst   → reviews clinical data & risk scores
  - Social Worker      → assesses social determinants of health (SDOH)
  - Care Plan Writer   → generates the structured care plan

The crew collaborates to produce a comprehensive, FHIR-ready care plan.
"""

from crewai import Agent, Crew, Process, Task
from langchain_openai import ChatOpenAI

from src.config.settings import get_settings
from src.tools.clinical_tools import calculate_readmission_risk, check_drug_interactions, identify_care_gaps
from src.tools.fhir_tools import (
    get_patient,
    get_patient_conditions,
    get_patient_medications,
    get_patient_observations,
)


def _llm():
    settings = get_settings()
    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0.1)


def build_care_management_crew(patient_id: str) -> Crew:
    llm = _llm()

    # ── Agents ────────────────────────────────────────────────────────────────
    coordinator = Agent(
        role="Care Coordinator",
        goal="Orchestrate the care management process and ensure all team members have the information they need.",
        backstory=(
            "Experienced care coordinator with 15 years in complex case management. "
            "Expert at navigating health systems and coordinating multidisciplinary teams."
        ),
        tools=[get_patient, get_patient_conditions],
        llm=llm,
        verbose=True,
        allow_delegation=True,
    )

    clinical_analyst = Agent(
        role="Clinical Analyst",
        goal="Analyze clinical data, calculate risk scores, and identify evidence-based care priorities.",
        backstory=(
            "Board-certified clinical pharmacist with expertise in population health. "
            "Applies evidence-based guidelines (ACC/AHA, ADA, USPSTF) to patient cases."
        ),
        tools=[get_patient_conditions, get_patient_medications, get_patient_observations,
               calculate_readmission_risk, check_drug_interactions, identify_care_gaps],
        llm=llm,
        verbose=True,
    )

    social_worker = Agent(
        role="Social Determinants Specialist",
        goal="Assess social determinants of health (SDOH) barriers and connect patients with community resources.",
        backstory=(
            "Licensed clinical social worker specializing in SDOH screening. "
            "Identifies barriers including housing instability, food insecurity, and transportation."
        ),
        tools=[get_patient],
        llm=llm,
        verbose=True,
    )

    care_plan_writer = Agent(
        role="Care Plan Writer",
        goal=(
            "Synthesize all team inputs into a structured, FHIR R4-compatible care plan "
            "with measurable goals and actionable interventions."
        ),
        backstory=(
            "Clinical documentation specialist who translates complex care needs into "
            "clear, actionable plans following PCMH and value-based care frameworks."
        ),
        tools=[],
        llm=llm,
        verbose=True,
    )

    # ── Tasks ─────────────────────────────────────────────────────────────────
    gather_task = Task(
        description=f"Retrieve and summarize the complete clinical profile for patient {patient_id}. "
                    f"Include demographics, diagnoses, medications, and recent observations.",
        expected_output="Structured patient clinical summary with all relevant data.",
        agent=coordinator,
    )

    risk_task = Task(
        description=f"For patient {patient_id}, calculate the 30-day readmission risk score, "
                    f"check for drug interactions, and identify preventive care gaps. "
                    f"Provide prioritized clinical recommendations.",
        expected_output="Risk assessment report with scores, alerts, and evidence-based recommendations.",
        agent=clinical_analyst,
        context=[gather_task],
    )

    sdoh_task = Task(
        description=f"Assess social determinants of health for patient {patient_id}. "
                    f"Based on available data, identify potential SDOH barriers and suggest resources.",
        expected_output="SDOH assessment with identified barriers and community resource recommendations.",
        agent=social_worker,
        context=[gather_task],
    )

    care_plan_task = Task(
        description=(
            f"Generate a comprehensive FHIR R4-compatible care plan for patient {patient_id}. "
            f"The plan must include: (1) 3-5 measurable SMART goals, "
            f"(2) specific interventions with assigned roles and timelines, "
            f"(3) monitoring schedule, (4) patient education components. "
            f"Output as structured JSON matching FHIR CarePlan resource schema."
        ),
        expected_output=(
            "Complete care plan in FHIR R4 JSON format with goals, activities, "
            "responsible parties, and monitoring schedule."
        ),
        agent=care_plan_writer,
        context=[gather_task, risk_task, sdoh_task],
    )

    return Crew(
        agents=[coordinator, clinical_analyst, social_worker, care_plan_writer],
        tasks=[gather_task, risk_task, sdoh_task, care_plan_task],
        process=Process.sequential,
        verbose=True,
    )


async def run_care_management(patient_id: str) -> dict:
    """Run the full care management crew for a patient."""
    crew = build_care_management_crew(patient_id)
    result = crew.kickoff()
    return {
        "patient_id": patient_id,
        "care_plan_output": str(result),
        "status": "completed",
    }
