"""Clinical co-pilot API routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.agents.clinical_copilot import run_clinical_copilot
from src.hipaa.access_control import TokenData, require_permission
from src.hipaa.audit_logger import AuditAction, get_audit_logger

router = APIRouter(prefix="/clinical", tags=["Clinical Co-pilot"])


class CopilotRequest(BaseModel):
    patient_id: str
    query: str


class CopilotResponse(BaseModel):
    patient_id: str
    clinical_summary: str
    risk_level: str
    alerts: list[str]


@router.post("/copilot", response_model=CopilotResponse)
async def clinical_copilot(
    request: CopilotRequest,
    current_user: TokenData = Depends(require_permission("ai:inference")),
):
    """Run the AI clinical co-pilot for a patient query (requires inference permission)."""
    audit = get_audit_logger()
    audit.log(
        AuditAction.AI_INFERENCE,
        user_id=current_user.user_id,
        resource_type="Patient",
        resource_id=request.patient_id,
        patient_id=request.patient_id,
        details={"query_length": len(request.query)},
    )
    result = await run_clinical_copilot(request.patient_id, request.query)
    return CopilotResponse(**result)


class AssessmentResponse(BaseModel):
    patient_id: str
    risk_level: str
    recommended_actions: list[str]
    next_review_days: int
    triage_notes: str


@router.post("/assess/{patient_id}", response_model=AssessmentResponse)
async def assess_patient(
    patient_id: str,
    current_user: TokenData = Depends(require_permission("patient:read")),
):
    """Run the structured patient assessment workflow."""
    from src.workflows.patient_assessment import run_patient_assessment

    audit = get_audit_logger()
    audit.log(
        AuditAction.AI_INFERENCE,
        user_id=current_user.user_id,
        resource_type="Patient",
        resource_id=patient_id,
        patient_id=patient_id,
        details={"workflow": "patient_assessment"},
    )
    result = await run_patient_assessment(patient_id)
    return AssessmentResponse(**result)
