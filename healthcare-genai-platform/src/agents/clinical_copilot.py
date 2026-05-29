"""
LangGraph-based Clinical Co-pilot.

State machine:
  START → fetch_patient_data → assess_risk → check_interactions
        → identify_gaps → synthesize → END

The co-pilot assists clinicians by gathering FHIR data, running
evidence-based risk models, and generating a structured clinical summary.
"""

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from src.config.settings import get_settings
from src.tools.clinical_tools import CLINICAL_TOOLS
from src.tools.fhir_tools import FHIR_TOOLS

ALL_TOOLS = FHIR_TOOLS + CLINICAL_TOOLS

SYSTEM_PROMPT = """You are a clinical AI co-pilot supporting healthcare providers.
Your role is to:
1. Retrieve comprehensive patient data from the FHIR server
2. Calculate evidence-based risk scores (readmission, deterioration)
3. Check for drug interactions and contraindications
4. Identify preventive care gaps per USPSTF guidelines
5. Synthesize findings into a structured clinical summary

Always cite your sources and flag high-priority alerts at the top.
You are a decision-support tool — final clinical decisions rest with the physician.
Do NOT disclose raw PHI in your reasoning steps."""


class CopilotState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    patient_id: str
    clinical_summary: str
    risk_level: str
    alerts: list[str]


def _build_llm():
    settings = get_settings()
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    ).bind_tools(ALL_TOOLS)


def call_model(state: CopilotState) -> dict:
    llm = _build_llm()
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def should_continue(state: CopilotState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "synthesize"


def synthesize(state: CopilotState) -> dict:
    """Extract structured outputs from the final AI message."""
    last_ai = next(
        (m for m in reversed(state["messages"]) if isinstance(m, AIMessage)),
        None,
    )
    content = last_ai.content if last_ai else ""

    # Simple heuristic extraction — in production use structured output
    risk_level = "unknown"
    if "High" in content:
        risk_level = "high"
    elif "Moderate" in content:
        risk_level = "moderate"
    elif "Low" in content:
        risk_level = "low"

    alerts = [line.strip() for line in content.split("\n") if line.strip().startswith("⚠")]

    return {
        "clinical_summary": content,
        "risk_level": risk_level,
        "alerts": alerts,
    }


def build_clinical_copilot() -> StateGraph:
    tool_node = ToolNode(ALL_TOOLS)

    graph = StateGraph(CopilotState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.add_node("synthesize", synthesize)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "synthesize": "synthesize"})
    graph.add_edge("tools", "agent")
    graph.add_edge("synthesize", END)

    return graph.compile()


async def run_clinical_copilot(patient_id: str, query: str) -> dict:
    """Entry point: run the co-pilot for a given patient and clinical query."""
    copilot = build_clinical_copilot()
    initial_state: CopilotState = {
        "messages": [HumanMessage(content=f"Patient ID: {patient_id}\n\nClinical query: {query}")],
        "patient_id": patient_id,
        "clinical_summary": "",
        "risk_level": "unknown",
        "alerts": [],
    }
    result = await copilot.ainvoke(initial_state)
    return {
        "patient_id": patient_id,
        "clinical_summary": result["clinical_summary"],
        "risk_level": result["risk_level"],
        "alerts": result["alerts"],
    }
