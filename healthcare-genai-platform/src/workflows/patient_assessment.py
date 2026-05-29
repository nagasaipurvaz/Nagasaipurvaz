"""
LangGraph workflow: Patient Assessment Pipeline.

Runs a structured, multi-step assessment on admission or care plan trigger.
Steps: triage → clinical_review → risk_stratification → notification
"""

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from src.config.settings import get_settings
from src.tools.clinical_tools import calculate_readmission_risk, identify_care_gaps
from src.tools.fhir_tools import get_patient_conditions, get_patient_medications, get_patient_observations


class AssessmentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    patient_id: str
    triage_notes: str
    risk_score: int
    risk_level: str
    care_gaps: list[str]
    recommended_actions: list[str]
    next_review_days: int


TRIAGE_PROMPT = """Review the patient data and perform initial triage.
Determine acuity level (urgent/routine/preventive) and list immediate concerns."""

RISK_PROMPT = """Based on the clinical data and triage notes, calculate the risk stratification.
Use the available tools to compute readmission risk and care gaps.
Output a risk_level (high/moderate/low) and recommended_actions list."""


def _llm():
    settings = get_settings()
    return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0)


def triage_node(state: AssessmentState) -> dict:
    llm = _llm()
    patient_id = state["patient_id"]
    conditions = get_patient_conditions.invoke({"patient_id": patient_id})
    meds = get_patient_medications.invoke({"patient_id": patient_id})
    obs = get_patient_observations.invoke({"patient_id": patient_id})

    context = f"Conditions:\n{conditions}\n\nMedications:\n{meds}\n\nObservations:\n{obs}"
    prompt = f"{TRIAGE_PROMPT}\n\nPatient {patient_id}:\n{context}"

    response = llm.invoke([HumanMessage(content=prompt)])
    return {
        "messages": [response],
        "triage_notes": response.content,
    }


def risk_stratification_node(state: AssessmentState) -> dict:
    llm = _llm().bind_tools([calculate_readmission_risk, identify_care_gaps])
    prompt = f"{RISK_PROMPT}\n\nTriage notes:\n{state['triage_notes']}"
    response = llm.invoke([HumanMessage(content=prompt)])

    risk_level = "moderate"
    next_review = 14
    if "high" in response.content.lower():
        risk_level, next_review = "high", 3
    elif "low" in response.content.lower():
        risk_level, next_review = "low", 30

    actions = [
        line.strip("- ").strip()
        for line in response.content.split("\n")
        if line.strip().startswith(("-", "•", "*"))
    ]

    return {
        "messages": [response],
        "risk_level": risk_level,
        "recommended_actions": actions,
        "next_review_days": next_review,
    }


def notification_node(state: AssessmentState) -> dict:
    risk = state["risk_level"]
    actions = state["recommended_actions"]

    summary = (
        f"Assessment complete for patient {state['patient_id']}.\n"
        f"Risk level: {risk.upper()}\n"
        f"Next review: {state['next_review_days']} days\n"
        f"Actions:\n" + "\n".join(f"  - {a}" for a in actions[:5])
    )
    return {"messages": [HumanMessage(content=summary)]}


def build_assessment_workflow() -> StateGraph:
    graph = StateGraph(AssessmentState)
    graph.add_node("triage", triage_node)
    graph.add_node("risk_stratification", risk_stratification_node)
    graph.add_node("notification", notification_node)

    graph.add_edge(START, "triage")
    graph.add_edge("triage", "risk_stratification")
    graph.add_edge("risk_stratification", "notification")
    graph.add_edge("notification", END)

    return graph.compile()


async def run_patient_assessment(patient_id: str) -> dict:
    workflow = build_assessment_workflow()
    initial: AssessmentState = {
        "messages": [],
        "patient_id": patient_id,
        "triage_notes": "",
        "risk_score": 0,
        "risk_level": "unknown",
        "care_gaps": [],
        "recommended_actions": [],
        "next_review_days": 30,
    }
    result = await workflow.ainvoke(initial)
    return {
        "patient_id": patient_id,
        "risk_level": result["risk_level"],
        "recommended_actions": result["recommended_actions"],
        "next_review_days": result["next_review_days"],
        "triage_notes": result["triage_notes"],
    }
